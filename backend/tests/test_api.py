"""API integration tests using FastAPI TestClient.

Tests all endpoints: upload, list, get, measurements (pagination + filter),
delete. Also covers error cases: bad extension, oversized file, corrupt zip,
missing sidecar files, zip-slip, 404.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, Point, Polygon

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

EQUATOR_SQUARE = Polygon([(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01)])
A_LINE = LineString([(0.0, 0.0), (0.01, 0.0)])
A_POINT = Point(77.0, 28.0)


def _open_file(path: Path) -> tuple[str, bytes, str]:
    """Return (filename, content, content-type) for a file upload tuple."""
    suffix = path.suffix.lower()
    content_type = "application/zip" if suffix == ".zip" else "application/vnd.google-earth.kml+xml"
    return (path.name, path.read_bytes(), content_type)


def _upload(client: TestClient, path: Path):  # type: ignore[return]
    name, data, ct = _open_file(path)
    return client.post(
        "/api/files/",
        files={"file": (name, data, ct)},
    )


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------


class TestUploadKml:
    """Tests for uploading a valid KML file."""

    def test_valid_kml_returns_201(self, client: TestClient, sample_kml_file: Path) -> None:
        """Valid KML upload should return 201 with correct fields."""
        resp = _upload(client, sample_kml_file)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert "id" in body
        assert body["status"] == "COMPLETED"
        assert body["feature_count"] == 1
        assert body["crs"] is not None

    def test_kml_upload_feature_count(self, client: TestClient, sample_kml_file: Path) -> None:
        """KML with one polygon should report feature_count=1."""
        resp = _upload(client, sample_kml_file)
        assert resp.json()["feature_count"] == 1


class TestUploadShapefile:
    """Tests for uploading a valid zipped Shapefile."""

    def test_valid_shp_zip_returns_201(self, client: TestClient, sample_shp_zip: Path) -> None:
        """Valid Shapefile zip upload should return 201."""
        resp = _upload(client, sample_shp_zip)
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "COMPLETED"
        assert body["feature_count"] >= 1

    def test_projected_shp_zip(self, client: TestClient, projected_shp_zip: Path) -> None:
        """A Shapefile in projected CRS (EPSG:32643) should be processed correctly."""
        resp = _upload(client, projected_shp_zip)
        assert resp.status_code == 201, resp.text
        assert resp.json()["status"] == "COMPLETED"


class TestUploadErrors:
    """Tests for upload validation errors."""

    def test_bad_extension_returns_400(self, client: TestClient, tmp_path: Path) -> None:
        """Uploading a .txt file should return 400 Unsupported Extension."""
        bad = tmp_path / "file.txt"
        bad.write_text("not a geospatial file")
        resp = client.post(
            "/api/files/",
            files={"file": ("file.txt", bad.read_bytes(), "text/plain")},
        )
        assert resp.status_code == 400
        assert "detail" in resp.json()

    def test_oversized_file_returns_413(self, client: TestClient, tmp_path: Path) -> None:
        """A file exceeding MAX_UPLOAD_MB should return 413."""
        # Create a 51 MB dummy zip
        big = tmp_path / "big.zip"
        with zipfile.ZipFile(big, "w") as zf:
            zf.writestr("data.bin", b"\x00" * (51 * 1024 * 1024))
        resp = client.post(
            "/api/files/",
            files={"file": ("big.zip", big.read_bytes(), "application/zip")},
        )
        assert resp.status_code == 413

    def test_corrupt_zip_returns_422(self, client: TestClient, bad_zip: Path) -> None:
        """A corrupt zip should return 422 with detail."""
        resp = _upload(client, bad_zip)
        assert resp.status_code == 422
        assert "detail" in resp.json()

    def test_missing_shx_returns_422(self, client: TestClient, missing_shx_zip: Path) -> None:
        """Shapefile missing .shx should return 422."""
        resp = _upload(client, missing_shx_zip)
        assert resp.status_code == 422
        body = resp.json()
        assert "detail" in body

    def test_missing_prj_returns_422(self, client: TestClient, missing_prj_zip: Path) -> None:
        """Shapefile missing .prj (no CRS) should return 422."""
        resp = _upload(client, missing_prj_zip)
        assert resp.status_code == 422

    def test_zip_slip_returns_422(self, client: TestClient, zip_slip_zip: Path) -> None:
        """Zip archive with path traversal entry should return 422."""
        resp = _upload(client, zip_slip_zip)
        assert resp.status_code == 422
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# GET /api/files/{id}/ tests
# ---------------------------------------------------------------------------


class TestGetFile:
    """Tests for retrieving a file by ID."""

    def test_get_existing_file(self, client: TestClient, sample_kml_file: Path) -> None:
        """Should return 200 with full details for an existing file."""
        upload_resp = _upload(client, sample_kml_file)
        file_id = upload_resp.json()["id"]

        resp = client.get(f"/api/files/{file_id}/")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == file_id
        assert "created_at" in body
        assert "error_message" in body

    def test_get_nonexistent_file_returns_404(self, client: TestClient) -> None:
        """GET on a non-existent ID should return 404."""
        resp = client.get("/api/files/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 404
        assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# GET /api/files/ list tests
# ---------------------------------------------------------------------------


class TestListFiles:
    """Tests for the file listing endpoint."""

    def test_list_returns_200(self, client: TestClient) -> None:
        """GET /api/files/ should always return 200."""
        resp = client.get("/api/files/")
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "items" in body

    def test_list_is_newest_first(self, client: TestClient, sample_kml_file: Path) -> None:
        """The first item in the list should have the latest created_at."""
        _upload(client, sample_kml_file)
        resp = client.get("/api/files/?limit=100")
        items = resp.json()["items"]
        if len(items) >= 2:
            assert items[0]["created_at"] >= items[1]["created_at"]


# ---------------------------------------------------------------------------
# GET /api/files/{id}/measurements/ tests
# ---------------------------------------------------------------------------


class TestMeasurements:
    """Tests for the measurements endpoint."""

    @pytest.fixture()
    def uploaded_file_id(self, client: TestClient, sample_kml_file: Path) -> str:
        resp = _upload(client, sample_kml_file)
        return resp.json()["id"]

    def test_measurements_returns_200(
        self, client: TestClient, uploaded_file_id: str
    ) -> None:
        """Measurements endpoint should return 200 for a valid file."""
        resp = client.get(f"/api/files/{uploaded_file_id}/measurements/")
        assert resp.status_code == 200
        body = resp.json()
        assert "features" in body
        assert "summary" in body
        assert "total" in body

    def test_measurements_summary_fields(
        self, client: TestClient, uploaded_file_id: str
    ) -> None:
        """Summary should contain expected fields."""
        resp = client.get(f"/api/files/{uploaded_file_id}/measurements/")
        summary = resp.json()["summary"]
        assert "total_area_m2" in summary
        assert "total_length_m" in summary
        assert "unsupported" in summary
        assert "failed" in summary
        assert "by_geometry_type" in summary

    def test_measurements_pagination(
        self, client: TestClient, uploaded_file_id: str
    ) -> None:
        """Pagination parameters should be respected."""
        resp = client.get(
            f"/api/files/{uploaded_file_id}/measurements/?limit=1&offset=0"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["features"]) <= 1

    def test_measurements_geometry_type_filter(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """geometry_type filter should only return features of that type."""
        # Build a file with two geometry types
        from tests.conftest import _make_kml

        mixed_gdf = gpd.GeoDataFrame(
            {"name": ["poly", "line"]},
            geometry=[EQUATOR_SQUARE, A_LINE],
            crs="EPSG:4326",
        )
        kml_path = _make_kml(tmp_path, mixed_gdf, "mixed")
        resp = _upload(client, kml_path)
        fid = resp.json()["id"]

        # Filter to Polygon only
        resp = client.get(
            f"/api/files/{fid}/measurements/?geometry_type=Polygon"
        )
        assert resp.status_code == 200
        body = resp.json()
        for feat in body["features"]:
            assert feat["geometry_type"] == "Polygon"

    def test_measurements_404_for_missing_file(self, client: TestClient) -> None:
        """Measurements for a non-existent file should return 404."""
        resp = client.get(
            "/api/files/00000000-0000-0000-0000-000000000000/measurements/"
        )
        assert resp.status_code == 404

    def test_summary_covers_whole_file(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Summary totals must reflect the whole file, not just the current page."""
        from tests.conftest import _make_kml

        # 3 polygons
        polys = [
            Polygon([
                (i * 0.1, 0.0), (i * 0.1 + 0.01, 0.0),
                (i * 0.1 + 0.01, 0.01), (i * 0.1, 0.01),
            ])
            for i in range(3)
        ]
        gdf = gpd.GeoDataFrame({"name": list(range(3))}, geometry=polys, crs="EPSG:4326")
        kml = _make_kml(tmp_path, gdf, "three")
        fid = _upload(client, kml).json()["id"]

        # Page 1: only 1 feature
        resp_p1 = client.get(f"/api/files/{fid}/measurements/?limit=1&offset=0")
        resp_all = client.get(f"/api/files/{fid}/measurements/?limit=100&offset=0")

        # Summary should be identical regardless of page
        assert resp_p1.json()["summary"] == resp_all.json()["summary"]


# ---------------------------------------------------------------------------
# DELETE tests
# ---------------------------------------------------------------------------


class TestDeleteFile:
    """Tests for deleting a file."""

    def test_delete_returns_204(self, client: TestClient, sample_kml_file: Path) -> None:
        """DELETE should return 204 No Content."""
        resp = _upload(client, sample_kml_file)
        fid = resp.json()["id"]
        del_resp = client.delete(f"/api/files/{fid}/")
        assert del_resp.status_code == 204

    def test_delete_then_get_returns_404(
        self, client: TestClient, sample_kml_file: Path
    ) -> None:
        """After deletion, GET should return 404."""
        fid = _upload(client, sample_kml_file).json()["id"]
        client.delete(f"/api/files/{fid}/")
        assert client.get(f"/api/files/{fid}/").status_code == 404

    def test_delete_nonexistent_returns_404(self, client: TestClient) -> None:
        """DELETE on a non-existent ID should return 404."""
        resp = client.delete("/api/files/00000000-0000-0000-0000-000000000000/")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


class TestHealth:
    """Tests for /health endpoint."""

    def test_health_returns_ok(self, client: TestClient) -> None:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
