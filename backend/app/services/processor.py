"""Processing orchestrator.

Ties together file storage, reading, measurement, and DB persistence.
Designed to be called synchronously from a route handler but structured
so that it can be trivially moved to a BackgroundTask or Celery worker.
"""

from __future__ import annotations

import json
import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

import geopandas as gpd
from sqlalchemy.orm import Session

from app.core.errors import FileTooLargeError, InvalidFileError, UnsupportedExtensionError
from app.db.models import Feature, UploadedFile
from app.services import measurements as measure_svc
from app.services import storage as storage_svc
from app.services.readers import read_kml, read_shapefile_zip
from app.utils.geometry import force_2d, repair_geometry, sanitise_properties, to_geojson

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = frozenset({".zip", ".kml"})


def _detect_file_type(filename: str) -> str:
    """Map a filename extension to a file-type label.

    Parameters
    ----------
    filename:
        The original filename (extension is used).

    Returns
    -------
    str
        ``"shapefile"`` or ``"kml"``.

    Raises
    ------
    UnsupportedExtensionError
        If the extension is not in the allowed set.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedExtensionError(
            f"File extension {suffix!r} is not supported. "
            f"Allowed extensions: {sorted(ALLOWED_EXTENSIONS)}"
        )
    return "shapefile" if suffix == ".zip" else "kml"


def _read_geodataframe(file_path: Path, file_type: str, extract_dir: Path) -> gpd.GeoDataFrame:
    """Dispatch to the correct reader based on file type.

    Parameters
    ----------
    file_path:
        Path to the uploaded file.
    file_type:
        ``"shapefile"`` or ``"kml"``.
    extract_dir:
        Temporary directory for shapefile extraction.

    Returns
    -------
    GeoDataFrame
    """
    if file_type == "kml":
        return read_kml(file_path)
    # shapefile
    return read_shapefile_zip(file_path, extract_dir=extract_dir)


def _build_feature_row(
    file_id: str,
    idx: int,
    row: gpd.GeoSeries,
    src_crs: str,
) -> Feature:
    """Build a ``Feature`` ORM object from a GeoDataFrame row.

    Parameters
    ----------
    file_id:
        Parent ``UploadedFile`` UUID.
    idx:
        Zero-based feature index.
    row:
        A row from a GeoDataFrame (Series with a ``geometry`` key).
    src_crs:
        Source CRS string (e.g. ``"EPSG:4326"``).

    Returns
    -------
    Feature
        An unsaved ORM object.
    """
    geom = row.get("geometry")

    note: str | None = None
    geom_type: str | None = None

    if geom is not None and not geom.is_empty:
        # Strip Z
        geom = force_2d(geom)
        # Repair invalid polygons
        geom, repair_note = repair_geometry(geom)
        if repair_note:
            note = repair_note
        geom_type = geom.geom_type

    # Compute measurement (never raises)
    m = measure_svc.measure(geom, src_crs)

    # Merge notes
    if m.get("note") and note:
        combined_note = f"{note}; {m['note']}"
    elif m.get("note"):
        combined_note = m["note"]
    else:
        combined_note = note

    # Build properties (excluding geometry column)
    props = {k: v for k, v in row.items() if k != "geometry"}
    safe_props = sanitise_properties(props)

    return Feature(
        file_id=file_id,
        feature_index=idx,
        geometry_type=geom_type,
        geometry=json.dumps(to_geojson(geom)) if geom is not None else None,
        crs=src_crs,
        properties=json.dumps(safe_props),
        measurement_type=m["type"],
        measurement_value=m["value"],
        measurement_unit=m["unit"],
        projected_crs=m["projected_crs"],
        measurement_status=m["status"],
        note=combined_note,
    )


def process_upload(
    file_obj: BinaryIO,
    filename: str,
    db: Session,
) -> UploadedFile:
    """Full pipeline: validate → save → read → measure → persist.

    Parameters
    ----------
    file_obj:
        Raw file bytes stream from the multipart upload.
    filename:
        Original client-supplied filename.
    db:
        SQLAlchemy session (caller manages commit/rollback).

    Returns
    -------
    UploadedFile
        The completed (status=COMPLETED) DB record.

    Raises
    ------
    UnsupportedExtensionError
        If the extension is not allowed.
    FileTooLargeError
        If the file exceeds the size limit.
    InvalidFileError
        If the file is structurally invalid.
    """
    file_id = str(uuid.uuid4())
    file_type = _detect_file_type(filename)

    # Create DB row immediately so we have an ID to work with
    db_file = UploadedFile(
        id=file_id,
        filename=storage_svc.sanitise_filename(filename),
        file_type=file_type,
        status="PROCESSING",
        created_at=datetime.now(UTC),
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    saved_path: Path | None = None
    extract_tmp: tempfile.TemporaryDirectory | None = None

    try:
        # Save file to disk
        saved_path = storage_svc.save_upload(file_obj, filename, file_id)

        # Extract dir for shapefiles
        extract_tmp = tempfile.TemporaryDirectory(prefix="geo_extract_")
        extract_dir = Path(extract_tmp.name)

        # Read into GeoDataFrame
        gdf = _read_geodataframe(saved_path, file_type, extract_dir)

        src_crs = str(gdf.crs) if gdf.crs else "EPSG:4326"
        feature_rows: list[Feature] = []

        # Process each feature; one bad feature must not fail the whole file
        for idx, row in enumerate(gdf.itertuples(index=False)):
            try:
                row_dict = row._asdict()
                feature_row = _build_feature_row(file_id, idx, row_dict, src_crs)
                feature_rows.append(feature_row)
            except Exception as exc:
                logger.error(
                    "Feature %d in file %s failed: %s", idx, file_id, exc, exc_info=True
                )
                # Insert a FAILED placeholder
                feature_rows.append(
                    Feature(
                        file_id=file_id,
                        feature_index=idx,
                        geometry_type=None,
                        geometry=None,
                        crs=src_crs,
                        properties=None,
                        measurement_type=None,
                        measurement_value=None,
                        measurement_unit=None,
                        projected_crs=None,
                        measurement_status="FAILED",
                        note=f"Feature processing error: {exc!s}",
                    )
                )

        # Bulk insert
        db.bulk_save_objects(feature_rows)

        # Mark completed
        db_file.status = "COMPLETED"
        db_file.crs = src_crs
        db_file.feature_count = len(feature_rows)
        db.commit()
        db.refresh(db_file)

        logger.info(
            "File %s processed successfully: %d features, CRS=%s",
            file_id,
            len(feature_rows),
            src_crs,
        )
        return db_file

    except (UnsupportedExtensionError, FileTooLargeError, InvalidFileError) as exc:
        # Mark as FAILED in DB, then re-raise so the route handler can return 4xx
        db_file.status = "FAILED"
        db_file.error_message = exc.detail
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise

    except Exception as exc:
        logger.exception("Unexpected error processing file %s: %s", file_id, exc)
        db_file.status = "FAILED"
        db_file.error_message = f"Internal processing error: {exc!s}"
        try:
            db.commit()
        except Exception:
            db.rollback()
        raise InvalidFileError(f"File processing failed: {exc!s}") from exc

    finally:
        # Clean up temp extraction dir
        if extract_tmp is not None:
            try:
                extract_tmp.cleanup()
            except Exception:
                logger.warning("Failed to clean up extract dir")
        # On failure, remove the saved upload
        if saved_path is not None and db_file.status == "FAILED":
            storage_svc.delete_file(saved_path)
