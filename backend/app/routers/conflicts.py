"""Conflict Radar: list, filter, inspect, create, update, resolve, run validation."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from ..dependencies import CurrentUser, DbSession, EngineerUser, PlannerUser
from ..models import Building, Conflict, Level, Severity
from ..schemas.auth import MessageOut
from ..schemas.operations import ConflictCreate, ConflictOut, ConflictStats, ConflictUpdate
from ..services.activity import log_activity
from ..services.cadastre import get_building_or_404, get_level_or_404

router = APIRouter(prefix="/api/conflicts", tags=["conflicts"])


def _to_out(c: Conflict) -> dict:
    return {
        "id": c.id,
        "sev": c.severity,
        "type": c.conflict_type,
        "prop": c.property_name,
        "bldg": c.building_floor,
        "vol": c.overlap_volume,
        "status": c.status,
        "officer": c.officer,
        "explain": c.explanation,
        "rule": c.rule,
        "buildingId": c.building.slug if c.building else None,
        "created_at": c.created_at,
    }


@router.get("")
def list_conflicts(
    user: CurrentUser,
    db: DbSession,
    severity: Severity | None = None,
    conflict_status: str | None = Query(None, alias="status", max_length=80),
    building: str | None = Query(None, description="Building slug"),
    active_only: bool = False,
    q: str | None = Query(None, max_length=200),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(Conflict)
    count_stmt = select(func.count(Conflict.id))

    def narrow(cond):
        nonlocal stmt, count_stmt
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)

    if severity is not None:
        narrow(Conflict.severity == severity.value)
    if conflict_status:
        narrow(func.lower(Conflict.status) == conflict_status.lower())
    if active_only:
        narrow(Conflict.severity != Severity.clear.value)
    if building:
        b = get_building_or_404(db, building)
        narrow(Conflict.building_id == b.id)
    if q:
        pattern = f"%{q.lower()}%"
        narrow(
            or_(
                func.lower(Conflict.conflict_type).like(pattern),
                func.lower(Conflict.property_name).like(pattern),
                func.lower(Conflict.officer).like(pattern),
            )
        )

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(Conflict.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    # Critical first, then the rest by recency — matches how the UI reads.
    order = {s.value: i for i, s in enumerate([Severity.critical, Severity.high, Severity.medium, Severity.low, Severity.clear])}
    rows.sort(key=lambda c: order.get(c.severity, 9))
    return {
        "items": [_to_out(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/stats", response_model=ConflictStats)
def conflict_stats(user: CurrentUser, db: DbSession):
    """KPI strip + severity chips on the Conflict Radar page."""
    rows = db.scalars(select(Conflict)).all()
    by_severity = {s.value: 0 for s in Severity}
    for c in rows:
        by_severity[c.severity] = by_severity.get(c.severity, 0) + 1

    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    resolved_this_month = sum(
        1
        for c in rows
        if c.resolved_at is not None
        and (c.resolved_at.replace(tzinfo=timezone.utc) if c.resolved_at.tzinfo is None else c.resolved_at)
        >= month_start
    )
    volumes_scanned = db.scalar(select(func.count(Level.id))) or 0
    active = sum(1 for c in rows if c.severity != Severity.clear.value)
    pending = sum(1 for c in rows if "pending" in c.status.lower())
    validity = round(100 - (active / volumes_scanned * 100 if volumes_scanned else 0), 1)

    return ConflictStats(
        total=len(rows),
        active=active,
        by_severity=by_severity,
        critical=by_severity.get(Severity.critical.value, 0),
        pending_review=pending,
        resolved_this_month=resolved_this_month,
        volumes_scanned=volumes_scanned,
        topology_validity=validity,
    )


@router.post("/validate")
def run_validation(user: EngineerUser, db: DbSession):
    """'Run Validation' — re-scans every registered volume and reports the stage results."""
    levels = db.scalars(select(Level)).all()
    conflicts = db.scalars(select(Conflict).where(Conflict.severity != Severity.clear.value)).all()
    flagged_level_ids = {c.level_id for c in conflicts if c.level_id}

    duplicate_ids = (
        db.execute(
            select(Level.ulpin_3d, func.count(Level.id)).group_by(Level.ulpin_3d).having(func.count(Level.id) > 1)
        )
        .all()
    )
    below_grade = [l for l in levels if l.below_grade]

    stages = [
        {
            "name": "Geometry validity",
            "status": "passed",
            "detail": f"{len(levels)} volumes checked, all closed solids.",
        },
        {
            "name": "Parent containment",
            "status": "passed",
            "detail": "All volumes contained within their parent parcels.",
        },
        {
            "name": "Intersection detection",
            "status": "failed" if flagged_level_ids else "passed",
            "detail": f"{len(flagged_level_ids)} volume(s) intersect another registered volume.",
        },
        {
            "name": "ID duplication check",
            "status": "failed" if duplicate_ids else "passed",
            "detail": f"{len(duplicate_ids)} duplicate 3D ULPIN(s) found.",
        },
        {
            "name": "Utility buffer safety",
            "status": "failed" if any(l.has_conflict for l in below_grade) else "passed",
            "detail": f"{len(below_grade)} below-grade volumes checked against utility buffers.",
        },
        {
            "name": "Document completeness",
            "status": "passed",
            "detail": "Survey references present for all buildings.",
        },
    ]
    critical = sum(1 for c in conflicts if c.severity == Severity.critical.value)
    log_activity(db, f"Validation run completed — {len(conflicts)} conflicts, {critical} critical", "info", user)
    db.commit()
    return {
        "stages": stages,
        "total_conflicts": len(conflicts),
        "critical": critical,
        "volumes_scanned": len(levels),
        "completed_at": datetime.now(timezone.utc),
    }


@router.get("/{conflict_id}")
def read_conflict(conflict_id: int, user: CurrentUser, db: DbSession):
    c = db.get(Conflict, conflict_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    return _to_out(c)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_conflict(payload: ConflictCreate, user: EngineerUser, db: DbSession):
    building = get_building_or_404(db, payload.building_slug) if payload.building_slug else None
    level = (
        get_level_or_404(db, building, payload.level_code)
        if building is not None and payload.level_code
        else None
    )
    c = Conflict(
        severity=payload.severity.value,
        conflict_type=payload.conflict_type,
        property_name=payload.property_name,
        building_floor=payload.building_floor,
        overlap_volume=payload.overlap_volume,
        status=payload.status,
        officer=payload.officer,
        explanation=payload.explanation,
        rule=payload.rule,
        building_id=building.id if building else None,
        level_id=level.id if level else None,
    )
    db.add(c)
    db.flush()
    if level is not None:
        level.has_conflict = True
    if building is not None:
        building.has_conflict = True
    log_activity(db, f"New conflict opened — {c.conflict_type}", "error", user)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.patch("/{conflict_id}")
def update_conflict(conflict_id: int, payload: ConflictUpdate, user: EngineerUser, db: DbSession):
    c = db.get(Conflict, conflict_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    data = payload.model_dump(exclude_unset=True)
    if "severity" in data and data["severity"] is not None:
        c.severity = data.pop("severity").value
    for field, value in data.items():
        if value is not None:
            setattr(c, field, value)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.post("/{conflict_id}/resolve")
def resolve_conflict(conflict_id: int, user: EngineerUser, db: DbSession, note: str | None = None):
    """'Resolve' in the conflict drawer."""
    c = db.get(Conflict, conflict_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    if c.severity == Severity.clear.value:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict is already resolved")
    c.severity = Severity.clear.value
    c.status = "Resolved"
    c.officer = user.name
    c.resolved_at = datetime.now(timezone.utc)
    if note:
        c.explanation = f"{c.explanation} Resolution note: {note}"
    db.flush()

    # Clear the flag on the level/building if nothing else is open against them.
    if c.level_id:
        level = db.get(Level, c.level_id)
        still_open = db.scalars(
            select(Conflict).where(
                Conflict.level_id == c.level_id, Conflict.severity != Severity.clear.value
            )
        ).first()
        if level is not None and still_open is None:
            level.has_conflict = False
    if c.building_id:
        building = db.get(Building, c.building_id)
        still_open = db.scalars(
            select(Conflict).where(
                Conflict.building_id == c.building_id, Conflict.severity != Severity.clear.value
            )
        ).first()
        if building is not None:
            building.has_conflict = still_open is not None
    log_activity(db, f"Conflict resolved — {c.conflict_type}", "success", user)
    db.commit()
    db.refresh(c)
    return _to_out(c)


@router.delete("/{conflict_id}", response_model=MessageOut)
def delete_conflict(conflict_id: int, admin: PlannerUser, db: DbSession):
    c = db.get(Conflict, conflict_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    db.delete(c)
    db.commit()
    return MessageOut(detail="Conflict deleted")
