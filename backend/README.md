# Geospatial File Measurement API

A production-quality FastAPI service that accepts geospatial files (`.zip` Shapefile or `.kml`), extracts every feature, calculates accurate metric measurements using projected CRS (UTM), stores results in SQLite/PostgreSQL, and exposes them via REST APIs.

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [API Reference](#api-reference)
3. [Architecture](#architecture)
4. [Design Decisions](#design-decisions)
5. [Known Limitations](#known-limitations)

---

## Quick Start

### Prerequisites
- Python 3.11+
- `pip`

### Setup

```bash
cd backend/
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### Run the server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Interactive API docs: http://localhost:8000/docs

### Run tests

```bash
pytest tests/ -v
```

### Run linter

```bash
ruff check app/ tests/
```

### Docker

```bash
docker build -t geo-api .
docker run -p 8000:8000 -e DATABASE_URL="sqlite:///./geospatial.db" geo-api
```

---

## API Reference

### POST /api/files/ — Upload a geospatial file

```bash
curl -X POST http://localhost:8000/api/files/ -F "file=@/path/to/file.zip"
```

**Response 201:**
```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "filename": "roads.zip",
  "feature_count": 142,
  "crs": "EPSG:4326",
  "status": "COMPLETED"
}
```

Errors: 400 (bad extension), 413 (too large), 422 (corrupt/missing sidecar/no CRS/zip-slip)

### GET /api/files/ — List uploaded files

```bash
curl "http://localhost:8000/api/files/?limit=10&offset=0"
```

**Response 200:**
```json
{
  "total": 5, "limit": 10, "offset": 0,
  "items": [{"id": "...", "filename": "roads.zip", "file_type": "shapefile",
              "feature_count": 142, "crs": "EPSG:4326", "status": "COMPLETED",
              "error_message": null, "created_at": "2024-01-15T10:30:00Z"}]
}
```

### GET /api/files/{id}/ — Get file details

```bash
curl http://localhost:8000/api/files/3fa85f64.../
```

Response 200 with full detail including `error_message` and `created_at`. 404 if missing.

### GET /api/files/{id}/measurements/ — Get measurements

Supports: `?limit=100&offset=0&geometry_type=Polygon`

```bash
curl "http://localhost:8000/api/files/{id}/measurements/?geometry_type=Polygon"
```

**Response 200:**
```json
{
  "file_id": "...", "total": 3,
  "summary": {
    "total_area_m2": 4567890.12, "total_length_m": 0.0,
    "unsupported": 0, "failed": 0,
    "by_geometry_type": {"Polygon": 3}
  },
  "features": [{
    "index": 0, "geometry_type": "Polygon", "crs": "EPSG:4326",
    "properties": {"name": "Block A"},
    "geometry": {"type": "Polygon", "coordinates": [...]},
    "measurement": {
      "type": "area", "value": 1234567.89, "unit": "m2",
      "projected_crs": "EPSG:32643", "status": "OK", "note": null
    }
  }]
}
```

Summary covers the entire file (not just current page).

### DELETE /api/files/{id}/ — Delete a file

```bash
curl -X DELETE http://localhost:8000/api/files/{id}/
```

Response: 204 No Content. Removes DB rows and stored files.

### GET /health — Health check

```bash
curl http://localhost:8000/health
# {"status": "ok", "service": "Geospatial File Measurement API", "version": "1.0.0"}
```

---

## Architecture

### Layer Diagram

```
HTTP Layer  (app/api/routes/files.py)
  Multipart parsing, query params, status codes
          |
Service Layer
  processor.py   readers.py    storage.py
  measurements.py    crs.py
          |
DB Layer  (app/db/)
  SQLAlchemy ORM: UploadedFile, Feature
  SQLite (default) or PostgreSQL
```

### File Processing Flow

```
POST /api/files/
  1. Validate extension (.zip/.kml) -> 400
  2. processor.process_upload()
     a. Create UploadedFile(status=PROCESSING) in DB
     b. save_upload() -> STORAGE_DIR
     c. read_kml() or read_shapefile_zip()
        - zip bomb check, zip-slip check
        - sidecar checks (.shx .dbf .prj)
        - return GeoDataFrame
     d. For each feature (per-feature try/except):
        - force_2d(), repair_geometry()
        - measure(geom, src_crs)
        - build Feature ORM object
     e. bulk_save_objects(features)
     f. UploadedFile(status=COMPLETED)
  3. Return 201 FileOut
```

### Measurement Flow

```
measure(geom, src_crs)
  1. None/empty? -> FAILED
  2. Point/MultiPoint? -> NOT_REQUIRED
  3. GeometryCollection? -> UNSUPPORTED
  4. Polygon/MultiPolygon/LineString/MultiLineString:
     a. Parse src_crs -> EPSG int
     b. Transform to EPSG:4326 (if not already)
     c. Pick UTM zone from representative_point()
     d. Transform 4326 -> UTM (always_xy=True)
     e. Compute .area (m2) or .length (m) -> OK
```

### CRS Selection Flow

```
utm_epsg(lon, lat)
  lat > 84  -> EPSG:32661 (UPS North)
  lat < -80 -> EPSG:32761 (UPS South)
  else:
    zone = int((lon + 180) / 6) + 1  [clamped 1..60]
    base = 32600 (N) or 32700 (S)
    return base + zone
```

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Projection strategy | UTM per-feature | Higher accuracy than equal-area for global data; avoids geodesic calc complexity |
| Geometry library | geopandas + pyogrio | pyogrio 5-10x faster than fiona; GDF interface for attributes |
| Processing mode | Synchronous (v1) | Simplest correct impl; process_upload() trivially movable to BackgroundTask/Celery |
| Database | SQLite + JSON columns | Zero-infra dev; TEXT columns work in any DB; PostgreSQL: just change DATABASE_URL |
| Multi-geometry summing | Shapely .area/.length | Shapely 2.0 auto-sums Multi-* parts; no manual iteration |
| Reject missing .prj | Yes, 422 | Silent wrong-CRS default causes invisible measurement errors |
| UNSUPPORTED handling | Store with status=UNSUPPORTED | File still completes; user sees which features weren't measurable |
| make_valid repair | Repair + note | Invalid polygons common in real data; repair safer than failing the feature |
| Axis order | always_xy=True | PROJ 6+ changed geographic CRS axis order; always_xy ensures lon/lat regardless of definition |

---

## Known Limitations

- **UTM zone crossing**: Features spanning zones measured in representative-point zone. Error < 0.5% for features < 6 deg wide.
- **No auth**: All endpoints publicly accessible. Add API key middleware or OAuth2 for production.
- **Sync processing**: Large files block the request thread. Use BackgroundTasks or Celery+Redis for production.
- **SQLite concurrency**: WAL mode handles concurrent reads but serialises writes. Use PostgreSQL for multi-worker.
- **KML network links**: External links not fetched; only local geometry read.
- **KML CRS assumption**: Always EPSG:4326 per OGC spec. Non-standard KML may produce wrong results.
