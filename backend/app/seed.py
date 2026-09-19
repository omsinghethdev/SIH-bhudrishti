"""Seed the development database with the MP Nagar demo dataset the frontend expects.

Run with:  python -m app.seed          (idempotent — skips if parcels already exist)
           python -m app.seed --reset  (drops and recreates every table first)
"""
import sys
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from .core.security import hash_password
from .database import Base, SessionLocal, engine
from .models import (
    Activity,
    ApprovalCase,
    Building,
    CaseEvent,
    Conflict,
    Dataset,
    FloorSegment,
    InfraAsset,
    Level,
    Parcel,
    Role,
    User,
)

BLUE = {"top": "#9fc3d8", "left": "#7fa8c9", "right": "#6c93b3"}
GREY = {"top": "#c4ced6", "left": "#a9b6c0", "right": "#95a4b1"}
BASEMENT = {"top": "#b8c2ca", "left": "#9dadb6", "right": "#8a9ba5"}
DEEP = {"top": "#a3adb5", "left": "#8b969e", "right": "#79858e"}
OFFICE = {"top": "#a9c8dd", "left": "#87abc9", "right": "#7196b4"}

DEMO_PASSWORD = "Bhudrishti@2026"

DEMO_USERS = [
    ("R. Mehta", "r.mehta@bmc.gov.in", Role.planner, "Bhopal Municipal Corporation", 2),
    ("S. Verma", "s.verma@mpudd.gov.in", Role.planner, "MP Urban Development Dept.", 60),
    ("N. Iqbal", "n.iqbal@geosurv.in", Role.surveyor, "GeoSurv Consultants", 1440),
    ("R. Bansal", "r.bansal@geosurv.in", Role.surveyor, "GeoSurv Consultants", 4320),
    ("K. Nair", "k.nair@bmrc.co.in", Role.constructor, "BMRC (Metro Corridor)", 300),
    ("A. Sharma", "a.sharma@example.com", Role.public, None, 2880),
    ("V. Deshpande", "v.deshpande@deshpandeinfra.in", Role.constructor, "Deshpande Infra Pvt. Ltd.", 20160),
]


