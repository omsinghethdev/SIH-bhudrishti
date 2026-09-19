"""Overview dashboard, Analytics & Reports."""
from fastapi import APIRouter, Query
from sqlalchemy import func, select

from ..dependencies import CurrentUser, DbSession
from ..models import (
    Activity,
    ApprovalCase,
    Building,
    Conflict,
    Dataset,
    InfraAsset,
    InfraProposal,
    Level,
    Parcel,
    Severity,
)
from ..services.activity import activity_payload
from ..services.analysis import INFRA_PROFILES

router = APIRouter(prefix="/api", tags=["insights"])

JURISDICTION = "MP Nagar, Bhopal Municipal Area"

REPORTS = [
    {"name": "Property Passport", "desc": "Single-property verified record, printable and shareable.", "formats": ["PDF"]},
    {"name": "3D ULPIN Generation Report", "desc": "Summary of ID generation activity for a date range.", "formats": ["PDF", "CSV"]},
    {"name": "Conflict Validation Report", "desc": "Full conflict log with severity, status, and resolution.", "formats": ["PDF", "CSV"]},
    {"name": "Ward-level Cadastral Coverage", "desc": "Parcel and volume coverage by ward.", "formats": ["PDF", "GeoJSON", "CityGML"]},
    {"name": "Underground Utility Clash Report", "desc": "Utility-property intersections and buffer breaches.", "formats": ["PDF", "GeoJSON", "CityGML"]},
    {"name": "Pending Approval Report", "desc": "Cases awaiting officer decision, by SLA.", "formats": ["PDF", "CSV"]},
    {"name": "Survey Confidence Report", "desc": "Confidence score breakdown by source and ward.", "formats": ["CSV"]},
    {"name": "Audit History Report", "desc": "Immutable log of all record changes.", "formats": ["PDF", "CSV"]},
]


def _confidence_distribution(db) -> list[dict]:
    levels = db.scalars(select(Level)).all()
    total = len(levels) or 1
    verified = sum(1 for l in levels if l.confidence >= 90)
    review = sum(1 for l in levels if 70 <= l.confidence < 90)
    low = sum(1 for l in levels if l.confidence < 70)
    return [
        {"label": "Verified", "pct": round(verified / total * 100), "count": verified, "color": "#2e7d5b"},
        {"label": "Review needed", "pct": round(review / total * 100), "count": review, "color": "#c8831a"},
        {"label": "Low confidence", "pct": round(low / total * 100), "count": low, "color": "#b64242"},
    ]


