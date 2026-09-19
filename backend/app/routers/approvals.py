"""Approval Workflows — kanban board, table, case drawer, officer decisions."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..dependencies import CurrentUser, DbSession, PlannerUser, StaffUser
from ..models import APPROVAL_STAGE_LABELS, APPROVAL_STAGES, ApprovalCase, CaseEvent
from ..schemas.auth import MessageOut
from ..schemas.operations import ApprovalCaseCreate, ApprovalDecision
from ..services.activity import log_activity
from ..services.cadastre import get_building_or_404

router = APIRouter(prefix="/api/approvals", tags=["approvals"])

DECISION_STAGES = {
    "approve": "approved",
    "publish": "published",
    "reject": "rejected",
    "return_for_correction": "needs_correction",
    "request_resurvey": "submitted",
}


def _case_out(c: ApprovalCase) -> dict:
    return {
        "id": c.id,
        "ulpin_3d": c.ulpin_3d,
        "title": c.title,
        "stage": c.stage,
        "stage_label": APPROVAL_STAGE_LABELS.get(c.stage, c.stage),
        "conf": c.confidence,
        "sla": c.sla,
        "conflict": c.has_conflict,
        "ward": c.ward,
        "surveyor": c.surveyor,
        "urgency": c.urgency,
        "surveyor_notes": c.surveyor_notes,
        "created_at": c.created_at,
    }


@router.get("/board")
def read_board(
    user: CurrentUser,
    db: DbSession,
    ward: str | None = None,
    surveyor: str | None = None,
    urgency: str | None = None,
):
    """Kanban columns. The frontend's Table view uses the same data flattened."""
    stmt = select(ApprovalCase)
    if ward:
        stmt = stmt.where(ApprovalCase.ward == ward)
    if surveyor:
        stmt = stmt.where(ApprovalCase.surveyor == surveyor)
    if urgency:
        stmt = stmt.where(ApprovalCase.urgency == urgency)
    cases = db.scalars(stmt.order_by(ApprovalCase.created_at)).all()

    columns = []
    for stage_id, label in APPROVAL_STAGES:
        stage_cases = [_case_out(c) for c in cases if c.stage == stage_id]
        if stage_id == "rejected" and not stage_cases:
            continue  # the frontend board has no Rejected column until something lands there
        columns.append({"id": stage_id, "label": label, "cases": stage_cases})

    wards = [w for (w,) in db.execute(select(ApprovalCase.ward).distinct()).all() if w]
    surveyors = [s for (s,) in db.execute(select(ApprovalCase.surveyor).distinct()).all() if s]
    return {
        "columns": columns,
        "filters": {"wards": sorted(wards), "surveyors": sorted(surveyors), "urgencies": ["Critical", "Standard"]},
    }


@router.get("")
def list_cases(
    user: CurrentUser,
    db: DbSession,
    stage: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(ApprovalCase)
    count_stmt = select(func.count(ApprovalCase.id))
    if stage:
        stmt, count_stmt = stmt.where(ApprovalCase.stage == stage), count_stmt.where(
            ApprovalCase.stage == stage
        )
    total = db.scalar(count_stmt) or 0
    rows = db.scalars(
        stmt.order_by(ApprovalCase.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [_case_out(c) for c in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_case(payload: ApprovalCaseCreate, staff: StaffUser, db: DbSession):
    if payload.stage not in APPROVAL_STAGE_LABELS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown approval stage")
    building = get_building_or_404(db, payload.building_slug) if payload.building_slug else None
    case = ApprovalCase(
        ulpin_3d=payload.ulpin_3d,
        title=payload.title,
        stage=payload.stage,
        confidence=payload.confidence,
        sla=payload.sla,
        has_conflict=payload.has_conflict,
        ward=payload.ward,
        surveyor=payload.surveyor or staff.name,
        urgency=payload.urgency,
        surveyor_notes=payload.surveyor_notes,
        building_id=building.id if building else None,
        submitted_by_id=staff.id,
    )
    db.add(case)
    db.flush()
    db.add(
        CaseEvent(
            case_id=case.id, action="Submitted by surveyor", actor_id=staff.id, actor_name=staff.name
        )
    )
    log_activity(db, f"{case.title} submitted for approval", "info", staff)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.get("/{case_id}")
def read_case(case_id: int, user: CurrentUser, db: DbSession):
    case = db.get(ApprovalCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval case not found")
    out = _case_out(case)
    out["events"] = [
        {
            "id": e.id,
            "action": e.action,
            "note": e.note,
            "actor_name": e.actor_name,
            "created_at": e.created_at,
        }
        for e in case.events
    ]
    return out


@router.post("/{case_id}/decision")
def decide_case(case_id: int, payload: ApprovalDecision, officer: PlannerUser, db: DbSession):
    """Approve / reject / return for correction / request re-survey / publish."""
    case = db.get(ApprovalCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval case not found")
    if case.stage in {"approved", "published", "rejected"} and payload.action != "publish":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Case is already {APPROVAL_STAGE_LABELS[case.stage]} and cannot be {payload.action}d",
        )
    if payload.action == "publish" and case.stage != "approved":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Only approved cases can be published"
        )

    case.stage = DECISION_STAGES[payload.action]
    action_labels = {
        "approve": "Approved by officer",
        "reject": "Rejected by officer",
        "return_for_correction": "Returned for correction",
        "request_resurvey": "Re-survey requested",
        "publish": "Published",
    }
    db.add(
        CaseEvent(
            case_id=case.id,
            action=action_labels[payload.action],
            note=payload.note,
            actor_id=officer.id,
            actor_name=officer.name,
        )
    )
    tone = {"approve": "success", "publish": "success", "reject": "error"}.get(payload.action, "warning")
    log_activity(db, f"{case.title} — {action_labels[payload.action].lower()}", tone, officer)
    db.commit()
    db.refresh(case)
    return _case_out(case)


@router.delete("/{case_id}", response_model=MessageOut)
def delete_case(case_id: int, admin: PlannerUser, db: DbSession):
    case = db.get(ApprovalCase, case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval case not found")
    db.delete(case)
    db.commit()
    return MessageOut(detail="Approval case deleted")
