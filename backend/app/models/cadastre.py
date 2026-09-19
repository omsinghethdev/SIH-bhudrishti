"""Cadastral records: parcels, buildings, vertical levels, locality infrastructure assets."""
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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .user import utcnow


class Parcel(Base):
    """A 2D land parcel identified by its parent ULPIN / Bhu-Aadhaar."""

    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ulpin: Mapped[str] = mapped_column(String(40), unique=True, index=True, nullable=False)
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    ward: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    registered_area: Mapped[str | None] = mapped_column(String(40), nullable=True)
    khasra_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    migration_status: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    buildings: Mapped[list["Building"]] = relationship(
        back_populates="parcel", cascade="all, delete-orphan"
    )


class Building(Base):
    """A digitized building on a parcel. `slug` matches the frontend's building ids."""

    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="CASCADE"), index=True, nullable=False
    )

    address: Mapped[str] = mapped_column(String(255), nullable=False)
    ward: Mapped[str | None] = mapped_column(String(60), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    survey_no: Mapped[str | None] = mapped_column(String(60), nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    floors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    basements: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    land_use: Mapped[str | None] = mapped_column(String(80), nullable=True)
    use_category: Mapped[str | None] = mapped_column(String(40), nullable=True)  # residential/commercial/mixed
    ownership_type: Mapped[str | None] = mapped_column(String(160), nullable=True)
    boundary_dims: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    validation_status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    survey_accuracy: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gnss: Mapped[str | None] = mapped_column(String(120), nullable=True)
    lidar_availability: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Infrastructure context shown in the explorer detail panel.
    infra: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Schematic locality-map footprint (x, y, w, h in the frontend's 700x420 space).
    map_geometry: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    road_info: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    parcel: Mapped[Parcel] = relationship(back_populates="buildings")
    levels: Mapped[list["Level"]] = relationship(
        back_populates="building",
        cascade="all, delete-orphan",
        order_by="Level.sort_order",
    )


class Level(Base):
    """One vertical level (floor, terrace, basement) of a building — a 3D volume record."""

    __tablename__ = "levels"
    __table_args__ = (UniqueConstraint("building_id", "code", name="uq_level_building_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. "floor4", "b2", "gf"
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    tag: Mapped[str] = mapped_column(String(12), nullable=False)
    ulpin_3d: Mapped[str] = mapped_column(String(120), index=True, nullable=False)

    property_type: Mapped[str] = mapped_column(String(120), nullable=False)
    elevation: Mapped[str] = mapped_column(String(60), nullable=False)
    elevation_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    elevation_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    area: Mapped[str | None] = mapped_column(String(40), nullable=True)
    volume: Mapped[str | None] = mapped_column(String(40), nullable=True)
    owner: Mapped[str | None] = mapped_column(String(160), nullable=True)
    owner_full: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    surveyed_on: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verified_on: Mapped[str | None] = mapped_column(String(40), nullable=True)
    survey_year: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    rights: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    below_grade: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    airspace: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_conflict: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rendering hints used by the frontend's isometric SVG builder.
    render_height: Mapped[int] = mapped_column(Integer, default=34, nullable=False)
    colors: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    building: Mapped[Building] = relationship(back_populates="levels")


class InfraAsset(Base):
    """Locality infrastructure: metro corridor, railway track, parks, utility lines."""

    __tablename__ = "infra_assets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # metro/rail/park/utility
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    agency: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str | None] = mapped_column(String(80), nullable=True)
    depth_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    color: Mapped[str | None] = mapped_column(String(20), nullable=True)
    condition: Mapped[str | None] = mapped_column(String(40), nullable=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    geometry: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
