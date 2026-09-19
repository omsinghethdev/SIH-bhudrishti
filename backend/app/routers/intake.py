"""Survey & Data Intake: dataset uploads, processing pipeline, AI floor-segmentation review."""
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from ..config import settings
from ..dependencies import CurrentUser, DbSession, PlannerUser, SurveyorUser
from ..models import Dataset, FloorSegment
from ..schemas.auth import MessageOut
from ..schemas.operations import FloorSegmentUpdate
from ..services.activity import log_activity
from ..services.cadastre import get_building_or_404

router = APIRouter(prefix="/api", tags=["intake"])

# Extension -> (dataset kind, human label). Matches the dropzone's advertised formats.
ALLOWED_TYPES = {
    ".geojson": ("geojson", "GeoJSON"),
    ".json": ("geojson", "GeoJSON"),
    ".shp": ("shapefile", "Shapefile"),
    ".zip": ("shapefile", "Shapefile bundle"),
    ".dxf": ("cad", "CAD drawing"),
    ".dwg": ("cad", "CAD drawing"),
    ".las": ("lidar", "LiDAR point cloud"),
    ".laz": ("lidar", "LiDAR point cloud"),
    ".tif": ("orthophoto", "Orthophoto"),
    ".tiff": ("orthophoto", "Orthophoto"),
    ".pdf": ("floorplan", "Floor plan"),
    ".png": ("floorplan", "Floor plan image"),
    ".jpg": ("floorplan", "Floor plan image"),
    ".jpeg": ("floorplan", "Floor plan image"),
    ".csv": ("gnss", "GNSS points"),
    ".txt": ("gnss", "GNSS points"),
}

PIPELINE_STAGES = [
    "Upload complete",
    "Coordinate reference detected",
    "Point cloud classified",
    "Building envelope extracted",
    "Floor bands detected",
    "AI segmentation ready for review",
]


def _human_size(size: int | None) -> str:
    if not size:
        return "unknown size"
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{size} B"
        size /= 1024
    return f"{size:.1f} GB"


def _dataset_out(d: Dataset) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "meta": d.meta,
        "state": d.state,
        "kind": d.kind,
        "crs": d.crs,
        "url": d.url,
        "size_bytes": d.size_bytes,
        "created_at": d.created_at,
    }


@router.get("/datasets")
def list_datasets(
    user: CurrentUser,
    db: DbSession,
    building: str | None = Query(None, description="Building slug"),
    kind: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    stmt = select(Dataset)
    if building:
        stmt = stmt.where(Dataset.building_id == get_building_or_404(db, building).id)
    if kind:
        stmt = stmt.where(Dataset.kind == kind)
    rows = db.scalars(stmt.order_by(Dataset.created_at.desc())).all()
    total = len(rows)
    start = (page - 1) * page_size
    return {
        "items": [_dataset_out(d) for d in rows[start : start + page_size]],
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": max(1, (total + page_size - 1) // page_size),
    }


@router.post("/datasets", status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    surveyor: SurveyorUser,
    db: DbSession,
    file: UploadFile = File(..., description="Survey file (GeoJSON, LAS, CAD, PDF, orthophoto, GNSS)"),
    building_slug: str | None = Form(None),
    crs: str | None = Form("EPSG:4326"),
    kind: str | None = Form(None),
):
    """Handles the intake dropzone / 'Browse files' upload. Stored on local disk for now."""
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A filename is required")
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_TYPES))}",
        )
    detected_kind, label = ALLOWED_TYPES[suffix]

    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{suffix}"
    stored_path = upload_dir / stored_name

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    with stored_path.open("wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                stored_path.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the {settings.max_upload_mb} MB limit",
                )
            out.write(chunk)

    building = get_building_or_404(db, building_slug) if building_slug else None
    dataset = Dataset(
        name=file.filename,
        stored_path=str(stored_path),
        url=f"/uploads/{stored_name}",
        content_type=file.content_type,
        size_bytes=size,
        kind=kind or detected_kind,
        crs=crs,
        meta=f"{_human_size(size)} · {label} · {crs or 'CRS unknown'}",
        state="Coordinate reference detected" if crs else "Upload complete",
        building_id=building.id if building else None,
        uploaded_by_id=surveyor.id,
    )
    db.add(dataset)
    db.flush()

    # LiDAR passes produce AI floor-band candidates for human review.
    if dataset.kind == "lidar" and building is not None:
        for i, level in enumerate(building.levels):
            db.add(
                FloorSegment(
                    dataset_id=dataset.id,
                    building_id=building.id,
                    label=level.label,
                    confidence=level.confidence,
                    note=(
                        "Overlaps utility buffer — awaiting surveyor confirmation."
                        if level.has_conflict
                        else "Boundary matches submitted plan within tolerance."
                    ),
                    sort_order=i,
                )
            )
        dataset.state = "AI segmentation ready"

    log_activity(db, f"{dataset.name} uploaded for processing", "info", surveyor)
    db.commit()
    db.refresh(dataset)
    return _dataset_out(dataset)


