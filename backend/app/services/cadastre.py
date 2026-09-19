"""Read helpers that shape DB rows into the structures the frontend already consumes."""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Building, Conflict, Level, Parcel, Role, SEVERITY_RANK, Severity, User


def get_building_or_404(db: Session, slug_or_id: str) -> Building:
    stmt = select(Building).where(Building.slug == slug_or_id)
    building = db.scalars(stmt).first()
    if building is None and slug_or_id.isdigit():
        building = db.get(Building, int(slug_or_id))
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    return building


def get_level_or_404(db: Session, building: Building, code: str) -> Level:
    for level in building.levels:
        if level.code == code:
            return level
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Level not found")


def mask_owner(level: Level, user: User | None) -> str | None:
    """Public users never see the unmasked owner name."""
    is_public = user is None or user.role == Role.public
    if is_public:
        return level.owner
    return level.owner_full or level.owner


def building_meta(building: Building) -> dict:
    return {
        "id": building.id,
        "slug": building.slug,
        "name": building.name,
        "parent": building.parcel.ulpin,
        "floors": building.floors,
        "basements": building.basements,
        "address": building.address,
        "ward": building.ward,
        "zone": building.zone,
        "surveyNo": building.survey_no,
        "lat": building.lat,
        "lng": building.lng,
        "landUse": building.land_use,
        "ownershipType": building.ownership_type,
        "boundaryDims": building.boundary_dims,
        "status": building.status,
        "validationStatus": building.validation_status,
        "surveyAccuracy": building.survey_accuracy,
        "gnss": building.gnss,
        "lidarAvailability": building.lidar_availability,
        "infra": building.infra or {},
        "use": building.use_category,
        "conflict": building.has_conflict,
        "roadInfo": building.road_info,
        "geometry": building.map_geometry or {},
    }


def level_payload(level: Level, user: User | None) -> dict:
    return {
        "id": level.id,
        "code": level.code,
        "label": level.label,
        "tag": level.tag,
        "id3d": level.ulpin_3d,
        "type": level.property_type,
        "elevation": level.elevation,
        "elevation_min": level.elevation_min,
        "elevation_max": level.elevation_max,
        "area": level.area,
        "volume": level.volume,
        "owner": mask_owner(level, user),
        "source": level.source,
        "confidence": level.confidence,
        "surveyed_on": level.surveyed_on,
        "verified_on": level.verified_on,
        "rights": level.rights or {},
        "below": level.below_grade,
        "airspace": level.airspace,
        "conflict": level.has_conflict,
        "h": level.render_height,
        "colors": level.colors or {},
    }


def conflict_summary(db: Session, building: Building) -> dict | None:
    """Mirrors the frontend's buildingConflictSummary()."""
    flagged = [lvl for lvl in building.levels if lvl.has_conflict]
    if not flagged:
        return None
    related = db.scalars(
        select(Conflict).where(
            Conflict.building_id == building.id,
            Conflict.severity != Severity.clear.value,
        )
    ).all()
    worst = None
    for c in related:
        rank = SEVERITY_RANK.get(Severity(c.severity), 0)
        if worst is None or rank > SEVERITY_RANK.get(Severity(worst.severity), 0):
            worst = c
    severity = worst.severity if worst else Severity.medium.value
    return {
        "count": len(flagged),
        "severity": severity,
        "type": worst.conflict_type if worst else "Basement / utility overlap",
        "overlap": worst.overlap_volume if worst else "—",
        "affectedLevels": ", ".join(lvl.label for lvl in flagged),
        "recommended": (
            "Reroute or resurvey before approval"
            if severity == Severity.critical.value
            else "Coordinate with affected party before proceeding"
        ),
    }


def confidence_status(score: int) -> str:
    if score >= 90:
        return "Verified"
    if score >= 70:
        return "Review Required"
    return "Low Confidence"


def get_parcel_or_404(db: Session, ulpin: str) -> Parcel:
    parcel = db.scalars(select(Parcel).where(Parcel.ulpin == ulpin)).first()
    if parcel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parcel not found")
    return parcel
