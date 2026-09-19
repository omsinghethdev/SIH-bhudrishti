"""Proposed Infrastructure, Utility planner (dig-safe), spatial query, 3D ULPIN wizard."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from ..dependencies import CurrentUser, DbSession, EngineerUser, PlannerUser, StaffUser
from ..models import ApprovalCase, CaseEvent, Conflict, InfraAsset, InfraProposal, Level, Severity
from ..schemas.auth import MessageOut
from ..schemas.operations import (
    DigSafeRequest,
    ProposalCreate,
    UlpinGenerateRequest,
)
from ..services.activity import log_activity
from ..services.analysis import (
    INFRA_PROFILES,
    check_dig_safe,
    spatial_query,
    analyze_route,
    validate_geometry,
)
from ..services.cadastre import get_building_or_404, get_level_or_404, level_payload

router = APIRouter(prefix="/api", tags=["planning"])


# ----------------------------------------------------------------- proposals
def _proposal_out(p: InfraProposal) -> dict:
    analysis = p.analysis or {}
    return {
        "id": p.id,
        "infra_type": p.infra_type,
        "infra_label": INFRA_PROFILES[p.infra_type]["label"],
        "infra_color": INFRA_PROFILES[p.infra_type]["color"],
        "from_building": p.from_building.slug,
        "to_building": p.to_building.slug,
        "from_name": p.from_building.name,
        "to_name": p.to_building.name,
        "width_m": p.width_m,
        "depth_m": p.depth_m,
        "status": p.status,
        "route": analysis.get("route"),
        "conflicts": analysis.get("conflicts", []),
        "analyzed": bool(analysis.get("analyzed")),
        "created_at": p.created_at,
    }


@router.get("/infra-profiles")
def read_infra_profiles(user: CurrentUser):
    """Infrastructure types offered in the route-definition form."""
    return [{"value": k, **v} for k, v in INFRA_PROFILES.items()]


@router.get("/proposals")
def list_proposals(user: CurrentUser, db: DbSession, mine: bool = True):
    stmt = select(InfraProposal)
    if mine:
        stmt = stmt.where(InfraProposal.owner_id == user.id)
    rows = db.scalars(stmt.order_by(InfraProposal.created_at.desc())).all()
    return [_proposal_out(p) for p in rows]


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
def create_proposal(payload: ProposalCreate, engineer: EngineerUser, db: DbSession):
    """Define a route and immediately run the 3D (X, Y, Z) conflict analysis."""
    from_b = get_building_or_404(db, payload.from_building)
    to_b = get_building_or_404(db, payload.to_building)
    if from_b.id == to_b.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="From and To must be different buildings"
        )
    analysis = analyze_route(db, payload.infra_type, from_b, to_b, payload.depth_m)
    proposal = InfraProposal(
        infra_type=payload.infra_type,
        from_building_id=from_b.id,
        to_building_id=to_b.id,
        width_m=payload.width_m,
        depth_m=payload.depth_m,
        status="conflicts_flagged" if analysis["conflicts"] else "clear",
        analysis=analysis,
        owner_id=engineer.id,
    )
    db.add(proposal)
    db.flush()
    label = INFRA_PROFILES[payload.infra_type]["label"]
    log_activity(
        db,
        f"Proposed {label} ({from_b.name} → {to_b.name}) analysed — "
        f"{len(analysis['conflicts'])} conflict(s)",
        "warning" if analysis["conflicts"] else "success",
        engineer,
    )
    db.commit()
    db.refresh(proposal)
    return _proposal_out(proposal)


@router.get("/proposals/{proposal_id}")
def read_proposal(proposal_id: int, user: CurrentUser, db: DbSession):
    p = db.get(InfraProposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return _proposal_out(p)


@router.post("/proposals/{proposal_id}/analyze")
def reanalyze_proposal(
    proposal_id: int,
    engineer: EngineerUser,
    db: DbSession,
    depth_m: float | None = Query(None, ge=1, le=35),
    width_m: float | None = Query(None, ge=1, le=12),
):
    """Re-run the analysis after the user moves the depth / width sliders."""
    p = db.get(InfraProposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if p.owner_id != engineer.id and engineer.role.value != "planner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only re-analyse your own proposals"
        )
    if depth_m is not None:
        p.depth_m = depth_m
    if width_m is not None:
        p.width_m = width_m
    p.analysis = analyze_route(db, p.infra_type, p.from_building, p.to_building, p.depth_m)
    p.status = "conflicts_flagged" if p.analysis["conflicts"] else "clear"
    db.commit()
    db.refresh(p)
    return _proposal_out(p)


@router.delete("/proposals/{proposal_id}", response_model=MessageOut)
def delete_proposal(proposal_id: int, engineer: EngineerUser, db: DbSession):
    p = db.get(InfraProposal, proposal_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if p.owner_id != engineer.id and engineer.role.value != "planner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own proposals"
        )
    db.delete(p)
    db.commit()
    return MessageOut(detail="Proposal deleted")


# ----------------------------------------------------------------- utility planner
@router.get("/utility/assets")
def list_utility_assets(user: CurrentUser, db: DbSession):
    """Asset registry + cross-section rows for the Utility & Infrastructure planner."""
    assets = db.scalars(
        select(InfraAsset).where(InfraAsset.kind == "utility").order_by(InfraAsset.depth_m.desc())
    ).all()
    return [
        {
            "slug": a.slug,
            "name": a.name,
            "agency": a.agency,
            "condition": a.condition,
            "depth_m": a.depth_m,
            "color": a.color,
            "label": f"{a.name} ({a.depth_m}m)",
        }
        for a in assets
    ]


@router.post("/utility/dig-safe")
def dig_safe(payload: DigSafeRequest, engineer: EngineerUser, db: DbSession):
    """'Check Dig-Safe Clearance'."""
    result = check_dig_safe(db, payload.depth_m, payload.footprint)
    result["depth_m"] = payload.depth_m
    result["footprint"] = payload.footprint
    return result


@router.get("/spatial-query")
def run_spatial_query(
    user: CurrentUser,
    db: DbSession,
    building: str = Query(..., description="Centre building slug"),
    radius_m: float = Query(150, ge=10, le=2000),
):
    """Radius search on the Property Search page."""
    center = get_building_or_404(db, building)
    return spatial_query(db, center, radius_m)


# ----------------------------------------------------------------- 3D ULPIN wizard
@router.get("/ulpin/wizard-config")
def wizard_config(user: CurrentUser):
    return {
        "steps": [
            "Select Parent Parcel",
            "Add Building / Asset",
            "Define Vertical Levels",
            "Subdivide Units",
            "Rights & Restrictions",
            "Validate Geometry",
            "Preview IDs",
            "Submit for Approval",
        ],
        "asset_types": [
            "Building",
            "Underground utility asset",
            "Standalone parking structure",
            "Air-rights volume",
        ],
        "unit_types": [
            "Apartment",
            "Commercial unit",
            "Parking bay",
            "Common area",
            "Basement",
            "Utility corridor",
            "Air-rights zone",
            "Easement / restricted zone",
        ],
        "crs": "UTM Zone 43N / EPSG:32643",
    }


@router.get("/ulpin/preview")
def preview_ulpin(
    user: CurrentUser,
    parent_ulpin: str = Query(..., min_length=4, max_length=40),
    building_no: str = Query("01", max_length=6),
    level_no: str = Query(..., min_length=1, max_length=6),
    unit_number: str | None = Query(None, max_length=20),
):
    """Live ID preview shown alongside the wizard."""
    building_id = f"{parent_ulpin}-BLD-{building_no}"
    level_id = f"{building_id}-LVL-{level_no.zfill(2)}"
    generated = f"{level_id}-UNIT-{unit_number}" if unit_number else level_id
    return {
        "parent_ulpin": parent_ulpin,
        "building_id": building_id,
        "level_id": level_id,
        "generated_3d_id": generated,
    }


@router.get("/ulpin/validate-geometry")
def validate_record_geometry(
    user: CurrentUser,
    db: DbSession,
    building: str = Query(...),
    level_code: str | None = None,
):
    """Wizard step 6 — topology checks against the parent parcel and neighbours."""
    b = get_building_or_404(db, building)
    level = get_level_or_404(db, b, level_code) if level_code else None
    return validate_geometry(db, b, level)


@router.post("/ulpin/generate", status_code=status.HTTP_201_CREATED)
def generate_ulpin(payload: UlpinGenerateRequest, staff: StaffUser, db: DbSession):
    """Wizard submit: registers the 3D volume and routes it into the approval workflow."""
    building = get_building_or_404(db, payload.building_slug)
    if building.parcel.ulpin != payload.parent_ulpin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{payload.building_slug} belongs to parcel {building.parcel.ulpin}, "
            f"not {payload.parent_ulpin}",
        )

    level_id = f"{payload.parent_ulpin}-BLD-{payload.building_no}-LVL-{payload.level_no.zfill(2)}"
    generated = f"{level_id}-UNIT-{payload.unit_number}"
    if db.scalars(select(Level).where(Level.ulpin_3d == generated)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"3D ULPIN {generated} already exists (Rule ID-01: must be unique per volume)",
        )

    base = next((lvl for lvl in building.levels if lvl.code == payload.level_code), None)
    z = payload.z if payload.z is not None else 0.0
    depth = payload.depth_below_grade
    elevation_min = -depth if depth > 0 else z
    elevation_max = 0.0 if depth > 0 else z + 3.0

    level = Level(
        building_id=building.id,
        code=f"{payload.level_code}-unit-{payload.unit_number}".lower(),
        label=f"{payload.unit_type} {payload.unit_number}",
        tag=payload.unit_number[:6],
        ulpin_3d=generated,
        property_type=payload.unit_type,
        elevation=(
            base.elevation if base else f"{elevation_min:.1f} m – {elevation_max:.1f} m"
        ),
        elevation_min=base.elevation_min if base else elevation_min,
        elevation_max=base.elevation_max if base else elevation_max,
        area=None,
        volume=None,
        owner=payload.ownership or "Pending registration",
        source="Wizard entry + survey",
        confidence=70,
        below_grade=depth > 0,
        airspace=payload.unit_type == "Air-rights zone",
        render_height=base.render_height if base else 34,
        colors=base.colors if base else {},
        sort_order=(max((lvl.sort_order for lvl in building.levels), default=0) + 1),
        rights={
            "unit_name": f"{payload.unit_type} {payload.unit_number}",
            "ownership": payload.ownership,
            "parking_entitlement": payload.parking_entitlement,
            "common_area_access": payload.common_area_access,
            "restrictions": payload.restrictions,
            "coordinates": {"x": payload.x, "y": payload.y, "z": payload.z},
        },
    )
    db.add(level)
    db.flush()

    validation = validate_geometry(db, building, base)
    case = None
    if payload.submit_for_approval:
        case = ApprovalCase(
            ulpin_3d=generated,
            title=f"{payload.unit_type} {payload.unit_number}",
            stage="officer_review" if validation["conflicts_found"] else "submitted",
            confidence=level.confidence,
            sla="Due in 3 days",
            has_conflict=validation["conflicts_found"] > 0,
            ward=building.ward,
            surveyor=staff.name,
            urgency="Critical" if validation["conflicts_found"] else "Standard",
            surveyor_notes="Generated via the 3D ULPIN wizard.",
            building_id=building.id,
            submitted_by_id=staff.id,
        )
        db.add(case)
        db.flush()
        db.add(
            CaseEvent(
                case_id=case.id,
                action="Submitted via 3D ULPIN wizard",
                actor_id=staff.id,
                actor_name=staff.name,
            )
        )

    log_activity(db, f"3D ULPIN {generated} generated for {building.name}", "success", staff)
    db.commit()
    db.refresh(level)
    return {
        "level": level_payload(level, staff),
        "ids": {
            "parent_ulpin": payload.parent_ulpin,
            "building_id": f"{payload.parent_ulpin}-BLD-{payload.building_no}",
            "level_id": level_id,
            "generated_3d_id": generated,
        },
        "validation": validation,
        "approval_case_id": case.id if case else None,
    }