@router.get("/overview")
def read_overview(user: CurrentUser, db: DbSession):
    """Everything the Overview Dashboard renders."""
    parcels = db.scalar(select(func.count(Parcel.id))) or 0
    buildings = db.scalar(select(func.count(Building.id))) or 0
    volumes = db.scalar(select(func.count(Level.id))) or 0
    assets = db.scalar(select(func.count(InfraAsset.id))) or 0
    conflicts = db.scalars(select(Conflict)).all()
    active = [c for c in conflicts if c.severity != Severity.clear.value]
    critical = [c for c in conflicts if c.severity == Severity.critical.value]

    kpis = [
        {"label": "Total Parcels", "value": f"{parcels:,}"},
        {"label": "Total Buildings", "value": f"{buildings:,}"},
        {"label": "Infrastructure Assets", "value": f"{assets:,}"},
        {"label": "Active Conflicts", "value": str(len(active)), "cls": "warn", "delta": "Needs attention"},
        {"label": "Critical Conflicts", "value": str(len(critical)), "cls": "down", "delta": "Needs attention"},
        {"label": "3D Volumes", "value": f"{volumes:,}"},
    ]

    severity_order = {s.value: i for i, s in enumerate(
        [Severity.critical, Severity.high, Severity.medium, Severity.low, Severity.clear]
    )}
    top_conflicts = sorted(conflicts, key=lambda c: severity_order.get(c.severity, 9))[:3]

    datasets = db.scalars(select(Dataset).order_by(Dataset.created_at.desc()).limit(3)).all()

    recent_buildings = db.scalars(select(Building).order_by(Building.updated_at.desc()).limit(3)).all()
    recent_properties = []
    for b in recent_buildings:
        confs = [l.confidence for l in b.levels] or [0]
        recent_properties.append(
            {
                "name": b.name,
                "bid": b.slug,
                "conf": round(sum(confs) / len(confs)),
                "when": b.updated_at.strftime("%d %b %Y"),
            }
        )

    projects = []
    for p in db.scalars(select(InfraProposal).order_by(InfraProposal.created_at.desc()).limit(3)).all():
        has_conflict = bool((p.analysis or {}).get("conflicts"))
        projects.append(
            {
                "name": f"Proposed {INFRA_PROFILES[p.infra_type]['label']} "
                f"({p.from_building.name} → {p.to_building.name})",
                "status": "Conflicts flagged" if has_conflict else "Clear — pending submission",
                "pct": 20 if has_conflict else 45,
            }
        )
    metro = db.scalars(select(InfraAsset).where(InfraAsset.kind == "metro")).first()
    if metro is not None:
        projects.append(
            {
                "name": metro.name,
                "status": metro.status or "In progress",
                "pct": (metro.details or {}).get("completion_pct", 61),
            }
        )

    activities = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(6)).all()

    return {
        "jurisdiction": JURISDICTION,
        "kpis": kpis,
        "recent_conflicts": [
            {
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
            for c in top_conflicts
        ],
        "recent_datasets": [
            {"id": d.id, "name": d.name, "meta": d.meta, "state": d.state, "kind": d.kind}
            for d in datasets
        ],
        "recent_properties": recent_properties,
        "active_projects": projects,
        "activity": [activity_payload(a) for a in activities],
        "confidence_summary": _confidence_distribution(db),
    }


@router.get("/analytics")
def read_analytics(user: CurrentUser, db: DbSession):
    parcels = db.scalar(select(func.count(Parcel.id))) or 0
    buildings = db.scalar(select(func.count(Building.id))) or 0
    levels = db.scalars(select(Level)).all()
    verified = sum(1 for l in levels if l.confidence >= 90)
    conflicts = db.scalars(select(Conflict)).all()
    active = [c for c in conflicts if c.severity != Severity.clear.value]
    pending = db.scalar(
        select(func.count(ApprovalCase.id)).where(
            ApprovalCase.stage.in_(["submitted", "ai_review", "needs_correction", "officer_review"])
        )
    ) or 0
    assets = db.scalar(select(func.count(InfraAsset.id))) or 0
    avg_conf = round(sum(l.confidence for l in levels) / len(levels), 1) if levels else 0.0

    kpis = [
        {"label": "Parent parcels", "value": f"{parcels:,}"},
        {"label": "Buildings digitized", "value": f"{buildings:,}"},
        {"label": "3D volumes generated", "value": f"{len(levels):,}"},
        {"label": "Verified records", "value": f"{verified:,}"},
        {"label": "Conflict count", "value": str(len(active))},
        {"label": "Pending approvals", "value": str(pending)},
        {"label": "Underground assets mapped", "value": str(assets)},
        {"label": "Avg. validation confidence", "value": str(avg_conf)},
    ]

    # Conflicts per ward, derived from the buildings they're attached to.
    ward_counts: dict[str, int] = {}
    for c in active:
        ward = c.building.ward if c.building and c.building.ward else "Unassigned"
        ward_counts[ward] = ward_counts.get(ward, 0) + 1
    ward_conflicts = [
        {"ward": w, "count": n} for w, n in sorted(ward_counts.items(), key=lambda kv: -kv[1])
    ]

    severity_order = {s.value: i for i, s in enumerate(
        [Severity.critical, Severity.high, Severity.medium, Severity.low]
    )}
    priority = [
        f"{c.conflict_type} — {c.property_name}"
        for c in sorted(active, key=lambda c: severity_order.get(c.severity, 9))[:4]
    ]

    # Approval throughput by week of submission (real counts from the case table).
    cases = db.scalars(select(ApprovalCase)).all()
    weeks: dict[str, dict] = {}
    for c in cases:
        key = c.created_at.strftime("%Y-W%W")
        bucket = weeks.setdefault(key, {"label": c.created_at.strftime("W%W"), "surveyed": 0, "approved": 0})
        bucket["surveyed"] += 1
        if c.stage in {"approved", "published"}:
            bucket["approved"] += 1
    trend = [weeks[k] for k in sorted(weeks)]

    litigation = [
        {"title": c.conflict_type + " — " + c.property_name, "status": c.status}
        for c in active
        if c.severity in {Severity.critical.value, Severity.high.value}
    ]

    return {
        "kpis": kpis,
        "trend": trend,
        "confidence_distribution": _confidence_distribution(db),
        "ward_conflicts": ward_conflicts,
        "priority_queue": priority,
        "tax_realization": [
            {"period": "Q1", "demand": 74, "realized": 62},
            {"period": "Q2", "demand": 78, "realized": 69},
            {"period": "Q3", "demand": 81, "realized": 75},
            {"period": "Q4", "demand": 86, "realized": 80},
        ],
        "litigation": litigation,
        "dilrmp": [
            {"label": "Parcel digitization sync", "pct": 94},
            {"label": "Record integration (State DLR)", "pct": 81},
            {"label": "Mutation sync", "pct": 67},
        ],
    }


@router.get("/reports")
def list_reports(user: CurrentUser):
    """Report catalogue on the Reports tab."""
    return REPORTS


@router.get("/reports/{report_name}/export")
def export_report(
    report_name: str,
    user: CurrentUser,
    db: DbSession,
    fmt: str = Query("PDF", pattern="^(PDF|CSV|GeoJSON|CityGML)$"),
):
    """Records an export request and returns the row counts that would be included.

    Binary rendering (PDF/CityGML writers) is out of scope for this prototype backend —
    the endpoint returns the real dataset so the frontend can confirm the export.
    """
    known = {r["name"].lower(): r for r in REPORTS}
    report = known.get(report_name.lower())
    if report is None:
        from fastapi import HTTPException, status as st

        raise HTTPException(status_code=st.HTTP_404_NOT_FOUND, detail="Unknown report")
    if fmt not in report["formats"]:
        from fastapi import HTTPException, status as st

        raise HTTPException(
            status_code=st.HTTP_400_BAD_REQUEST,
            detail=f"{report['name']} supports: {', '.join(report['formats'])}",
        )
    return {
        "report": report["name"],
        "format": fmt,
        "generated_for": user.email,
        "row_counts": {
            "parcels": db.scalar(select(func.count(Parcel.id))) or 0,
            "buildings": db.scalar(select(func.count(Building.id))) or 0,
            "volumes": db.scalar(select(func.count(Level.id))) or 0,
            "conflicts": db.scalar(select(func.count(Conflict.id))) or 0,
            "approval_cases": db.scalar(select(func.count(ApprovalCase.id))) or 0,
        },
    }


@router.get("/activity")
def list_activity(
    user: CurrentUser,
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
):
    rows = db.scalars(select(Activity).order_by(Activity.created_at.desc()).limit(limit)).all()
    return [activity_payload(a) for a in rows]
