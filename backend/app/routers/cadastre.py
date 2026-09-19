"""Locality map, buildings, levels, parcels, property search, infrastructure assets."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from ..dependencies import CurrentUser, DbSession, PlannerUser, StaffUser
from ..models import Building, InfraAsset, Level, Parcel
from ..schemas.auth import MessageOut
from ..schemas.cadastre import (
    BuildingCreate,
    BuildingSummary,
    BuildingUpdate,
    InfraAssetOut,
    LevelCreate,
    LevelUpdate,
    Page,
    ParcelOut,
)
from ..services.activity import log_activity
from ..services.analysis import DEPTH_REFERENCE
from ..services.cadastre import (
    building_meta,
    conflict_summary,
    confidence_status,
    get_building_or_404,
    get_level_or_404,
    level_payload,
)

router = APIRouter(prefix="/api", tags=["cadastre"])

JURISDICTION = "MP Nagar, Bhopal Municipal Area"


# ----------------------------------------------------------------- locality map
@router.get("/locality")
def read_locality(user: CurrentUser, db: DbSession):
    """Everything the 3D Cadastre Explorer's locality map draws."""
    buildings = db.scalars(select(Building).order_by(Building.name)).all()
    assets = db.scalars(select(InfraAsset)).all()

    metro = next((a for a in assets if a.kind == "metro"), None)
    rail = next((a for a in assets if a.kind == "rail"), None)
    parks = [a for a in assets if a.kind == "park"]

    return {
        "name": JURISDICTION,
        "buildings": [BuildingSummary.model_validate(b).model_dump(by_alias=True) for b in buildings],
        "genericBuildings": (metro.details.get("generic_buildings") if metro else None)
        or _generic_blocks(db),
        "metro": (
            {
                "slug": metro.slug,
                "name": metro.name,
                "status": metro.status,
                "path": (metro.geometry or {}).get("path"),
                "stations": (metro.geometry or {}).get("stations", []),
            }
            if metro
            else {}
        ),
        "rail": (
            {
                "slug": rail.slug,
                "name": rail.name,
                "path": (rail.geometry or {}).get("path"),
                "label": (rail.details or {}).get("label", rail.name),
            }
            if rail
            else {}
        ),
        "parks": [
            {"slug": p.slug, "name": p.name, **(p.geometry or {}), **(p.details or {})} for p in parks
        ],
    }


def _generic_blocks(db) -> list[dict]:
    rows = db.scalars(select(InfraAsset).where(InfraAsset.kind == "generic_block")).all()
    return [{"name": r.name, **(r.geometry or {})} for r in rows]


@router.get("/infra-assets", response_model=list[InfraAssetOut])
def list_infra_assets(user: CurrentUser, db: DbSession, kind: str | None = None):
    stmt = select(InfraAsset)
    if kind:
        stmt = stmt.where(InfraAsset.kind == kind)
    return db.scalars(stmt.order_by(InfraAsset.kind, InfraAsset.name)).all()


@router.get("/infra-assets/{slug}", response_model=InfraAssetOut)
def read_infra_asset(slug: str, user: CurrentUser, db: DbSession):
    asset = db.scalars(select(InfraAsset).where(InfraAsset.slug == slug)).first()
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Infrastructure asset not found")
    return asset


@router.get("/depth-reference")
def read_depth_reference(user: CurrentUser):
    """Depth labels for the Underground / X-Ray and Vertical Stack views."""
    return DEPTH_REFERENCE


