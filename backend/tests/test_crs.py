"""Tests for services/crs.py – UTM EPSG zone selection."""

from __future__ import annotations

import pytest

from app.services.crs import utm_epsg


class TestUtmEpsg:
    """Tests for utm_epsg zone selection."""

    # --- Northern hemisphere ---

    def test_northern_hemisphere_india(self) -> None:
        """New Delhi (lon=77, lat=28.6) should be UTM zone 43N → EPSG:32643."""
        assert utm_epsg(77.0, 28.6) == 32643

    def test_northern_hemisphere_new_york(self) -> None:
        """New York (lon=-74, lat=40.7) should be UTM zone 18N → EPSG:32618."""
        assert utm_epsg(-74.0, 40.7) == 32618

    def test_northern_hemisphere_london(self) -> None:
        """London (lon=-0.12, lat=51.5) → UTM zone 30N → EPSG:32630."""
        assert utm_epsg(-0.12, 51.5) == 32630

    def test_equator_exactly(self) -> None:
        """Equator (lat=0) should be treated as northern hemisphere."""
        epsg = utm_epsg(0.0, 0.0)
        # Zone 31N at lon=0
        assert epsg == 32631

    # --- Southern hemisphere ---

    def test_southern_hemisphere_sydney(self) -> None:
        """Sydney (lon=151, lat=-33.9) → UTM zone 56S → EPSG:32756."""
        assert utm_epsg(151.0, -33.9) == 32756

    def test_southern_hemisphere_cape_town(self) -> None:
        """Cape Town (lon=18.4, lat=-33.9) → UTM zone 34S → EPSG:32734."""
        assert utm_epsg(18.4, -33.9) == 32734

    # --- Polar edge cases ---

    def test_polar_north_ups(self) -> None:
        """lat > 84 → UPS North → EPSG:32661."""
        assert utm_epsg(0.0, 85.0) == 32661

    def test_polar_north_boundary(self) -> None:
        """lat exactly 84 is the last UTM zone – should NOT be UPS."""
        epsg = utm_epsg(0.0, 84.0)
        assert epsg != 32661
        assert 32600 <= epsg <= 32660

    def test_polar_south_ups(self) -> None:
        """lat < -80 → UPS South → EPSG:32761."""
        assert utm_epsg(0.0, -85.0) == 32761

    def test_polar_south_boundary(self) -> None:
        """lat exactly -80 is the last UTM zone – should NOT be UPS."""
        epsg = utm_epsg(0.0, -80.0)
        assert epsg != 32761
        assert 32700 <= epsg <= 32760

    # --- Antimeridian edge ---

    def test_antimeridian_positive(self) -> None:
        """lon=180 should map to zone 60, not zone 61."""
        epsg = utm_epsg(180.0, 0.0)
        assert epsg == 32660  # zone 60N

    def test_antimeridian_negative(self) -> None:
        """lon=-180 should map to zone 1."""
        assert utm_epsg(-180.0, 0.0) == 32601

    def test_zone_range_northern(self) -> None:
        """All northern hemisphere EPSG codes should be between 32601 and 32660."""
        for lon in range(-180, 180, 10):
            epsg = utm_epsg(float(lon), 45.0)
            assert 32601 <= epsg <= 32660, f"Out-of-range for lon={lon}: {epsg}"

    def test_zone_range_southern(self) -> None:
        """All southern hemisphere EPSG codes should be between 32701 and 32760."""
        for lon in range(-180, 180, 10):
            epsg = utm_epsg(float(lon), -45.0)
            assert 32701 <= epsg <= 32760, f"Out-of-range for lon={lon}: {epsg}"
