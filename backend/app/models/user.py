"""User accounts and the four platform roles the frontend exposes."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class Role(str, enum.Enum):
    """Matches the values in the frontend's #roleSelect dropdown."""

    planner = "planner"        # Government / Planner — full access (admin)
    constructor = "constructor"  # Constructor / Engineer
    surveyor = "surveyor"      # Architect / Surveyor
    public = "public"          # Public User


ROLE_LABELS = {
    Role.planner: "Government / Planner",
    Role.constructor: "Constructor / Engineer",
    Role.surveyor: "Architect / Surveyor",
    Role.public: "Public User",
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.public, nullable=False, index=True)
    organization: Mapped[str | None] = mapped_column(String(160), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    @property
    def role_label(self) -> str:
        return ROLE_LABELS[self.role]
