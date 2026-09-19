"""Settings / Admin: jurisdiction, CRS, LADM mapping, legacy ID mapping, export config."""
from fastapi import APIRouter
from sqlalchemy import select

from ..dependencies import CurrentUser, DbSession
from ..models import Building, Parcel

router = APIRouter(prefix="/api/settings", tags=["settings"])

LADM_MAPPING = [
    {"local": "Parent parcel (ULPIN)", "ladm": "LA_SpatialUnit"},
    {"local": "Building / Building 01", "ladm": "LA_BuildingUnit"},
    {"local": "Apartment / floor / basement volume", "ladm": "LA_LegalSpaceBuildingUnit"},
    {"local": "Owner (masked or verified)", "ladm": "LA_Party"},
    {"local": "Ownership, lease, easement record", "ladm": "LA_RRR (Right / Restriction / Responsibility)"},
    {"local": "Survey source (LiDAR, GNSS, plan)", "ladm": "LA_SpatialSource"},
]


@router.get("")
def read_settings(user: CurrentUser, db: DbSession):
    wards = sorted({b.ward for b in db.scalars(select(Building)).all() if b.ward})
    return {
        "jurisdictions": [f"Bhopal Municipal Area — {w}" for w in wards] or ["Bhopal Municipal Area"],
        "active_jurisdiction": f"Bhopal Municipal Area — {wards[0]}" if wards else "Bhopal Municipal Area",
        "coordinate_systems": ["WGS 84 / EPSG:4326", "UTM Zone 43N / EPSG:32643"],
        "active_crs": "WGS 84 / EPSG:4326",
        "export_formats": [
            {"name": "GeoJSON", "enabled": True},
            {"name": "CityGML", "enabled": True},
            {"name": "Shapefile", "enabled": False},
            {"name": "CSV", "enabled": True},
            {"name": "Printable map", "enabled": False},
        ],
        "role_permissions": [
            {"role": "Government / Planner", "scope": "Full platform access"},
            {"role": "Constructor / Engineer", "scope": "Explorer, proposed infra, conflicts, reports"},
            {"role": "Architect / Surveyor", "scope": "Explorer, vertical stack, underground, survey intake"},
            {"role": "Public User", "scope": "Explorer (public view), search, passport (masked)"},
        ],
    }


@router.get("/ladm-mapping")
def read_ladm_mapping(user: CurrentUser):
    """Standards compliance — LADM (ISO 19152)."""
    return LADM_MAPPING


@router.get("/legacy-mapping")
def read_legacy_mapping(user: CurrentUser, db: DbSession):
    """Khasra / survey number to parent ULPIN traceability, counted from real rows."""
    rows = []
    for parcel in db.scalars(select(Parcel).order_by(Parcel.ulpin)).all():
        volumes = sum(len(b.levels) for b in parcel.buildings)
        rows.append(
            {
                "khasra": parcel.khasra_no or "—",
                "parent": parcel.ulpin,
                "volumes": f"{volumes} volumes migrated" if volumes else "Pending digitisation",
                "status": parcel.migration_status or ("Migrated" if volumes else "In progress"),
            }
        )
    return rows