# ----------------------------------------------------------------- parcels
@router.get("/parcels", response_model=Page[ParcelOut])
def list_parcels(
    user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    search: str | None = Query(None, max_length=120),
):
    stmt = select(Parcel)
    count_stmt = select(func.count(Parcel.id))
    if search:
        pattern = f"%{search.lower()}%"
        cond = or_(
            func.lower(Parcel.ulpin).like(pattern),
            func.lower(Parcel.address).like(pattern),
            func.lower(Parcel.khasra_no).like(pattern),
        )
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(Parcel.ulpin).offset((page - 1) * page_size).limit(page_size)).all()
    return Page(
        items=[ParcelOut.model_validate(r) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/parcels/{ulpin}", response_model=ParcelOut)
def read_parcel(ulpin: str, user: CurrentUser, db: DbSession):
    parcel = db.scalars(select(Parcel).where(Parcel.ulpin == ulpin)).first()
    if parcel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel not found")
    return parcel


# ----------------------------------------------------------------- buildings
@router.get("/buildings")
def list_buildings(user: CurrentUser, db: DbSession, conflict: bool | None = None):
    stmt = select(Building)
    if conflict is not None:
        stmt = stmt.where(Building.has_conflict == conflict)
    rows = db.scalars(stmt.order_by(Building.name)).all()
    return [BuildingSummary.model_validate(b).model_dump(by_alias=True) for b in rows]


@router.get("/buildings/{slug}")
def read_building(slug: str, user: CurrentUser, db: DbSession):
    """Meta + all levels + conflict summary — one call per building for the explorer."""
    building = get_building_or_404(db, slug)
    return {
        "meta": building_meta(building),
        "levels": [level_payload(lvl, user) for lvl in building.levels],
        "conflict_summary": conflict_summary(db, building),
    }


@router.post("/buildings", status_code=status.HTTP_201_CREATED)
def create_building(payload: BuildingCreate, staff: StaffUser, db: DbSession):
    if db.scalars(select(Building).where(Building.slug == payload.slug)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A building with this slug already exists"
        )
    parcel = db.scalars(select(Parcel).where(Parcel.ulpin == payload.parcel_ulpin)).first()
    if parcel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent parcel {payload.parcel_ulpin} not found"
        )
    data = payload.model_dump(exclude={"parcel_ulpin"})
    building = Building(parcel_id=parcel.id, **data)
    db.add(building)
    db.flush()
    log_activity(db, f"Building '{building.name}' added to parcel {parcel.ulpin}", "info", staff)
    db.commit()
    db.refresh(building)
    return {"meta": building_meta(building), "levels": [], "conflict_summary": None}


@router.patch("/buildings/{slug}")
def update_building(slug: str, payload: BuildingUpdate, staff: StaffUser, db: DbSession):
    building = get_building_or_404(db, slug)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(building, field, value)
    db.commit()
    db.refresh(building)
    return {
        "meta": building_meta(building),
        "levels": [level_payload(lvl, staff) for lvl in building.levels],
        "conflict_summary": conflict_summary(db, building),
    }


@router.delete("/buildings/{slug}", response_model=MessageOut)
def delete_building(slug: str, admin: PlannerUser, db: DbSession):
    building = get_building_or_404(db, slug)
    name = building.name
    db.delete(building)
    log_activity(db, f"Building '{name}' deleted", "warning", admin)
    db.commit()
    return MessageOut(detail=f"Building '{name}' deleted")


# ----------------------------------------------------------------- levels
@router.get("/buildings/{slug}/levels")
def list_levels(slug: str, user: CurrentUser, db: DbSession):
    building = get_building_or_404(db, slug)
    return [level_payload(lvl, user) for lvl in building.levels]


@router.get("/buildings/{slug}/levels/{code}")
def read_level(slug: str, code: str, user: CurrentUser, db: DbSession):
    building = get_building_or_404(db, slug)
    return level_payload(get_level_or_404(db, building, code), user)


@router.post("/buildings/{slug}/levels", status_code=status.HTTP_201_CREATED)
def create_level(slug: str, payload: LevelCreate, staff: StaffUser, db: DbSession):
    building = get_building_or_404(db, slug)
    if any(lvl.code == payload.code for lvl in building.levels):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Level '{payload.code}' already exists for this building",
        )
    data = payload.model_dump()
    level = Level(
        building_id=building.id,
        ulpin_3d=f"{building.parcel.ulpin}-BLD-01-LVL-{payload.code.upper()}",
        **data,
    )
    db.add(level)
    db.flush()
    log_activity(db, f"Level '{level.label}' added to {building.name}", "info", staff)
    db.commit()
    db.refresh(level)
    return level_payload(level, staff)


