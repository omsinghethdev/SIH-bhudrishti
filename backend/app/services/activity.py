"""Activity feed helpers."""
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..models import Activity, User


def log_activity(db: Session, text: str, tone: str = "info", actor: User | None = None) -> Activity:
    entry = Activity(text=text, tone=tone, actor_id=actor.id if actor else None)
    db.add(entry)
    db.flush()
    return entry


def relative_time(when: datetime) -> str:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - when).total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} min ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hr ago"
    days = int(hours // 24)
    if days == 1:
        return "Yesterday"
    if days < 7:
        return f"{days} days ago"
    weeks = days // 7
    if weeks < 5:
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    return when.strftime("%d %b %Y")


TONE_COLORS = {
    "success": "var(--success)",
    "error": "var(--error)",
    "warning": "var(--warning)",
    "info": "var(--info)",
}


def activity_payload(entry: Activity) -> dict:
    return {
        "id": entry.id,
        "t": entry.text,
        "tone": entry.tone,
        "c": TONE_COLORS.get(entry.tone, TONE_COLORS["info"]),
        "time": relative_time(entry.created_at),
        "created_at": entry.created_at,
    }