@router.get("/datasets/{dataset_id}")
def read_dataset(dataset_id: int, user: CurrentUser, db: DbSession):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    return _dataset_out(dataset)


@router.delete("/datasets/{dataset_id}", response_model=MessageOut)
def delete_dataset(dataset_id: int, surveyor: SurveyorUser, db: DbSession):
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    if dataset.uploaded_by_id not in (None, surveyor.id) and surveyor.role.value != "planner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete datasets you uploaded"
        )
    if dataset.stored_path:
        Path(dataset.stored_path).unlink(missing_ok=True)
    name = dataset.name
    db.delete(dataset)
    db.commit()
    return MessageOut(detail=f"{name} deleted")


@router.get("/datasets/{dataset_id}/pipeline")
def read_pipeline(dataset_id: int, user: CurrentUser, db: DbSession):
    """Processing-pipeline stage list for the intake page."""
    dataset = db.get(Dataset, dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")
    reached = PIPELINE_STAGES.index(
        dataset.state if dataset.state in PIPELINE_STAGES else PIPELINE_STAGES[0]
    )
    if dataset.state == "AI segmentation ready":
        reached = len(PIPELINE_STAGES) - 1
    return {
        "dataset_id": dataset.id,
        "stages": [
            {"name": s, "status": "done" if i < reached else "active" if i == reached else "pending"}
            for i, s in enumerate(PIPELINE_STAGES)
        ],
    }


# ------------------------------------------------- AI floor segmentation review
@router.get("/floor-segments")
def list_floor_segments(
    user: CurrentUser,
    db: DbSession,
    dataset_id: int | None = None,
    building: str | None = None,
):
    stmt = select(FloorSegment)
    if dataset_id is not None:
        stmt = stmt.where(FloorSegment.dataset_id == dataset_id)
    if building:
        stmt = stmt.where(FloorSegment.building_id == get_building_or_404(db, building).id)
    rows = db.scalars(stmt.order_by(FloorSegment.sort_order, FloorSegment.id)).all()
    return [
        {
            "id": s.id,
            "label": s.label,
            "conf": s.confidence,
            "note": s.note,
            "review_status": s.review_status,
            "dataset_id": s.dataset_id,
        }
        for s in rows
    ]


@router.patch("/floor-segments/{segment_id}")
def update_floor_segment(
    segment_id: int, payload: FloorSegmentUpdate, surveyor: SurveyorUser, db: DbSession
):
    """Corrections applied during AI-output review."""
    segment = db.get(FloorSegment, segment_id)
    if segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Floor segment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(segment, field, value)
    db.commit()
    db.refresh(segment)
    return {
        "id": segment.id,
        "label": segment.label,
        "conf": segment.confidence,
        "note": segment.note,
        "review_status": segment.review_status,
        "dataset_id": segment.dataset_id,
    }


@router.post("/floor-segments/submit")
def submit_segmentation(
    surveyor: SurveyorUser,
    db: DbSession,
    dataset_id: int | None = None,
    building: str | None = None,
):
    """'Submit for Surveyor Verification' — accepts the reviewed floor bands."""
    stmt = select(FloorSegment).where(FloorSegment.review_status == "pending")
    if dataset_id is not None:
        stmt = stmt.where(FloorSegment.dataset_id == dataset_id)
    if building:
        stmt = stmt.where(FloorSegment.building_id == get_building_or_404(db, building).id)
    segments = db.scalars(stmt).all()
    if not segments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No pending floor segments to submit"
        )
    for s in segments:
        s.review_status = "accepted"
    if dataset_id is not None:
        dataset = db.get(Dataset, dataset_id)
        if dataset is not None:
            dataset.state = "Submitted for verification"
    log_activity(db, f"{len(segments)} floor bands submitted for surveyor verification", "info", surveyor)
    db.commit()
    return {"submitted": len(segments), "detail": "Segmentation submitted for surveyor verification"}


@router.post("/floor-segments/reject", response_model=MessageOut)
def reject_segmentation(admin: PlannerUser, db: DbSession, dataset_id: int):
    """'Reject AI Output' — discards the generated floor bands for a dataset."""
    segments = db.scalars(select(FloorSegment).where(FloorSegment.dataset_id == dataset_id)).all()
    if not segments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No floor segments for dataset")
    for s in segments:
        s.review_status = "rejected"
    dataset = db.get(Dataset, dataset_id)
    if dataset is not None:
        dataset.state = "AI output rejected — re-processing required"
    log_activity(db, "AI floor segmentation rejected", "warning", admin)
    db.commit()
    return MessageOut(detail="AI output rejected")
