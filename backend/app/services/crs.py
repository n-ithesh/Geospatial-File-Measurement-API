"""CRS selection utilities.

Provides ``utm_epsg`` which selects the most appropriate UTM (or UPS polar)
EPSG code for a given longitude/latitude coordinate.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def utm_epsg(lon: float, lat: float) -> int:
    """Return the EPSG code of the best-fit UTM or polar projection.

    The returned code is always a *projected* CRS suitable for metric
    area/length calculations.

    Parameters
    ----------
    lon:
        Longitude in decimal degrees (−180 to 180).
    lat:
        Latitude in decimal degrees (−90 to 90).

    Returns
    -------
    int
        EPSG code of the selected projected CRS.

    Examples
    --------
    >>> utm_epsg(77.0, 28.6)   # New Delhi – UTM zone 43N
    32643
    >>> utm_epsg(-74.0, 40.7)  # New York – UTM zone 18N
    32618
    >>> utm_epsg(0.0, 85.5)    # Arctic – UPS North
    32661
    >>> utm_epsg(0.0, -85.5)   # Antarctic – UPS South
    32761
    """
    # Polar special cases
    if lat > 84:
        logger.debug("Using UPS North (EPSG:32661) for lat=%.4f", lat)
        return 32661  # UPS North
    if lat < -80:
        logger.debug("Using UPS South (EPSG:32761) for lat=%.4f", lat)
        return 32761  # UPS South

    # Standard UTM zone calculation
    # Clamp longitude to [−180, 180) then compute zone number
    lon_norm = ((lon + 180.0) % 360.0) - 180.0  # normalise to [−180, 180)
    zone = int((lon_norm + 180.0) // 6) + 1
    zone = min(zone, 60)  # guard against floating-point edge at exactly 180°

    # Northern or southern hemisphere base
    base = 32600 if lat >= 0 else 32700
    epsg = base + zone

    logger.debug(
        "utm_epsg(lon=%.4f, lat=%.4f) -> zone=%d, EPSG:%d",
        lon,
        lat,
        zone,
        epsg,
    )
    return epsg