@router.patch("/buildings/{slug}/levels/{code}")
def update_level(slug: str, code: str, payload: LevelUpdate, staff: StaffUser, db: DbSession):
    building = get_building_or_404(db, slug)
    level = get_level_or_404(db, building, code)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(level, field, value)
    db.flush()
    building.has_conflict = any(lvl.has_conflict for lvl in building.levels)
    db.commit()
    db.refresh(level)
    return level_payload(level, staff)


@router.delete("/buildings/{slug}/levels/{code}", response_model=MessageOut)
def delete_level(slug: str, code: str, admin: PlannerUser, db: DbSession):
    building = get_building_or_404(db, slug)
    level = get_level_or_404(db, building, code)
    label = level.label
    db.delete(level)
    db.commit()
    return MessageOut(detail=f"Level '{label}' deleted")


# ----------------------------------------------------------------- vertical stack
@router.get("/buildings/{slug}/vertical-stack")
def read_vertical_stack(slug: str, user: CurrentUser, db: DbSession):
    """Bands for the Vertical Stack view: airspace, floors, ground, underground, deep."""
    building = get_building_or_404(db, slug)
    levels = [level_payload(lvl, user) for lvl in building.levels]
    ground_codes = {"ground", "gf"}

    airspace = [l for l in levels if not l["below"] and l["airspace"]]
    floors = [l for l in levels if not l["below"] and not l["airspace"] and l["code"] not in ground_codes]
    ground = [l for l in levels if l["code"] in ground_codes]
    below = [l for l in levels if l["below"]]

    return {
        "building": building_meta(building),
        "bands": [
            {
                "id": "airspace",
                "title": "Airspace",
                "subtitle": "Terrace, roof, and upper amenity levels — air-rights zones.",
                "tone": "#9fc3d8",
                "levels": airspace,
            },
            {
                "id": "floors",
                "title": "Building Floors",
                "subtitle": f"{building.name} — {building.floors} floors above ground.",
                "tone": "var(--navy-700)",
                "levels": floors,
            },
            {
                "id": "ground",
                "title": "Ground",
                "subtitle": "Grade level — where the building meets the parcel surface.",
                "tone": "var(--teal-700)",
                "levels": ground,
            },
            {
                "id": "road",
                "title": "Road / Surface Infrastructure",
                "subtitle": "Adjacent roads and surface-level transit context.",
                "tone": "#b9c2c9",
                "levels": [],
                "note": building.road_info or "No surface infrastructure notes.",
            },
            {
                "id": "underground",
                "title": "Underground Utilities",
                "subtitle": "Basements, parking, and shallow utility lines (0–6 m below grade).",
                "tone": "var(--warning)",
                "levels": below,
                "depth_reference": [d for d in DEPTH_REFERENCE if -15 <= d["depth_m"] < 0],
            },
            {
                "id": "metro",
                "title": "Metro / Pipeline",
                "subtitle": "Mid-depth transit and trunk infrastructure (15–30 m below grade).",
                "tone": "#5b5f97",
                "levels": [],
                "depth_reference": [d for d in DEPTH_REFERENCE if d["depth_m"] <= -15],
            },
            {
                "id": "deep",
                "title": "Deep Underground Infrastructure",
                "subtitle": "Reserved corridors below 30 m for future utility and transit expansion.",
                "tone": "var(--navy-900)",
                "levels": [],
                "note": "No active infrastructure recorded below 30 m for this parcel.",
            },
        ],
    }