def _lakeview_levels() -> list[dict]:
    return [
        dict(code="terrace", label="Terrace", tag="Terrace", property_type="Common area",
             elevation="19.0 m – 19.6 m", elevation_min=19.0, elevation_max=19.6, area="210 m²",
             volume="126 m³", owner="Common — RWA managed", source="Drone orthophoto", confidence=88,
             below_grade=False, airspace=True, has_conflict=False, render_height=20, colors=GREY),
        dict(code="floor5", label="Floor 5", tag="L5", property_type="Office / shared amenity",
             elevation="15.4 m – 18.6 m", elevation_min=15.4, elevation_max=18.6, area="420 m²",
             volume="1344 m³", owner="Multiple (masked)", source="LiDAR", confidence=91,
             below_grade=False, airspace=True, has_conflict=False, render_height=34, colors=BLUE),
        dict(code="floor4", label="Floor 4", tag="L4", property_type="Apartments (incl. Unit 402)",
             elevation="12.0 m – 15.1 m", elevation_min=12.0, elevation_max=15.1, area="92.4 m²",
             volume="286.4 m³", owner="A. Sharma (masked)", owner_full="Anil Sharma",
             source="LiDAR + floor plan", confidence=96, below_grade=False, airspace=False,
             has_conflict=True, render_height=34, colors=BLUE,
             unit_suffix="-UNIT-402",
             rights={"unit_name": "Apartment 402", "lease_status": "Owner-occupied",
                     "parking_entitlement": "1 bay, Basement B1",
                     "common_area_access": "Lift, stair, terrace",
                     "fire_safety_boundary": "Conflict flagged"}),
        dict(code="floor3", label="Floor 3", tag="L3", property_type="Apartments",
             elevation="8.6 m – 11.8 m", elevation_min=8.6, elevation_max=11.8, area="412 m²",
             volume="1318 m³", owner="Multiple (masked)", source="LiDAR + floor plan", confidence=94,
             below_grade=False, airspace=False, has_conflict=False, render_height=34, colors=BLUE),
        dict(code="floor2", label="Floor 2", tag="L2", property_type="Apartments",
             elevation="5.4 m – 8.4 m", elevation_min=5.4, elevation_max=8.4, area="412 m²",
             volume="1318 m³", owner="Multiple (masked)", source="LiDAR + floor plan", confidence=95,
             below_grade=False, airspace=False, has_conflict=False, render_height=34, colors=BLUE),
        dict(code="floor1", label="Floor 1", tag="L1", property_type="Apartments",
             elevation="2.2 m – 5.2 m", elevation_min=2.2, elevation_max=5.2, area="412 m²",
             volume="1318 m³", owner="Multiple (masked)", source="LiDAR + floor plan", confidence=95,
             below_grade=False, airspace=False, has_conflict=False, render_height=34, colors=BLUE),
        dict(code="ground", label="Ground Floor", tag="G", property_type="Retail & lobby",
             elevation="0.0 m – 2.0 m", elevation_min=0.0, elevation_max=2.0, area="480 m²",
             volume="960 m³", owner="Common + 3 retail units", source="Floor plan + survey",
             confidence=90, below_grade=False, airspace=False, has_conflict=False,
             render_height=38, colors=GREY),
        dict(code="b1", label="Basement B1", tag="B1", property_type="Parking (common)",
             elevation="-3.0 m – 0.0 m", elevation_min=-3.0, elevation_max=0.0, area="520 m²",
             volume="1560 m³", owner="Common — RWA managed", source="GNSS + manual entry",
             confidence=82, below_grade=True, airspace=False, has_conflict=False,
             render_height=34, colors=BASEMENT),
        dict(code="b2", label="Basement B2", tag="B2", property_type="Utility / service area",
             elevation="-6.2 m – -3.0 m", elevation_min=-6.2, elevation_max=-3.0, area="260 m²",
             volume="832 m³", owner="Municipal utility easement", source="GNSS + manual entry",
             confidence=71, below_grade=True, airspace=False, has_conflict=True,
             render_height=34, colors=DEEP),
    ]


def _dbtrade_levels() -> list[dict]:
    office = lambda c, l, t, e, emin, emax, conf, conflict=False, airspace=False: dict(  # noqa: E731
        code=c, label=l, tag=t, property_type="Corporate office", elevation=e, elevation_min=emin,
        elevation_max=emax, area="560 m²", volume="1568 m³", owner="Multiple (masked)",
        source="LiDAR", confidence=conf, below_grade=False, airspace=airspace,
        has_conflict=conflict, render_height=28, colors=OFFICE)
    return [
        dict(code="roof", label="Roof Amenity", tag="Roof", property_type="Common area",
             elevation="21.0 m – 21.6 m", elevation_min=21.0, elevation_max=21.6, area="180 m²",
             volume="108 m³", owner="Common — facility managed", source="Drone orthophoto",
             confidence=85, below_grade=False, airspace=True, has_conflict=False,
             render_height=18, colors=GREY),
        office("f6", "Floor 6", "L6", "18.0 m – 20.8 m", 18.0, 20.8, 92, airspace=True),
        office("f5", "Floor 5", "L5", "15.2 m – 18.0 m", 15.2, 18.0, 93),
        office("f4", "Floor 4", "L4", "12.4 m – 15.2 m", 12.4, 15.2, 93),
        office("f3", "Floor 3", "L3", "9.6 m – 12.4 m", 9.6, 12.4, 90),
        office("f2", "Floor 2", "L2", "6.8 m – 9.6 m", 6.8, 9.6, 69, conflict=True),
        dict(code="gf", label="Ground Floor", tag="G", property_type="Retail & lobby",
             elevation="0.0 m – 3.2 m", elevation_min=0.0, elevation_max=3.2, area="640 m²",
             volume="2048 m³", owner="Common + 5 retail units", source="Floor plan + survey",
             confidence=89, below_grade=False, airspace=False, has_conflict=False,
             render_height=34, colors=GREY),
        dict(code="b1", label="Basement B1", tag="B1", property_type="Parking (common)",
             elevation="-3.0 m – 0.0 m", elevation_min=-3.0, elevation_max=0.0, area="610 m²",
             volume="1830 m³", owner="Common — facility managed", source="GNSS + manual entry",
             confidence=80, below_grade=True, airspace=False, has_conflict=False,
             render_height=30, colors=BASEMENT),
    ]


