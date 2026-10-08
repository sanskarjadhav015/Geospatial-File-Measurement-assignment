# Geospatial Measurement API

A FastAPI service to upload geospatial files (Shapefile `.zip` and KML) and calculate area and length measurements.

## Approach & CRS Handling

Geospatial data formats like Shapefiles and KML usually come in EPSG:4326 (WGS84 latitude and longitude in degrees). 

Because 1 degree of longitude varies in physical length depending on latitude, computing Euclidean area or distance directly on lat/long coordinates gives distorted and inaccurate numbers.

To calculate accurate real-world measurements:
1. The app reads the features and checks their centroid coordinates.
2. It determines the appropriate local UTM (Universal Transverse Mercator) zone (for example, EPSG:32618 for New York).
3. It reprojects the geometry coordinates into meters.
4. It calculates the area (in sq meters, hectares, sq km, acres) for Polygons, or length (in meters and km) for LineStrings.
5. For Polygons, it also calculates geodesic area using `pyproj.Geod` as an extra cross-check.
6. For Points, measurements are skipped since points don't have area or length.

## Project Structure

- `app/`
  - `api/routes.py` - API endpoints
  - `api/schemas.py` - Pydantic request/response schemas
  - `core/crs_transformer.py` - UTM projection and reprojection logic
  - `models/db_models.py` - Database models (SQLite / SQLAlchemy)
  - `services/file_service.py` - File upload and handling
  - `services/parser_service.py` - Shapefile and KML parser
  - `services/measurement_service.py` - Area and length calculation logic
  - `main.py` - FastAPI app entrypoint
- `sample_data/` - Test shapefiles and KML files
- `tests/` - Pytest test cases
- `requirements.txt` - Project dependencies

## How to Run

1. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the API server:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Open API Documentation:**
   Open `http://127.0.0.1:8000/docs` in your browser to test endpoints via Swagger UI.

## API Endpoints

- `POST /api/files/` - Upload a `.zip` (containing shapefile components) or a `.kml` file.
- `GET /api/files/` - List all uploaded files.
- `GET /api/files/{id}/` - Get file details and status.
- `GET /api/files/{id}/measurements/` - Get calculated measurements and summary.
- `GET /api/files/{id}/geojson/` - Export the file's features as GeoJSON.
- `DELETE /api/files/{id}/` - Delete an uploaded file and its features.
- `GET /health` - Health check endpoint.

## Running Tests

Run the test suite using pytest:
```bash
pytest
```

## Sample Files

The `sample_data/` directory contains sample files for testing:
- `sample_polygons.zip` - Shapefile with park polygons in NYC.
- `sample_lines.zip` - Shapefile with street lines in NYC.
- `sample_points.zip` - Shapefile with transit points.
- `sample_survey.kml` - KML file with mixed geometry types.
- `sample_donut.kml` - KML polygon with an inner hole.
