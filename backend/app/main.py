"""BhuDrishti 3D backend — FastAPI application entrypoint."""
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from .config import settings
from .database import Base, engine
from .models import *  # noqa: F401,F403 — register mappers before create_all
from .routers import approvals, auth, cadastre, conflicts, insights, intake, meta, planning, users

app = FastAPI(
    title="BhuDrishti 3D API",
    version="1.0.0",
    description=(
        "Backend for the BhuDrishti 3D cadastre prototype: parcels, buildings, vertical "
        "property volumes, conflict detection, approvals, survey intake and analytics.\n\n"
        "Authenticate with `POST /api/auth/login`, then send `Authorization: Bearer <token>`."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Registration, login, current user, logout."},
        {"name": "users", "description": "User & role management (planner only) and the permission matrix."},
        {"name": "cadastre", "description": "Locality map, parcels, buildings, levels, search, passport."},
        {"name": "conflicts", "description": "Conflict Radar: listing, stats, validation runs, resolution."},
        {"name": "approvals", "description": "Approval workflow board and officer decisions."},
        {"name": "intake", "description": "Survey dataset uploads and AI floor-segmentation review."},
        {"name": "planning", "description": "Proposed infrastructure, dig-safe checks, 3D ULPIN wizard."},
        {"name": "insights", "description": "Overview dashboard, analytics, reports, activity feed."},
        {"name": "settings", "description": "Jurisdiction, CRS, LADM and legacy ID mapping."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

# Uploaded survey files are served back at the URLs stored on each dataset row.
upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

for r in (auth, users, cadastre, conflicts, approvals, intake, planning, insights, meta):
    app.include_router(r.router)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Consistent 422 shape: {"detail": "...", "errors": [{field, message}]}."""
    errors = [
        {"field": ".".join(str(p) for p in err["loc"][1:]) or "body", "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation failed", "errors": errors},
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    """Surface DB constraint violations as 409 rather than a 500."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "That record conflicts with an existing one (duplicate or invalid reference)"},
    )


@app.get("/api/health", tags=["insights"])
def health():
    # Never echo the raw URL: a PostgreSQL DSN carries the password, and this
    # endpoint is unauthenticated (it is what the load balancer polls).
    url = make_url(settings.database_url)
    return {"status": "ok", "database": f"{url.get_backend_name()}:{url.database}"}