def _mpplaza_levels() -> list[dict]:
    apt = lambda c, l, t, e, emin, emax, conf: dict(  # noqa: E731
        code=c, label=l, tag=t, property_type="Apartments", elevation=e, elevation_min=emin,
        elevation_max=emax, area="380 m²", volume="1064 m³", owner="Multiple (masked)",
        source="LiDAR + floor plan", confidence=conf, below_grade=False, airspace=False,
        has_conflict=False, render_height=28, colors=BLUE)
    return [
        apt("f4", "Floor 4", "L4", "9.8 m – 12.6 m", 9.8, 12.6, 94),
        apt("f3", "Floor 3", "L3", "7.0 m – 9.8 m", 7.0, 9.8, 94),
        apt("f2", "Floor 2", "L2", "4.2 m – 7.0 m", 4.2, 7.0, 95),
        apt("f1", "Floor 1", "L1", "1.4 m – 4.2 m", 1.4, 4.2, 95),
        dict(code="gf", label="Ground Floor", tag="G", property_type="Retail & lobby",
             elevation="0.0 m – 1.4 m", elevation_min=0.0, elevation_max=1.4, area="420 m²",
             volume="588 m³", owner="Common + 2 retail units", source="Floor plan + survey",
             confidence=88, below_grade=False, airspace=False, has_conflict=False,
             render_height=34, colors=GREY),
        dict(code="b1", label="Basement B1", tag="B1", property_type="Parking (common)",
             elevation="-2.6 m – 0.0 m", elevation_min=-2.6, elevation_max=0.0, area="400 m²",
             volume="1040 m³", owner="Common — RWA managed", source="GNSS + manual entry",
             confidence=84, below_grade=True, airspace=False, has_conflict=False,
             render_height=30, colors=BASEMENT),
    ]


