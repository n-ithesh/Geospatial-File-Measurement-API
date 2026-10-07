"""Geometry utility helpers.

Provides safe wrappers around Shapely operations used across services.
"""

from __future__ import annotations

import logging
import math
from datetime import date, datetime
from typing import Any

import numpy as np
from shapely import make_valid
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

logger = logging.getLogger(__name__)


def force_2d(geom: BaseGeometry) -> BaseGeometry:
    """Strip Z (and M) coordinates from a geometry.

    Shapely ≥2.0 provides ``shapely.force_2d``; we replicate the behaviour
    here using the public API so it works even if the internal function moves.

    Parameters
    ----------
    geom:
        Any Shapely geometry, potentially with Z coordinates.

    Returns
    -------
    BaseGeometry
        The same geometry type but with only X and Y coordinates.
    """
    import shapely

    return shapely.force_2d(geom)


def repair_geometry(geom: BaseGeometry) -> tuple[BaseGeometry, str | None]:
    """Attempt to repair an invalid geometry using ``shapely.make_valid``.

    Parameters
    ----------
    geom:
        A potentially invalid Shapely geometry.

    Returns
    -------
    tuple[BaseGeometry, str | None]
        ``(repaired_geometry, note)`` where *note* is a human-readable string
        if a repair was performed, or ``None`` if the geometry was already valid.
    """
    if geom.is_valid:
        return geom, None

    note = f"Geometry was invalid (reason: {geom.explain_validity()}); repaired with make_valid."
    repaired = make_valid(geom)
    logger.debug("Repaired geometry: %s", note)
    return repaired, note


def to_geojson(geom: BaseGeometry | None) -> dict | None:
    """Convert a Shapely geometry to a GeoJSON-compatible dict.

    Parameters
    ----------
    geom:
        A Shapely geometry or ``None``.

    Returns
    -------
    dict | None
        GeoJSON geometry dict, or ``None`` if *geom* is ``None`` or empty.
    """
    if geom is None or geom.is_empty:
        return None
    try:
        return dict(mapping(geom))
    except Exception:
        logger.exception("Failed to convert geometry to GeoJSON")
        return None


def _sanitise_value(v: Any) -> Any:
    """Convert a single value to a JSON-safe Python primitive.

    Handles numpy scalars, NaN/Inf floats, NaT, datetimes, dates.
    """
    # numpy scalars
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        fv = float(v)
        return None if (math.isnan(fv) or math.isinf(fv)) else fv
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.ndarray):
        return [_sanitise_value(x) for x in v.tolist()]

    # pandas NaT
    try:
        import pandas as pd  # type: ignore

        if pd.isnull(v):
            return None
    except (ImportError, TypeError, ValueError):
        pass

    # Python floats
    if isinstance(v, float):
        return None if (math.isnan(v) or math.isinf(v)) else v

    # datetime-likes
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()

    # bytes -> base64 string
    if isinstance(v, bytes | bytearray):
        import base64

        return base64.b64encode(v).decode("ascii")

    return v


def sanitise_properties(props: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe copy of a feature properties dict.

    Converts numpy scalars, NaN/NaT values, datetimes, etc. to Python
    primitives that can be serialised with ``json.dumps``.

    Parameters
    ----------
    props:
        Raw properties dict from a GeoDataFrame row.

    Returns
    -------
    dict[str, Any]
        JSON-serialisable properties dict.
    """
    if not props:
        return {}
    return {k: _sanitise_value(v) for k, v in props.items()}
