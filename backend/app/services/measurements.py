"""Geospatial measurement service.

Computes area (m²) or length (m) for a single Shapely geometry by:
1. Re-projecting from the source CRS to EPSG:4326.
2. Picking the optimal UTM zone based on the geometry's representative point.
3. Re-projecting from EPSG:4326 to that UTM zone.
4. Computing area or length in metric units.

Never raises — all failures are captured in the returned dict.
"""

from __future__ import annotations

import logging
from typing import Any

from pyproj import Transformer
from shapely.geometry.base import BaseGeometry

from app.services.crs import utm_epsg

logger = logging.getLogger(__name__)

# Geometry types that need area measurement
_AREA_TYPES = frozenset({"Polygon", "MultiPolygon"})
# Geometry types that need length measurement
_LENGTH_TYPES = frozenset({"LineString", "MultiLineString"})
# Geometry types for which measurement is not required
_NOT_REQUIRED_TYPES = frozenset({"Point", "MultiPoint"})


def _make_transformer(src_epsg: int | str, dst_epsg: int | str) -> Transformer:
    """Create a pyproj Transformer with always_xy=True to avoid axis-order bugs.

    Parameters
    ----------
    src_epsg:
        Source CRS as an EPSG code integer or string (e.g. ``4326`` or ``"EPSG:4326"``).
    dst_epsg:
        Destination CRS.

    Returns
    -------
    Transformer
    """
    return Transformer.from_crs(
        src_epsg,
        dst_epsg,
        always_xy=True,
    )


def _transform_geom(geom: BaseGeometry, transformer: Transformer) -> BaseGeometry:
    """Apply a pyproj Transformer to a Shapely geometry.

    Parameters
    ----------
    geom:
        Input Shapely geometry (2-D assumed).
    transformer:
        A pyproj ``Transformer`` instance.

    Returns
    -------
    BaseGeometry
        The transformed geometry.
    """
    from shapely.ops import transform

    return transform(transformer.transform, geom)


def _crs_to_epsg_int(crs_str: str) -> int:
    """Extract the integer EPSG code from a CRS string.

    Parameters
    ----------
    crs_str:
        CRS string such as ``"EPSG:4326"`` or ``"EPSG:32643"``.

    Returns
    -------
    int
        Integer EPSG code.

    Raises
    ------
    ValueError
        If the string cannot be parsed.
    """
    upper = crs_str.upper()
    if upper.startswith("EPSG:"):
        return int(upper.split(":")[1])
    # Try pyproj for anything else
    from pyproj import CRS

    return int(CRS(crs_str).to_epsg())


def measure(geom: BaseGeometry | None, src_crs: str) -> dict[str, Any]:
    """Compute the metric measurement for a single geometry.

    The function NEVER raises. All error conditions are captured in the
    ``status`` and ``note`` fields of the returned dict.

    Parameters
    ----------
    geom:
        A Shapely geometry (may be ``None`` or empty).
    src_crs:
        The CRS of *geom* as a string, e.g. ``"EPSG:4326"`` or ``"EPSG:32643"``.

    Returns
    -------
    dict with keys:
        - ``type``: ``"area"`` | ``"length"`` | ``None``
        - ``value``: float | ``None``
        - ``unit``: ``"m2"`` | ``"m"`` | ``None``
        - ``projected_crs``: ``"EPSG:<n>"`` | ``None``
        - ``status``: ``"OK"`` | ``"NOT_REQUIRED"`` | ``"UNSUPPORTED"`` | ``"FAILED"``
        - ``note``: ``str`` | ``None``
    """
    _empty_result: dict[str, Any] = {
        "type": None,
        "value": None,
        "unit": None,
        "projected_crs": None,
        "status": "FAILED",
        "note": None,
    }

    # --- Guard: None or empty geometry ---
    if geom is None or geom.is_empty:
        return {
            **_empty_result,
            "status": "FAILED",
            "note": "Geometry is None or empty; cannot measure.",
        }

    geom_type = geom.geom_type

    # --- NOT_REQUIRED: Point / MultiPoint ---
    if geom_type in _NOT_REQUIRED_TYPES:
        return {
            **_empty_result,
            "status": "NOT_REQUIRED",
            "note": f"{geom_type} geometries do not require area or length measurement.",
        }

    # --- UNSUPPORTED: anything that isn't area/length ---
    if geom_type not in (_AREA_TYPES | _LENGTH_TYPES):
        return {
            **_empty_result,
            "status": "UNSUPPORTED",
            "note": (
                f"Geometry type '{geom_type}' is not supported for metric measurement. "
                "Supported types: Polygon, MultiPolygon, LineString, MultiLineString."
            ),
        }

    try:
        # Step 1 – normalise source CRS to EPSG int
        src_epsg = _crs_to_epsg_int(src_crs)

        # Step 2 – reproject to EPSG:4326 (if not already)
        if src_epsg == 4326:
            geom_4326 = geom
        else:
            t_to_4326 = _make_transformer(src_epsg, 4326)
            geom_4326 = _transform_geom(geom, t_to_4326)

        # Step 3 – pick UTM zone from representative point
        rep = geom_4326.representative_point()
        utm_code = utm_epsg(rep.x, rep.y)

        # Step 4 – reproject from 4326 → UTM
        t_to_utm = _make_transformer(4326, utm_code)
        geom_utm = _transform_geom(geom_4326, t_to_utm)

        projected_crs_str = f"EPSG:{utm_code}"

        # Step 5 – compute measurement
        if geom_type in _AREA_TYPES:
            # For MultiPolygon, shapely .area already sums all parts
            value = geom_utm.area
            return {
                "type": "area",
                "value": value,
                "unit": "m2",
                "projected_crs": projected_crs_str,
                "status": "OK",
                "note": None,
            }

        # LineString / MultiLineString
        value = geom_utm.length
        return {
            "type": "length",
            "value": value,
            "unit": "m",
            "projected_crs": projected_crs_str,
            "status": "OK",
            "note": None,
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("Measurement failed for geometry type %s: %s", geom_type, exc)
        return {
            **_empty_result,
            "status": "FAILED",
            "note": f"Measurement failed: {exc!s}",
        }
