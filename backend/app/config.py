"""Application configuration loaded from environment variables (.env supported)."""
from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Security
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # Database (SQLite for now; swap for a PostgreSQL URL later)
    database_url: str = f"sqlite:///{BACKEND_DIR / 'bhudrishti.db'}"

    # CORS — the frontend origin(s), comma separated
    frontend_url: str = (
        "http://localhost:8000,http://127.0.0.1:8000,"
        "http://localhost:5500,http://127.0.0.1:5500,"
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:5173,http://127.0.0.1:5173"
    )

    # Uploads
    upload_dir: str = str(BACKEND_DIR / "uploads")
    max_upload_mb: int = 200

    class Config:
        env_file = BACKEND_DIR / ".env"
        env_file_encoding = "utf-8"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.frontend_url.split(",") if o.strip()]


settings = Settings()
