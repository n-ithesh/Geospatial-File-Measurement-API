"""Tests for services/measurements.py."""

from __future__ import annotations

import math

import pytest
from app.services.measurements import measure
from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
)

# A 0.01° × 0.01° square near the equator
EQUATOR_SQUARE = Polygon([(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)])

# Same degree square at high latitude (lat ≈ 70°) – area should be smaller
HIGH_LAT_SQUARE = Polygon(
    [(10.0, 70.0), (10.01, 70.0), (10.01, 70.01), (10.0, 70.01), (10.0, 70.0)]
)

# Line along the equator ≈ 1.11 km
EQUATOR_LINE = LineString([(0.0, 0.0), (0.01, 0.0)])


class TestMeasureArea:
    """Area measurement tests for Polygon geometries."""

    def test_equator_square_approx_area(self) -> None:
        """0.01°×0.01° square near equator ≈ 1.23 km² (within 1%)."""
        result = measure(EQUATOR_SQUARE, "EPSG:4326")
        assert result["status"] == "OK"
        assert result["type"] == "area"
        assert result["unit"] == "m2"
        assert result["value"] is not None
        expected_m2 = 1_230_000  # ~1.23 km²
        assert math.isclose(result["value"], expected_m2, rel_tol=0.01), (
            f"Expected ~{expected_m2} m², got {result['value']:.0f} m²"
        )

    def test_high_latitude_smaller_than_equator(self) -> None:
        """Same degree-square at high lat should have a smaller area than at equator."""
        result_eq = measure(EQUATOR_SQUARE, "EPSG:4326")
        result_hi = measure(HIGH_LAT_SQUARE, "EPSG:4326")
        assert result_eq["status"] == "OK"
        assert result_hi["status"] == "OK"
        assert result_hi["value"] < result_eq["value"], (
            "High-latitude polygon should have a smaller area than equatorial polygon"
        )

    def test_projected_crs_input_matches_4326(self) -> None:
        """A polygon in EPSG:32643 (UTM) should give the same area as the EPSG:4326 equivalent."""
        from pyproj import Transformer
        from shapely.ops import transform

        t = Transformer.from_crs(4326, 32643, always_xy=True)
        utm_poly = transform(t.transform, EQUATOR_SQUARE)

        result_4326 = measure(EQUATOR_SQUARE, "EPSG:4326")
        result_utm = measure(utm_poly, "EPSG:32643")

        assert result_4326["status"] == "OK"
        assert result_utm["status"] == "OK"
        assert math.isclose(
            result_4326["value"], result_utm["value"], rel_tol=0.02
        ), (
            f"4326 area={result_4326['value']:.2f}, UTM area={result_utm['value']:.2f}"
        )

    def test_polygon_projected_crs_label(self) -> None:
        """Projected CRS in result should be an EPSG string."""
        result = measure(EQUATOR_SQUARE, "EPSG:4326")
        assert result["projected_crs"] is not None
        assert result["projected_crs"].startswith("EPSG:")

    def test_multi_polygon_sums_parts(self) -> None:
        """MultiPolygon area should equal sum of individual polygon areas."""
        poly1 = EQUATOR_SQUARE
        poly2 = Polygon([(0.1, 0.0), (0.11, 0.0), (0.11, 0.01), (0.1, 0.01)])
        multi = MultiPolygon([poly1, poly2])

        r_multi = measure(multi, "EPSG:4326")
        r1 = measure(poly1, "EPSG:4326")
        r2 = measure(poly2, "EPSG:4326")

        assert r_multi["status"] == "OK"
        assert math.isclose(
            r_multi["value"], r1["value"] + r2["value"], rel_tol=0.01
        )


class TestMeasureLength:
    """Length measurement tests for LineString geometries."""

    def test_line_length_sanity(self) -> None:
        """0.01° line along the equator should be approximately 1,111 m."""
        result = measure(EQUATOR_LINE, "EPSG:4326")
        assert result["status"] == "OK"
        assert result["type"] == "length"
        assert result["unit"] == "m"
        # 0.01° ≈ 1111 m along the equator
        assert math.isclose(result["value"], 1111.0, rel_tol=0.02), (
            f"Expected ~1111 m, got {result['value']:.1f} m"
        )

    def test_multi_linestring_sums_parts(self) -> None:
        """MultiLineString length should equal sum of individual lengths."""
        line1 = LineString([(0.0, 0.0), (0.01, 0.0)])
        line2 = LineString([(0.1, 0.0), (0.11, 0.0)])
        multi = MultiLineString([line1, line2])

        r_multi = measure(multi, "EPSG:4326")
        r1 = measure(line1, "EPSG:4326")
        r2 = measure(line2, "EPSG:4326")

        assert r_multi["status"] == "OK"
        assert math.isclose(r_multi["value"], r1["value"] + r2["value"], rel_tol=0.01)


class TestMeasureSpecialCases:
    """Tests for NOT_REQUIRED, UNSUPPORTED, FAILED, and None cases."""

    def test_point_not_required(self) -> None:
        """Point geometry → status NOT_REQUIRED, no measurement value."""
        result = measure(Point(0.0, 0.0), "EPSG:4326")
        assert result["status"] == "NOT_REQUIRED"
        assert result["type"] is None
        assert result["value"] is None

    def test_geometry_collection_unsupported(self) -> None:
        """GeometryCollection → status UNSUPPORTED."""
        gc = GeometryCollection([Point(0, 0), EQUATOR_SQUARE])
        result = measure(gc, "EPSG:4326")
        assert result["status"] == "UNSUPPORTED"
        assert result["type"] is None

    def test_none_geometry_failed(self) -> None:
        """None geometry → status FAILED."""
        result = measure(None, "EPSG:4326")
        assert result["status"] == "FAILED"
        assert result["note"] is not None

    def test_empty_geometry_failed(self) -> None:
        """Empty polygon → status FAILED."""
        result = measure(Polygon(), "EPSG:4326")
        assert result["status"] == "FAILED"
        assert result["note"] is not None

    def test_never_raises(self) -> None:
        """measure() must never raise, regardless of input."""
        # Pass deliberately broken inputs
        for geom, crs in [
            (None, "EPSG:4326"),
            (Polygon(), "EPSG:4326"),
            (Point(999, 999), "INVALID_CRS"),
        ]:
            try:
                result = measure(geom, crs)
                assert isinstance(result, dict)
            except Exception as exc:
                pytest.fail(f"measure() raised unexpectedly: {exc}")
