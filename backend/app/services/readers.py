"""Geospatial file readers.

Provides two reader functions that return a ``GeoDataFrame``:

- ``read_kml(path)``   – reads all layers from a KML file.
- ``read_shapefile_zip(path)`` – safely extracts and reads a zipped Shapefile.

Both functions validate inputs rigorously and raise ``InvalidFileError`` (422)
on any structural problem.
"""

from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import Union

import geopandas as gpd
import pyogrio

from app.core.config import settings
from app.core.errors import InvalidFileError

logger = logging.getLogger(__name__)

PathLike = Union[str, Path]


# ---------------------------------------------------------------------------
# KML reader
# ---------------------------------------------------------------------------


def read_kml(path: PathLike) -> gpd.GeoDataFrame:
    """Read all layers from a KML file and return a single concatenated GeoDataFrame.

    Parameters
    ----------
    path:
        Filesystem path to the KML file.

    Returns
    -------
    GeoDataFrame
        All features across all KML layers. CRS is set to EPSG:4326.

    Raises
    ------
    InvalidFileError
        If the file cannot be read, has no layers, or has no valid features.
    """
    path = Path(path)
    logger.info("Reading KML file: %s", path)

    try:
        layers = pyogrio.list_layers(str(path))
    except Exception as exc:
        raise InvalidFileError(f"Cannot read KML file: {exc}") from exc

    if not layers:
        raise InvalidFileError("KML file contains no layers.")

    layer_frames: list[gpd.GeoDataFrame] = []
    for layer_name, _geom_type in layers:
        try:
            gdf = gpd.read_file(str(path), layer=layer_name, engine="pyogrio")
            # Drop rows with null or empty geometry
            if "geometry" in gdf.columns:
                gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
            if not gdf.empty:
                layer_frames.append(gdf)
        except Exception as exc:
            logger.warning("Skipping KML layer %r: %s", layer_name, exc)
            continue

    if not layer_frames:
        raise InvalidFileError("KML file contains no readable features with valid geometry.")

    result = gpd.pd.concat(layer_frames, ignore_index=True)
    gdf_result = gpd.GeoDataFrame(result, geometry="geometry")

    # KML is always WGS84
    gdf_result = gdf_result.set_crs("EPSG:4326", allow_override=True)

    logger.info("KML read complete: %d features.", len(gdf_result))
    return gdf_result


# ---------------------------------------------------------------------------
# Shapefile ZIP reader
# ---------------------------------------------------------------------------


def _check_zip_bomb(zip_path: Path) -> None:
    """Raise InvalidFileError if the zip archive is a zip bomb.

    Compares the total uncompressed size of all members against
    ``settings.max_uncompressed_bytes``.
    """
    limit = settings.max_uncompressed_bytes
    total = 0
    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            total += info.file_size
            if total > limit:
                raise InvalidFileError(
                    f"Zip archive uncompressed size exceeds the {settings.MAX_UNCOMPRESSED_MB} MB limit."
                )


def _safe_extract(zip_path: Path, target_dir: Path) -> None:
    """Extract a zip archive, rejecting any zip-slip path traversal attempts.

    Parameters
    ----------
    zip_path:
        Path to the zip archive.
    target_dir:
        Directory to extract into (must already exist).

    Raises
    ------
    InvalidFileError
        On zip-slip detected or corrupt archive.
    """
    target_dir_resolved = target_dir.resolve()
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                member_path = (target_dir_resolved / member.filename).resolve()
                # Zip-slip protection: resolved path must be inside target_dir
                if not str(member_path).startswith(str(target_dir_resolved) + os.sep) and \
                        member_path != target_dir_resolved:
                    raise InvalidFileError(
                        f"Zip archive contains a path traversal entry: {member.filename!r}"
                    )
            zf.extractall(target_dir_resolved)
    except zipfile.BadZipFile as exc:
        raise InvalidFileError(f"Corrupt or invalid zip archive: {exc}") from exc


def _find_shp_file(extract_dir: Path) -> Path:
    """Recursively locate the .shp file inside an extraction directory.

    Raises
    ------
    InvalidFileError
        If no .shp file or more than one .shp file is found.
    """
    shp_files = list(extract_dir.rglob("*.shp"))
    if not shp_files:
        raise InvalidFileError("No .shp file found inside the zip archive.")
    if len(shp_files) > 1:
        logger.warning(
            "Multiple .shp files found; using the first one: %s",
            shp_files[0],
        )
    return shp_files[0]


def read_shapefile_zip(path: PathLike, extract_dir: PathLike | None = None) -> gpd.GeoDataFrame:
    """Read a Shapefile from a zip archive and return a GeoDataFrame.

    Performs:
    - Zip-bomb protection (uncompressed size limit).
    - Zip-slip protection (path traversal check).
    - Required sidecar file checks (.shx, .dbf).
    - Missing .prj / undefined CRS rejection.
    - Empty feature set rejection.

    Parameters
    ----------
    path:
        Filesystem path to the ``.zip`` archive.
    extract_dir:
        Directory to extract into. If ``None`` a temporary directory is used
        (callers are responsible for cleanup).

    Returns
    -------
    GeoDataFrame
        All features from the Shapefile.

    Raises
    ------
    InvalidFileError
        On any structural problem with the archive or Shapefile.
    """
    import tempfile

    path = Path(path)
    logger.info("Reading Shapefile zip: %s", path)

    # Zip bomb protection
    _check_zip_bomb(path)

    # Use caller-supplied dir or a tmp dir
    _owned_tmp: tempfile.TemporaryDirectory | None = None
    if extract_dir is None:
        _owned_tmp = tempfile.TemporaryDirectory(prefix="geo_shp_")
        extract_dir = Path(_owned_tmp.name)
    else:
        extract_dir = Path(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)

    try:
        _safe_extract(path, extract_dir)

        shp_path = _find_shp_file(extract_dir)
        shp_stem = shp_path.stem
        shp_dir = shp_path.parent

        # Check required sidecar files
        missing = [
            ext
            for ext in (".shx", ".dbf")
            if not (shp_dir / f"{shp_stem}{ext}").exists()
        ]
        if missing:
            raise InvalidFileError(
                f"Shapefile is missing required sidecar file(s): {missing}. "
                "A valid Shapefile requires at minimum: .shp, .shx, .dbf."
            )

        # Check .prj presence
        prj_path = shp_dir / f"{shp_stem}.prj"
        if not prj_path.exists():
            raise InvalidFileError(
                "Missing .prj file – the Shapefile has no CRS definition. "
                "Please include a .prj file in the zip archive."
            )

        # Read the Shapefile
        try:
            gdf = gpd.read_file(str(shp_path), engine="pyogrio")
        except Exception as exc:
            raise InvalidFileError(f"Failed to read Shapefile: {exc}") from exc

        # Verify CRS
        if gdf.crs is None:
            raise InvalidFileError(
                "Missing .prj / CRS undefined: geopandas could not determine the CRS. "
                "Ensure the .prj file is well-formed."
            )

        # Drop rows with null or empty geometry
        if "geometry" in gdf.columns:
            gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

        if gdf.empty:
            raise InvalidFileError(
                "The Shapefile contains no features (or all features have null/empty geometry)."
            )

        logger.info(
            "Shapefile read complete: %d features, CRS=%s",
            len(gdf),
            gdf.crs,
        )
        return gdf

    finally:
        if _owned_tmp is not None:
            try:
                _owned_tmp.cleanup()
            except Exception:
                logger.warning("Failed to clean up temp dir: %s", _owned_tmp.name)