BUILDINGS = [
    dict(
        slug="lakeview", name="Lakeview Residency", ulpin="1450A9B7C23456", khasra="245/2, Ward 12",
        address="14 Lakeview Avenue, MP Nagar", ward="Ward 12", zone="MP Nagar Zone II",
        survey_no="SVY-2026-0451", lat=23.2296, lng=77.4362, floors=5, basements=2,
        land_use="Residential (mixed-use)", use_category="residential",
        ownership_type="Multiple private + common (RWA)", boundary_dims="38 m × 32 m (approx.)",
        status="Occupied / operational", validation_status="Verified",
        survey_accuracy="±0.05 m (RTK-GNSS)", gnss="RTK-GNSS, 12 control points",
        lidar="Yes — Aug 2026 pass", registered_area="1,240 m²",
        infra={"roads": "Main Road frontage", "metro": "210 m from proposed station",
               "water": "Connected — municipal supply", "gas": "Not connected (LPG cylinders)",
               "electricity": "Connected — 3-phase, MPPKVVCL",
               "underground": "Water, sewer, fibre corridor nearby"},
        geometry={"x": 100, "y": 260, "w": 90, "h": 72},
        road_info="Frontage on Main Road; 210 m from the proposed metro station.",
        surveyed_on="02 Aug 2026", verified_on="18 Aug 2026", survey_year=2026,
        levels=_lakeview_levels(), conflict=True,
    ),
    dict(
        slug="dbtrade", name="DB Trade Centre", ulpin="1450B2C88F1122", khasra="246/1, Ward 12",
        address="MP Nagar Zone I, Bhopal", ward="Ward 12", zone="MP Nagar Zone I",
        survey_no="SVY-2026-0398", lat=23.2310, lng=77.4340, floors=6, basements=1,
        land_use="Commercial", use_category="commercial",
        ownership_type="Multiple corporate leaseholders", boundary_dims="44 m × 30 m (approx.)",
        status="Operational", validation_status="Review required (Floor 2)",
        survey_accuracy="±0.08 m (GNSS)", gnss="Static GNSS, 8 control points",
        lidar="Yes — Jul 2026 pass", registered_area="1,320 m²",
        infra={"roads": "Frontage on metro corridor road",
               "metro": "Direct frontage — piers proposed within 4.5 m", "water": "Connected",
               "gas": "Piped gas — commercial line",
               "electricity": "Connected — high-tension feed",
               "underground": "Metro pier clearance conflict flagged"},
        geometry={"x": 300, "y": 110, "w": 120, "h": 66},
        road_info="Fronts the metro corridor directly; piers proposed within 4.5 m of the parcel boundary.",
        surveyed_on="09 Aug 2026", verified_on=None, survey_year=2026,
        levels=_dbtrade_levels(), conflict=True,
    ),
    dict(
        slug="mpplaza", name="MP Nagar Zone II Plaza", ulpin="1450C7A55D3390", khasra="251/3A, Ward 12",
        address="MP Nagar Zone II, Bhopal", ward="Ward 12", zone="MP Nagar Zone II",
        survey_no="SVY-2026-0512", lat=23.2288, lng=77.4375, floors=4, basements=1,
        land_use="Residential", use_category="mixed",
        ownership_type="Multiple private + common (RWA)", boundary_dims="34 m × 28 m (approx.)",
        status="Operational", validation_status="Verified", survey_accuracy="±0.06 m (RTK-GNSS)",
        gnss="RTK-GNSS, 9 control points", lidar="Yes — Jun 2026 pass", registered_area="980 m²",
        infra={"roads": "Set back from Main Road", "metro": "No direct frontage",
               "water": "Connected", "gas": "Not connected", "electricity": "Connected",
               "underground": "No utility conflicts recorded"},
        geometry={"x": 470, "y": 260, "w": 100, "h": 70},
        road_info="Set back from Main Road behind the central park; no direct metro frontage.",
        surveyed_on="22 Jul 2026", verified_on="25 Jul 2026", survey_year=2026,
        levels=_mpplaza_levels(), conflict=False,
    ),
]

