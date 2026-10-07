"""API route handlers for /api/files/.

This module is intentionally thin: it only handles HTTP concerns (parsing
requests, returning responses, status codes). All business logic lives in
the service layer.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, UnsupportedExtensionError
from app.db.models import Feature, UploadedFile
from app.db.session import get_db
from app.schemas.file import FileDetailOut, FileListOut, FileOut
from app.schemas.measurement import FeatureOut, MeasurementOut, MeasurementsResponse, Summary
from app.services import processor as proc_svc
from app.services import storage as storage_svc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


# ---------------------------------------------------------------------------
# POST /api/files/
# ---------------------------------------------------------------------------


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=FileOut,
    summary="Upload a geospatial file",
    description="Upload a .zip (Shapefile) or .kml file for feature extraction and measurement.",
)
async def upload_file(
    file: Annotated[UploadFile, File(description="Geospatial file (.zip or .kml)")],
    db: Session = Depends(get_db),
) -> FileOut:
    """Handle multipart upload, validate, process, and return the created record."""
    filename = file.filename or "upload"

    # Validate extension before reading bytes
    from pathlib import Path
    suffix = Path(filename).suffix.lower()
    if suffix not in proc_svc.ALLOWED_EXTENSIONS:
        raise UnsupportedExtensionError(
            f"File extension {suffix!r} is not supported. "
            f"Allowed: {sorted(proc_svc.ALLOWED_EXTENSIONS)}"
        )

    db_file = proc_svc.process_upload(
        file_obj=file.file,
        filename=filename,
        db=db,
    )
    return FileOut.model_validate(db_file)


# ---------------------------------------------------------------------------
# GET /api/files/
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response_model=FileListOut,
    summary="List uploaded files",
    description="Returns all uploaded files, newest first, with pagination.",
)
def list_files(
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size")] = 20,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    db: Session = Depends(get_db),
) -> FileListOut:
    """Return a paginated list of all uploaded files."""
    total = db.scalar(select(func.count(UploadedFile.id))) or 0
    rows = (
        db.scalars(
            select(UploadedFile)
            .order_by(UploadedFile.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        .all()
    )
    return FileListOut(
        total=total,
        limit=limit,
        offset=offset,
        items=[FileDetailOut.model_validate(r) for r in rows],
    )


# ---------------------------------------------------------------------------
# GET /api/files/{id}/
# ---------------------------------------------------------------------------


@router.get(
    "/{file_id}/",
    response_model=FileDetailOut,
    summary="Get file details",
    description="Retrieve metadata for a specific uploaded file by UUID.",
)
def get_file(
    file_id: str,
    db: Session = Depends(get_db),
) -> FileDetailOut:
    """Return details for a single uploaded file."""
    db_file = db.get(UploadedFile, file_id)
    if db_file is None:
        raise NotFoundError(f"File with id={file_id!r} not found.")
    return FileDetailOut.model_validate(db_file)


# ---------------------------------------------------------------------------
# GET /api/files/{id}/measurements/
# ---------------------------------------------------------------------------


def _build_summary(file_id: str, db: Session) -> Summary:
    """Compute file-wide summary statistics across ALL features."""
    rows = db.scalars(
        select(Feature).where(Feature.file_id == file_id)
    ).all()

    total_area = 0.0
    total_length = 0.0
    unsupported = 0
    failed = 0
    by_type: dict[str, int] = {}

    for r in rows:
        gt = r.geometry_type or "Unknown"
        by_type[gt] = by_type.get(gt, 0) + 1
        if r.measurement_status == "UNSUPPORTED":
            unsupported += 1
        elif r.measurement_status == "FAILED":
            failed += 1
        if r.measurement_type == "area" and r.measurement_value is not None:
            total_area += r.measurement_value
        elif r.measurement_type == "length" and r.measurement_value is not None:
            total_length += r.measurement_value

    return Summary(
        total_area_m2=total_area,
        total_length_m=total_length,
        unsupported=unsupported,
        failed=failed,
        by_geometry_type=by_type,
    )


def _feature_orm_to_out(f: Feature) -> FeatureOut:
    """Convert a Feature ORM object to a FeatureOut Pydantic model."""
    measurement = MeasurementOut(
        type=f.measurement_type,
        value=f.measurement_value,
        unit=f.measurement_unit,
        projected_crs=f.projected_crs,
        status=f.measurement_status,
        note=f.note,
    )
    return FeatureOut(
        index=f.feature_index,
        geometry_type=f.geometry_type,
        crs=f.crs,
        properties=f.properties,
        geometry=f.geometry,
        measurement=measurement,
    )


@router.get(
    "/{file_id}/measurements/",
    response_model=MeasurementsResponse,
    summary="Get measurements for a file",
    description=(
        "Returns per-feature measurements plus a file-wide summary. "
        "Supports pagination and filtering by geometry_type."
    ),
)
def get_measurements(
    file_id: str,
    limit: Annotated[int, Query(ge=1, le=1000, description="Page size")] = 100,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
    geometry_type: Annotated[
        Optional[str],
        Query(description="Filter by geometry type (e.g. Polygon, LineString)"),
    ] = None,
    db: Session = Depends(get_db),
) -> MeasurementsResponse:
    """Return paginated features with measurements and a whole-file summary."""
    # Validate file exists
    db_file = db.get(UploadedFile, file_id)
    if db_file is None:
        raise NotFoundError(f"File with id={file_id!r} not found.")

    # Base query
    base_q = select(Feature).where(Feature.file_id == file_id)
    if geometry_type:
        base_q = base_q.where(Feature.geometry_type == geometry_type)

    total = db.scalar(
        select(func.count()).select_from(base_q.subquery())
    ) or 0

    page_rows = db.scalars(
        base_q.order_by(Feature.feature_index).limit(limit).offset(offset)
    ).all()

    # Summary always covers the whole file (ignores geometry_type filter)
    summary = _build_summary(file_id, db)

    features = [_feature_orm_to_out(f) for f in page_rows]

    return MeasurementsResponse(
        file_id=file_id,
        total=total,
        summary=summary,
        features=features,
    )


# ---------------------------------------------------------------------------
# DELETE /api/files/{id}/
# ---------------------------------------------------------------------------


@router.delete(
    "/{file_id}/",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a file",
    description="Remove a file record and all associated features and stored files.",
)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db),
) -> None:
    """Delete a file and all its features from the DB and storage."""
    db_file = db.get(UploadedFile, file_id)
    if db_file is None:
        raise NotFoundError(f"File with id={file_id!r} not found.")

    # Remove stored files
    storage_svc.delete_upload_dir(file_id)

    # Delete DB record (cascades to features)
    db.delete(db_file)
    db.commit()
    logger.info("Deleted file record and storage for file_id=%s", file_id)
