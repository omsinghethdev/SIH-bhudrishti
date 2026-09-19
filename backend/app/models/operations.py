"""Operational records: conflicts, approval cases, survey datasets, activity, proposals."""
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .user import utcnow


class Severity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    clear = "clear"


SEVERITY_RANK = {
    Severity.clear: 0,
    Severity.low: 1,
    Severity.medium: 2,
    Severity.high: 3,
    Severity.critical: 4,
}


class Conflict(Base):
    """A volumetric / regulatory conflict raised against a property record."""

    __tablename__ = "conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    severity: Mapped[Severity] = mapped_column(
        String(20), default=Severity.medium.value, nullable=False, index=True
    )
    conflict_type: Mapped[str] = mapped_column(String(200), nullable=False)
    property_name: Mapped[str] = mapped_column(String(200), nullable=False)
    building_floor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    overlap_volume: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="Pending Review", nullable=False, index=True)
    officer: Mapped[str] = mapped_column(String(120), default="Unassigned", nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    rule: Mapped[str] = mapped_column(Text, nullable=False)

    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    level_id: Mapped[int | None] = mapped_column(
        ForeignKey("levels.id", ondelete="SET NULL"), index=True, nullable=True
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    building = relationship("Building")
    level = relationship("Level")


APPROVAL_STAGES = [
    ("submitted", "Submitted by Surveyor"),
    ("ai_review", "AI Review Complete"),
    ("needs_correction", "Needs Correction"),
    ("officer_review", "Under Officer Review"),
    ("approved", "Approved"),
    ("published", "Published"),
    ("rejected", "Rejected"),
]
APPROVAL_STAGE_LABELS = dict(APPROVAL_STAGES)


class ApprovalCase(Base):
    """A submitted 3D property record moving through the approval workflow."""

    __tablename__ = "approval_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ulpin_3d: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    stage: Mapped[str] = mapped_column(String(40), default="submitted", nullable=False, index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sla: Mapped[str | None] = mapped_column(String(60), nullable=True)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ward: Mapped[str | None] = mapped_column(String(60), nullable=True)
    surveyor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    urgency: Mapped[str | None] = mapped_column(String(40), nullable=True)
    surveyor_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    submitted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    events: Mapped[list["CaseEvent"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="CaseEvent.created_at"
    )


class CaseEvent(Base):
    """Audit-trail entry for an approval case."""

    __tablename__ = "case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("approval_cases.id", ondelete="CASCADE"), index=True, nullable=False
    )
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    actor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    case: Mapped[ApprovalCase] = relationship(back_populates="events")


class Dataset(Base):
    """An uploaded survey / LiDAR / floor-plan dataset."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    kind: Mapped[str | None] = mapped_column(String(60), nullable=True)  # lidar/floorplan/geojson/orthophoto
    crs: Mapped[str | None] = mapped_column(String(40), nullable=True)
    meta: Mapped[str | None] = mapped_column(String(255), nullable=True)  # human-readable meta line
    state: Mapped[str] = mapped_column(String(80), default="Upload complete", nullable=False)

    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    uploaded_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    segments: Mapped[list["FloorSegment"]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class FloorSegment(Base):
    """An AI-detected floor band awaiting human verification."""

    __tablename__ = "floor_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset_id: Mapped[int | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    building_id: Mapped[int | None] = mapped_column(
        ForeignKey("buildings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_status: Mapped[str] = mapped_column(String(40), default="pending", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    dataset: Mapped[Dataset | None] = relationship(back_populates="segments")


class Activity(Base):
    """Recent-activity feed entry."""

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    tone: Mapped[str] = mapped_column(String(20), default="info", nullable=False)  # success/error/info/warning
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class InfraProposal(Base):
    """A proposed metro / pipeline / utility route plus its stored conflict analysis."""

    __tablename__ = "infra_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    infra_type: Mapped[str] = mapped_column(String(40), nullable=False)  # metro/water/sewer/gas/fibre
    from_building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    to_building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False
    )
    width_m: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    depth_m: Mapped[float] = mapped_column(Float, default=18.0, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="draft", nullable=False)
    analysis: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    from_building = relationship("Building", foreign_keys=[from_building_id])
    to_building = relationship("Building", foreign_keys=[to_building_id])