INFRA_ASSETS = [
    dict(slug="metro-corridor", kind="metro", name="MP Nagar Metro Corridor",
         agency="Bhopal Metro Rail Corporation (demo)",
         status="Under construction — elevated corridor, Phase 2", depth_m=-30.0, color="#5b5f97",
         details={"alignment": "Elevated viaduct, Phase 2", "completion_pct": 61,
                  "impacted_parcels": "3 flagged for clearance review",
                  "note": "Piers along this corridor fall within 4.5 m of DB Trade Centre's "
                          "registered parcel boundary — flagged for coordination.",
                  "generic_buildings": [
                      {"name": "Block C (undigitized)", "x": 220, "y": 300, "w": 55, "h": 46},
                      {"name": "Block D (undigitized)", "x": 410, "y": 130, "w": 46, "h": 40},
                      {"name": "Block E (undigitized)", "x": 130, "y": 150, "w": 50, "h": 40},
                      {"name": "Block F (undigitized)", "x": 560, "y": 340, "w": 60, "h": 48}]},
         geometry={"path": "M 20 200 C 180 170, 380 230, 640 190",
                   "stations": [{"x": 195, "y": 182, "name": "MP Nagar Metro Station (Under Construction)"},
                                {"x": 470, "y": 205, "name": "Zone II Interchange (Planned)"}]}),
    dict(slug="railway-approach", kind="rail", name="Railway Track — MP Nagar Approach",
         agency="Indian Railways (demo)", status="Operational", depth_m=0.0, color="#6b4f2a",
         details={"label": "Rani Kamlapati (Habibganj) railway approach — demo alignment",
                  "safety_buffer": "15 m from track centreline",
                  "nearby_station": "Rani Kamlapati (Habibganj)"},
         geometry={"path": "M 0 380 L 700 340"}),
    dict(slug="central-park", kind="park", name="MP Nagar Central Park (Demo)",
         agency="Bhopal Municipal Corporation", status="Public green space — no-build zone",
         color="#3f8f5b",
         details={"amenities": "Walking track, seating, play area",
                  "classification": "Public green space — no-build zone"},
         geometry={"x": 250, "y": 330, "w": 70, "h": 50}),
    dict(slug="green-corridor", kind="park", name="Shivaji Nagar Green Corridor (Demo)",
         agency="Bhopal Municipal Corporation", status="Public green space — no-build zone",
         color="#3f8f5b",
         details={"amenities": "Walking track, seating",
                  "classification": "Public green space — no-build zone"},
         geometry={"x": 40, "y": 60, "w": 90, "h": 34}),
    dict(slug="water-line", kind="utility", name="Water line", agency="City Water Board",
         condition="Fair", depth_m=-3.8, color="#2563a9", details={}, geometry={}),
    dict(slug="sewer-line", kind="utility", name="Sewer line", agency="Municipal PWD",
         condition="Fair", depth_m=-2.9, color="#6b4f2a", details={}, geometry={}),
    dict(slug="fibre-conduit", kind="utility", name="Fibre conduit", agency="BSNL Infra",
         condition="Good", depth_m=-2.6, color="#2F6F73", details={}, geometry={}),
    dict(slug="gas-line", kind="utility", name="Gas line", agency="City Gas Distribution",
         condition="Good", depth_m=-3.2, color="#c8831a", details={}, geometry={}),
]