# ----------------------------------------------------------------- property search
@router.get("/search")
def search_properties(
    user: CurrentUser,
    db: DbSession,
    q: str | None = Query(None, max_length=200, description="ULPIN, address, building, unit or owner"),
    property_type: str | None = None,
    verification_status: str | None = Query(
        None, description="Verified | Review Required | Low Confidence"
    ),
    conflict: bool | None = None,
    survey_year: int | None = Query(None, ge=1900, le=2100),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """Backs both the global search box and the Property Search page filters."""
    stmt = select(Level).join(Building).join(Parcel)
    count_stmt = select(func.count(Level.id)).select_from(Level).join(Building).join(Parcel)

    if q:
        pattern = f"%{q.lower()}%"
        cond = or_(
            func.lower(Level.ulpin_3d).like(pattern),
            func.lower(Level.label).like(pattern),
            func.lower(Level.property_type).like(pattern),
            func.lower(Level.owner).like(pattern),
            func.lower(Building.name).like(pattern),
            func.lower(Building.address).like(pattern),
            func.lower(Parcel.ulpin).like(pattern),
            func.lower(Parcel.address).like(pattern),
        )
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    if property_type:
        cond = func.lower(Level.property_type).like(f"%{property_type.lower()}%")
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    if conflict is not None:
        stmt, count_stmt = stmt.where(Level.has_conflict == conflict), count_stmt.where(
            Level.has_conflict == conflict
        )
    if survey_year is not None:
        stmt, count_stmt = stmt.where(Level.survey_year == survey_year), count_stmt.where(
            Level.survey_year == survey_year
        )
    if verification_status:
        wanted = verification_status.strip().lower()
        if wanted == "verified":
            cond = Level.confidence >= 90
        elif wanted in {"review required", "review"}:
            cond = (Level.confidence >= 70) & (Level.confidence < 90)
        elif wanted in {"low confidence", "low"}:
            cond = Level.confidence < 70
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="verification_status must be Verified, Review Required or Low Confidence",
            )
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(Level.confidence.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()

    items = []
    for lvl in rows:
        b = lvl.building
        short_id = lvl.ulpin_3d.replace(b.parcel.ulpin, "...") if b.parcel.ulpin in lvl.ulpin_3d else lvl.ulpin_3d
        items.append(
            {
                "addr": f"{b.name}, {b.zone or b.address} ({lvl.label})",
                "parent": b.parcel.ulpin,
                "buildingId": b.slug,
                "id3d": short_id,
                "full_id3d": lvl.ulpin_3d,
                "level_code": lvl.code,
                "status": confidence_status(lvl.confidence),
                "conf": lvl.confidence,
                "conflict": lvl.has_conflict,
                "date": lvl.surveyed_on or "—",
            }
        )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


# ----------------------------------------------------------------- passport
@router.get("/passport/{ulpin_3d}")
def read_passport(ulpin_3d: str, user: CurrentUser, db: DbSession):
    """The 3D Property Passport record. Owner data is masked for public users."""
    level = db.scalars(select(Level).where(Level.ulpin_3d == ulpin_3d)).first()
    if level is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property record not found")
    building = level.building
    summary = conflict_summary(db, building)
    payload = level_payload(level, user)
    return {
        "id3d": level.ulpin_3d,
        "title": f"{payload['rights'].get('unit_name') or level.label}, {building.name}",
        "department": "GOVERNMENT OF MADHYA PRADESH · URBAN PROPERTY RECORDS (DEMO)",
        "identity": {
            "parent_ulpin": building.parcel.ulpin,
            "building": f"{building.name}, Bldg 01",
            "level": level.label,
            "property_type": level.property_type,
            "location": building.address,
            "locality": f"{building.zone or JURISDICTION} (Demo Dataset)",
        },
        "geometry": {
            "elevation": level.elevation,
            "area": level.area,
            "volume": level.volume,
        },
        "rights": {
            "ownership": payload["owner"],
            **(level.rights or {}),
            "conflict_flagged": level.has_conflict,
        },
        "verification": {
            "source": level.source,
            "survey_date": level.surveyed_on,
            "surveyor_ref": building.survey_no,
            "officer_approval": "Approved" if level.confidence >= 90 else "Pending",
            "confidence": level.confidence,
            "status": confidence_status(level.confidence),
            "verified_on": level.verified_on,
        },
        "conflict_summary": summary,
        "documents": [
            {"label": "Floor plan (PDF)", "url": f"/api/datasets?building={building.slug}&kind=floorplan"},
            {"label": "Survey report", "url": f"/api/datasets?building={building.slug}&kind=lidar"},
        ],
    }
