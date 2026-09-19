"""Schemas for conflicts, approvals, intake, proposals, analytics."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from ..models.operations import Severity


class ConflictOut(BaseModel):
    """Field names match the frontend's CONFLICTS entries (sev/type/prop/bldg/vol)."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    sev: Severity = Field(validation_alias="severity", serialization_alias="sev")
    type: str = Field(validation_alias="conflict_type", serialization_alias="type")
    prop: str = Field(validation_alias="property_name", serialization_alias="prop")
    bldg: str | None = Field(validation_alias="building_floor", serialization_alias="bldg")
    vol: str | None = Field(validation_alias="overlap_volume", serialization_alias="vol")
    status: str
    officer: str
    explain: str = Field(validation_alias="explanation", serialization_alias="explain")
    rule: str
    buildingId: str | None = None
    created_at: datetime


class ConflictCreate(BaseModel):
    severity: Severity
    conflict_type: str = Field(min_length=3, max_length=200)
    property_name: str = Field(min_length=1, max_length=200)
    building_floor: str | None = Field(default=None, max_length=120)
    overlap_volume: str | None = Field(default=None, max_length=40)
    status: str = Field(default="Pending Review", max_length=80)
    officer: str = Field(default="Unassigned", max_length=120)
    explanation: str = Field(min_length=3)
    rule: str = Field(min_length=3)
    building_slug: str | None = None
    level_code: str | None = None


class ConflictUpdate(BaseModel):
    severity: Severity | None = None
    status: str | None = Field(default=None, max_length=80)
    officer: str | None = Field(default=None, max_length=120)
    explanation: str | None = None
    rule: str | None = None


class ConflictStats(BaseModel):
    total: int
    active: int
    by_severity: dict[str, int]
    critical: int
    pending_review: int
    resolved_this_month: int
    volumes_scanned: int
    topology_validity: float


class ValidationRunOut(BaseModel):
    stages: list[dict]
    total_conflicts: int
    critical: int
    volumes_scanned: int
    completed_at: datetime


class CaseEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    action: str
    note: str | None
    actor_name: str | None
    created_at: datetime


class ApprovalCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ulpin_3d: str
    title: str
    stage: str
    stage_label: str
    conf: int = Field(validation_alias="confidence", serialization_alias="conf")
    sla: str | None
    conflict: bool = Field(validation_alias="has_conflict", serialization_alias="conflict")
    ward: str | None
    surveyor: str | None
    urgency: str | None
    surveyor_notes: str | None
    created_at: datetime


class ApprovalCaseDetail(ApprovalCaseOut):
    events: list[CaseEventOut] = []


class ApprovalCaseCreate(BaseModel):
    ulpin_3d: str = Field(min_length=4, max_length=160)
    title: str = Field(min_length=2, max_length=200)
    confidence: int = Field(default=0, ge=0, le=100)
    sla: str | None = Field(default=None, max_length=60)
    has_conflict: bool = False
    ward: str | None = Field(default=None, max_length=60)
    surveyor: str | None = Field(default=None, max_length=120)
    urgency: str | None = Field(default=None, max_length=40)
    surveyor_notes: str | None = None
    building_slug: str | None = None
    stage: str = "submitted"


class ApprovalDecision(BaseModel):
    action: str = Field(pattern="^(approve|reject|return_for_correction|request_resurvey|publish)$")
    note: str | None = None


class KanbanColumn(BaseModel):
    id: str
    label: str
    cases: list[ApprovalCaseOut]


class DatasetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    meta: str | None
    state: str
    kind: str | None
    crs: str | None
    url: str | None
    size_bytes: int | None
    created_at: datetime


class FloorSegmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    conf: int = Field(validation_alias="confidence", serialization_alias="conf")
    note: str | None
    review_status: str
    dataset_id: int | None


class FloorSegmentUpdate(BaseModel):
    confidence: int | None = Field(default=None, ge=0, le=100)
    note: str | None = None
    review_status: str | None = Field(default=None, pattern="^(pending|accepted|rejected)$")


class PipelineOut(BaseModel):
    dataset_id: int | None
    stages: list[dict]


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    t: str
    tone: str
    c: str
    time: str
    created_at: datetime


class ProposalCreate(BaseModel):
    infra_type: str = Field(pattern="^(metro|water|sewer|gas|fibre)$")
    from_building: str = Field(min_length=1, max_length=60)
    to_building: str = Field(min_length=1, max_length=60)
    width_m: float = Field(default=3.0, ge=1, le=12)
    depth_m: float = Field(default=18.0, ge=1, le=35)


class ProposalOut(BaseModel):
    id: int
    infra_type: str
    infra_label: str
    from_building: str
    to_building: str
    width_m: float
    depth_m: float
    status: str
    route: dict | None
    conflicts: list[dict]
    analyzed: bool
    created_at: datetime


class DigSafeRequest(BaseModel):
    depth_m: float = Field(ge=0.1, le=30)
    footprint: str = Field(default="Basement extension — south wing", max_length=120)
    building_slug: str | None = None


class DigSafeResult(BaseModel):
    verdict: str  # clear | review | prohibited
    message: str
    conflicting_assets: list[dict]
    safety_buffer_m: float


class SpatialQueryResult(BaseModel):
    radius_m: float
    center: dict
    count: int
    conflicts: int
    results: list[dict]


class UlpinPreview(BaseModel):
    parent_ulpin: str
    building_id: str
    level_id: str
    generated_3d_id: str


class UlpinGenerateRequest(BaseModel):
    parent_ulpin: str = Field(min_length=4, max_length=40)
    building_slug: str = Field(min_length=1, max_length=60)
    building_no: str = Field(default="01", max_length=6)
    level_code: str = Field(min_length=1, max_length=40)
    level_no: str = Field(min_length=1, max_length=6)
    unit_type: str = Field(min_length=2, max_length=60)
    unit_number: str = Field(min_length=1, max_length=20)
    x: float | None = None
    y: float | None = None
    z: float | None = None
    depth_below_grade: float = Field(default=0, ge=0, le=60)
    ownership: str | None = Field(default=None, max_length=80)
    parking_entitlement: str | None = Field(default=None, max_length=80)
    common_area_access: str | None = Field(default=None, max_length=120)
    restrictions: str | None = None
    submit_for_approval: bool = True


class GeometryValidation(BaseModel):
    checks: list[dict]
    passed: bool
    conflicts_found: int
    notes: list[str]


class KpiOut(BaseModel):
    label: str
    value: str
    cls: str | None = None
    delta: str | None = None


class OverviewOut(BaseModel):
    jurisdiction: str
    kpis: list[KpiOut]
    recent_conflicts: list[ConflictOut]
    recent_datasets: list[DatasetOut]
    recent_properties: list[dict]
    active_projects: list[dict]
    activity: list[ActivityOut]
    confidence_summary: list[dict]


class AnalyticsOut(BaseModel):
    kpis: list[KpiOut]
    trend: list[dict]
    confidence_distribution: list[dict]
    ward_conflicts: list[dict]
    priority_queue: list[str]
    tax_realization: list[dict]
    litigation: list[dict]
    dilrmp: list[dict]


class ReportOut(BaseModel):
    name: str
    desc: str
    formats: list[str]