CONFLICTS = [
    dict(severity="critical", conflict_type="Unit overlapping fire-escape / common area",
         property_name="Apartment 402", building_floor="Bldg 01 / L4", overlap_volume="14.8 m³",
         status="Officer Review Required", officer="R. Mehta", building="lakeview", level="floor4",
         explanation="Apartment 402 overlaps 14.8 m³ with the approved fire-escape volume on Level 4.",
         rule="Rule GEO-07: private volumes must not intersect designated egress paths."),
    dict(severity="critical", conflict_type="Basement intersecting utility buffer",
         property_name="Basement B2 extension", building_floor="Bldg 01 / B2", overlap_volume="9.2 m³",
         status="Under Investigation", officer="S. Verma", building="lakeview", level="b2",
         explanation="The proposed Basement B2 extension intersects 9.2 m³ with the sewer-line maintenance buffer.",
         rule="Rule UTL-03: no private construction within utility safety buffer."),
    dict(severity="high", conflict_type="Duplicate 3D ULPIN", property_name="Shop 3, Ground Floor",
         building_floor="Bldg 01 / GF", overlap_volume="—", status="Pending Review",
         officer="Unassigned", building="lakeview", level=None,
         explanation="Two submitted records reference the same generated 3D ULPIN for Shop 3.",
         rule="Rule ID-01: 3D ULPIN must be unique per volume."),
    dict(severity="medium", conflict_type="Unit extending outside parent parcel",
         property_name="Balcony extension, Unit 301", building_floor="Bldg 01 / L3",
         overlap_volume="2.1 m³", status="Pending Review", officer="N. Iqbal",
         building="lakeview", level=None,
         explanation="A balcony extension for Unit 301 extends 2.1 m³ beyond the registered parent parcel boundary.",
         rule="Rule GEO-02: child volumes must be fully contained within the parent parcel."),
    dict(severity="medium", conflict_type="Invalid elevation range",
         property_name="Utility Volume SEG-003", building_floor="Water corridor", overlap_volume="—",
         status="Pending Review", officer="Unassigned", building=None, level=None,
         explanation="Submitted elevation range for utility segment SEG-003 does not match GNSS survey points.",
         rule="Rule GEO-11: elevation range must be consistent with source survey."),
    dict(severity="medium", conflict_type="Metro pier clearance within parcel boundary",
         property_name="DB Trade Centre, Floor 2", building_floor="Bldg 01 / L2",
         overlap_volume="—", status="Pending Review", officer="K. Nair",
         building="dbtrade", level="f2",
         explanation="Metro alignment piers fall within 4.5 m of the registered parcel boundary — coordination required with BMRC.",
         rule="Rule GEO-02: infrastructure clearance must not encroach within the registered parcel boundary."),
    dict(severity="low", conflict_type="Minor setback deviation", property_name="Shop 1, Ground Floor",
         building_floor="Bldg 01 / GF", overlap_volume="0.3 m³", status="Pending Review",
         officer="Unassigned", building="lakeview", level=None,
         explanation="Shop 1's frontage deviates 0.3 m into the mandatory street setback — within tolerance but flagged for record.",
         rule="Rule GEO-14: frontage should respect the municipal setback line."),
    dict(severity="clear", conflict_type="Missing volume / gap between units",
         property_name="Units 201–202", building_floor="Bldg 01 / L2", overlap_volume="0 m³",
         status="Resolved", officer="R. Mehta", building="lakeview", level=None, resolved=True,
         explanation="A 0.4 m gap between Units 201 and 202 was corrected after re-survey.",
         rule="Rule GEO-05: adjacent private volumes should not leave unassigned gaps."),
    dict(severity="clear", conflict_type="Expired survey source", property_name="Shop 1, Ground Floor",
         building_floor="Bldg 01 / GF", overlap_volume="—", status="Resolved", officer="S. Verma",
         building="lakeview", level=None, resolved=True,
         explanation="Source survey for Shop 1 exceeded the 24-month validity window and was refreshed.",
         rule="Rule SRC-02: survey source must be refreshed every 24 months."),
]

APPROVAL_CASES = [
    ("1450A9B7C23456-BLD-01-LVL-05", "Floor 5 office subdivision", "submitted", 91, "Due in 3 days", False, "R. Bansal", "Standard"),
    ("1450A9B7C23456-BLD-01-LVL-GF-SHOP3", "Shop 3, Ground Floor", "submitted", 74, "Due in 1 day", True, "R. Bansal", "Critical"),
    ("1450A9B7C23456-BLD-01-LVL-B2", "Basement B2 utility area", "ai_review", 71, "Due in 2 days", True, "N. Iqbal", "Critical"),
    ("1450A9B7C23456-BLD-01-LVL-03-UNIT-301", "Unit 301 balcony extension", "needs_correction", 68, "Overdue", True, "N. Iqbal", "Critical"),
    ("1450A9B7C23456-BLD-01-LVL-04-UNIT-402", "Apartment 402", "officer_review", 96, "Due today", True, "R. Bansal", "Critical"),
    ("1450A9B7C23456-BLD-01-LVL-02-UNIT-201", "Unit 201", "officer_review", 95, "Due in 4 days", False, "N. Iqbal", "Standard"),
    ("1450A9B7C23456-BLD-01-LVL-01", "Floor 1 apartments", "approved", 95, "—", False, "R. Bansal", "Standard"),
    ("1450A9B7C23456-BLD-01-LVL-GF", "Ground floor retail & lobby", "published", 90, "—", False, "R. Bansal", "Standard"),
]

