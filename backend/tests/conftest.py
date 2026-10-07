"""Shared pytest fixtures and test data generation.

Sample geospatial files are generated programmatically using geopandas
so that no binary test fixtures need to be committed to the repository.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

import geopandas as gpd
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import LineString, MultiPolygon, Point, Polygon

# ---------------------------------------------------------------------------
# App / DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def tmp_storage(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-scoped temporary storage directory."""
    return tmp_path_factory.mktemp("storage")


@pytest.fixture(scope="session", autouse=True)
def configure_test_settings(tmp_storage: Path) -> None:
    """Override settings before the app is imported in tests.

    Sets env vars so that pydantic-settings picks them up on first import.
    Must run before any app module is imported, so it is session-scoped
    and autouse=True.
    """
    db_path = tmp_storage / "test.db"
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{db_path}")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ["STORAGE_DIR"] = str(tmp_storage)
    os.environ["MAX_UPLOAD_MB"] = "50"
    os.environ["MAX_UNCOMPRESSED_MB"] = "200"


@pytest.fixture(scope="session")
def client(configure_test_settings: None) -> TestClient:
    """Session-scoped FastAPI TestClient with an in-memory DB."""
    from app.db.session import Base, engine
    from app.main import app

    Base.metadata.create_all(bind=engine)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

# A 0.01° × 0.01° square near the equator (lon 0, lat 0)
# Expected area ≈ 1.23 km² (verified within 1%)
EQUATOR_SQUARE = Polygon([(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01), (0.0, 0.0)])

# A 0.01° × 0.01° square at high latitude (lat 70°)
HIGH_LAT_SQUARE = Polygon(
    [(10.0, 70.0), (10.01, 70.0), (10.01, 70.01), (10.0, 70.01), (10.0, 70.0)]
)

# A simple LineString
SIMPLE_LINE = LineString([(0.0, 0.0), (0.01, 0.0)])  # ≈ 1.11 km along equator

# A MultiPolygon (two small squares)
MULTI_POLY = MultiPolygon(
    [
        Polygon([(0.0, 0.0), (0.01, 0.0), (0.01, 0.01), (0.0, 0.01)]),
        Polygon([(0.1, 0.0), (0.11, 0.0), (0.11, 0.01), (0.1, 0.01)]),
    ]
)

# A point (measurement NOT_REQUIRED)
A_POINT = Point(77.0, 28.0)


# ---------------------------------------------------------------------------
# File-generation helpers
# ---------------------------------------------------------------------------


def _make_shapefile_zip(
    tmp_path: Path,
    gdf: gpd.GeoDataFrame,
    name: str = "test",
    missing: list[str] | None = None,
) -> Path:
    """Write a GeoDataFrame as a zipped Shapefile and return the zip path.

    Parameters
    ----------
    tmp_path:
        Directory to write intermediate files.
    gdf:
        GeoDataFrame to serialise.
    name:
        Base name for the Shapefile.
    missing:
        List of sidecar extensions to omit from the zip (e.g. [".shx"]).
    """
    shp_dir = tmp_path / "shp_out"
    shp_dir.mkdir(exist_ok=True)
    shp_path = shp_dir / f"{name}.shp"
    gdf.to_file(str(shp_path), driver="ESRI Shapefile")

    zip_path = tmp_path / f"{name}.zip"
    missing = missing or []
    with zipfile.ZipFile(zip_path, "w") as zf:
        for f in shp_dir.iterdir():
            if f.suffix in missing:
                continue
            zf.write(f, arcname=f.name)
    return zip_path


def _make_kml(tmp_path: Path, gdf: gpd.GeoDataFrame, name: str = "test") -> Path:
    """Write a GeoDataFrame as a KML file and return the path."""
    kml_path = tmp_path / f"{name}.kml"
    gdf.to_file(str(kml_path), driver="KML")
    return kml_path


# ---------------------------------------------------------------------------
# Reusable file fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_polygon_gdf() -> gpd.GeoDataFrame:
    """GeoDataFrame with one polygon near the equator."""
    return gpd.GeoDataFrame(
        {"name": ["test_poly"]},
        geometry=[EQUATOR_SQUARE],
        crs="EPSG:4326",
    )


@pytest.fixture()
def sample_kml_file(tmp_path: Path, sample_polygon_gdf: gpd.GeoDataFrame) -> Path:
    """A valid KML file with one polygon feature."""
    return _make_kml(tmp_path, sample_polygon_gdf, "sample")


@pytest.fixture()
def sample_shp_zip(tmp_path: Path, sample_polygon_gdf: gpd.GeoDataFrame) -> Path:
    """A valid zipped Shapefile with one polygon feature."""
    return _make_shapefile_zip(tmp_path, sample_polygon_gdf, "sample")


@pytest.fixture()
def projected_shp_zip(tmp_path: Path) -> Path:
    """A zipped Shapefile in a projected CRS (EPSG:32643 – UTM zone 43N)."""
    from pyproj import Transformer
    from shapely.ops import transform

    t = Transformer.from_crs(4326, 32643, always_xy=True)
    geom_utm = transform(t.transform, EQUATOR_SQUARE)
    gdf = gpd.GeoDataFrame({"name": ["projected"]}, geometry=[geom_utm], crs="EPSG:32643")
    return _make_shapefile_zip(tmp_path, gdf, "projected")


@pytest.fixture()
def missing_shx_zip(tmp_path: Path, sample_polygon_gdf: gpd.GeoDataFrame) -> Path:
    """A zipped Shapefile missing the required .shx sidecar."""
    return _make_shapefile_zip(tmp_path, sample_polygon_gdf, "no_shx", missing=[".shx"])


@pytest.fixture()
def missing_prj_zip(tmp_path: Path, sample_polygon_gdf: gpd.GeoDataFrame) -> Path:
    """A zipped Shapefile missing the .prj (CRS) file."""
    return _make_shapefile_zip(tmp_path, sample_polygon_gdf, "no_prj", missing=[".prj"])


@pytest.fixture()
def bad_zip(tmp_path: Path) -> Path:
    """A file with a .zip extension but corrupt/invalid content."""
    p = tmp_path / "bad.zip"
    p.write_bytes(b"THIS IS NOT A VALID ZIP FILE")
    return p


@pytest.fixture()
def zip_slip_zip(tmp_path: Path) -> Path:
    """A zip archive containing a path traversal (zip-slip) entry."""
    p = tmp_path / "slip.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("../../evil.sh", "#!/bin/bash\nrm -rf /")
    return p