DATASETS = [
    ("lakeview_lidar_pass_03.las", "1.8 GB · LiDAR point cloud · EPSG:4326 · 02 Aug 2026",
     "AI segmentation ready", "lidar", "EPSG:4326", 1_932_735_283, "lakeview"),
    ("lakeview_floorplan_L4.pdf", "4.2 MB · Floor plan · Uploaded 30 Jul 2026", "Processed",
     "floorplan", "EPSG:4326", 4_404_019, "lakeview"),
    ("ward12_parcel_boundary.geojson", "640 KB · GeoJSON · EPSG:4326",
     "Coordinate reference detected", "geojson", "EPSG:4326", 655_360, None),
    ("drone_orthophoto_ward12.tif", "2.1 GB · Orthophoto · Flown 28 Jul 2026",
     "Building envelope extracted", "orthophoto", "EPSG:4326", 2_254_857_830, None),
]

FLOOR_SEGMENTS = [
    ("Floor 5", 91, "Boundary matches submitted plan within tolerance."),
    ("Floor 4", 96, "High point-density agreement; verified against as-built plan."),
    ("Floor 3", 88, "Minor footprint deviation near south balcony — flagged for review."),
    ("Basement B1", 79, "Point cloud sparse near ramp entry; manual check suggested."),
    ("Basement B2", 71, "Overlaps utility buffer — awaiting surveyor confirmation."),
]

ACTIVITIES = [
    ("Apartment 402 geometry verified by R. Mehta", "success", 32),
    ("New conflict opened — Basement B2 utility buffer", "error", 60),
    ("LiDAR pass 03 uploaded for Lakeview Residency", "info", 180),
    ("Survey source for Shop 1 flagged as expired", "warning", 1440),
    ("Ground floor retail & lobby published", "success", 1500),
]


def seed(reset: bool = False) -> None:
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.scalars(select(Parcel)).first() is not None and not reset:
            print("Database already seeded — nothing to do. Use --reset to rebuild.")
            return

        now = datetime.now(timezone.utc)

        users: dict[str, User] = {}
        for name, email, role, org, minutes_ago in DEMO_USERS:
            user = User(
                name=name, email=email, password_hash=hash_password(DEMO_PASSWORD), role=role,
                organization=org, is_active=minutes_ago < 10000,
                last_active_at=now - timedelta(minutes=minutes_ago),
            )
            db.add(user)
            users[name] = user
        db.flush()

        buildings: dict[str, Building] = {}
        for spec in BUILDINGS:
            parcel = Parcel(
                ulpin=spec["ulpin"], address=spec["address"], ward=spec["ward"], zone=spec["zone"],
                registered_area=spec["registered_area"], khasra_no=spec["khasra"],
                migration_status="Migrated",
            )
            db.add(parcel)
            db.flush()

            building = Building(
                slug=spec["slug"], name=spec["name"], parcel_id=parcel.id, address=spec["address"],
                ward=spec["ward"], zone=spec["zone"], survey_no=spec["survey_no"], lat=spec["lat"],
                lng=spec["lng"], floors=spec["floors"], basements=spec["basements"],
                land_use=spec["land_use"], use_category=spec["use_category"],
                ownership_type=spec["ownership_type"], boundary_dims=spec["boundary_dims"],
                status=spec["status"], validation_status=spec["validation_status"],
                survey_accuracy=spec["survey_accuracy"], gnss=spec["gnss"],
                lidar_availability=spec["lidar"], infra=spec["infra"],
                map_geometry=spec["geometry"], has_conflict=spec["conflict"],
                road_info=spec["road_info"],
            )
            db.add(building)
            db.flush()
            buildings[spec["slug"]] = building

            for order, lvl in enumerate(spec["levels"]):
                lvl = dict(lvl)
                suffix = lvl.pop("unit_suffix", "")
                rights = lvl.pop("rights", {})
                code = lvl["code"]
                level_tag = code.replace("floor", "").replace("f", "") if code not in {
                    "terrace", "roof", "ground", "gf", "b1", "b2"
                } else None
                if code in {"terrace"}:
                    id_part = "T"
                elif code in {"roof"}:
                    id_part = "ROOF"
                elif code in {"ground", "gf"}:
                    id_part = "GF"
                elif code in {"b1", "b2"}:
                    id_part = code.upper()
                else:
                    id_part = (level_tag or "0").zfill(2)
                ulpin_3d = f"{spec['ulpin']}-BLD-01-LVL-{id_part}{suffix}"
                db.add(
                    Level(
                        building_id=building.id, ulpin_3d=ulpin_3d, sort_order=order,
                        surveyed_on=spec["surveyed_on"], verified_on=spec["verified_on"],
                        survey_year=spec["survey_year"], rights=rights, **lvl,
                    )
                )
        db.flush()

        for spec in INFRA_ASSETS:
            db.add(InfraAsset(**spec))
        db.flush()

        for spec in CONFLICTS:
            spec = dict(spec)
            building_slug = spec.pop("building")
            level_code = spec.pop("level")
            resolved = spec.pop("resolved", False)
            building = buildings.get(building_slug) if building_slug else None
            level = None
            if building is not None and level_code:
                level = next((l for l in building.levels if l.code == level_code), None)
            db.add(
                Conflict(
                    building_id=building.id if building else None,
                    level_id=level.id if level else None,
                    resolved_at=now - timedelta(days=3) if resolved else None,
                    **spec,
                )
            )
        db.flush()

        for ulpin_3d, title, stage, conf, sla, conflict, surveyor, urgency in APPROVAL_CASES:
            case = ApprovalCase(
                ulpin_3d=ulpin_3d, title=title, stage=stage, confidence=conf, sla=sla,
                has_conflict=conflict, ward="Ward 12", surveyor=surveyor, urgency=urgency,
                surveyor_notes="Geometry derived from LiDAR pass 03, verified against floor plan.",
                building_id=buildings["lakeview"].id,
                submitted_by_id=users.get(surveyor).id if users.get(surveyor) else None,
                created_at=now - timedelta(days=12),
            )
            db.add(case)
            db.flush()
            db.add(CaseEvent(case_id=case.id, action="Submitted by surveyor",
                             actor_name=surveyor, created_at=now - timedelta(days=12)))
            db.add(CaseEvent(case_id=case.id, action="AI segmentation reviewed",
                             created_at=now - timedelta(days=10)))
            if stage in {"officer_review", "approved", "published"}:
                db.add(CaseEvent(case_id=case.id, action="Routed to officer review",
                                 created_at=now - timedelta(days=7)))
        db.flush()

        lidar_dataset = None
        for name, meta, state, kind, crs, size, building_slug in DATASETS:
            dataset = Dataset(
                name=name, meta=meta, state=state, kind=kind, crs=crs, size_bytes=size,
                building_id=buildings[building_slug].id if building_slug else None,
                uploaded_by_id=users["N. Iqbal"].id,
            )
            db.add(dataset)
            if kind == "lidar":
                lidar_dataset = dataset
        db.flush()

        for order, (label, conf, note) in enumerate(FLOOR_SEGMENTS):
            db.add(
                FloorSegment(
                    dataset_id=lidar_dataset.id if lidar_dataset else None,
                    building_id=buildings["lakeview"].id, label=label, confidence=conf,
                    note=note, sort_order=order,
                )
            )

        for text, tone, minutes_ago in ACTIVITIES:
            db.add(Activity(text=text, tone=tone, created_at=now - timedelta(minutes=minutes_ago)))

        db.commit()
        print(
            f"Seeded {len(BUILDINGS)} buildings, "
            f"{sum(len(b['levels']) for b in BUILDINGS)} 3D volumes, "
            f"{len(CONFLICTS)} conflicts, {len(APPROVAL_CASES)} approval cases, "
            f"{len(DEMO_USERS)} users."
        )
        print(f"Demo login: r.mehta@bmc.gov.in / {DEMO_PASSWORD}  (Government / Planner)")
    finally:
        db.close()


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
