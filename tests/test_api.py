import io
import pytest


def test_root_and_health(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "service" in res.json()

    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_upload_shapefile_zip(client, sample_polygons_zip):
    with open(sample_polygons_zip, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.zip", f, "application/zip")}
        )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["filename"] == "sample_polygons.zip"
    assert data["file_type"] == "shapefile"
    assert data["feature_count"] == 2
    assert "4326" in data["crs"]
    assert data["status"] == "COMPLETED"


def test_get_file_info(client, sample_polygons_zip):
    # Upload first
    with open(sample_polygons_zip, "rb") as f:
        upload_res = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.zip", f, "application/zip")}
        )
    file_id = upload_res.json()["id"]

    # Get file info
    info_res = client.get(f"/api/files/{file_id}/")
    assert info_res.status_code == 200
    info = info_res.json()
    assert info["id"] == file_id
    assert info["feature_count"] == 2
    assert info["status"] == "COMPLETED"


def test_get_file_measurements_polygon(client, sample_polygons_zip):
    with open(sample_polygons_zip, "rb") as f:
        upload_res = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.zip", f, "application/zip")}
        )
    file_id = upload_res.json()["id"]

    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    data = meas_res.json()

    assert data["file_id"] == file_id
    assert data["total_features"] == 2

    # Check Summary
    summary = data["summary"]
    assert summary["polygons_count"] == 2
    assert summary["total_area_sq_meters"] > 0
    assert summary["total_area_hectares"] > 0

    # Check Features
    features = data["features"]
    assert len(features) == 2
    for feat in features:
        assert feat["geometry_type"] == "Polygon"
        assert feat["projected_crs"] == "EPSG:32618"  # Reprojected to UTM 18N!
        assert feat["status"] == "MEASURED"
        assert "area_sq_meters" in feat["measurements"]
        assert feat["measurements"]["area_sq_meters"] > 0
        assert "perimeter_meters" in feat["measurements"]


def test_upload_and_measure_kml(client, sample_survey_kml):
    with open(sample_survey_kml, "rb") as f:
        upload_res = client.post(
            "/api/files/",
            files={"file": ("sample_survey.kml", f, "application/vnd.google-earth.kml+xml")}
        )
    assert upload_res.status_code == 201
    file_id = upload_res.json()["id"]

    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    data = meas_res.json()

    summary = data["summary"]
    assert summary["total_features"] == 3
    assert summary["polygons_count"] == 1
    assert summary["linestrings_count"] == 1
    assert summary["points_count"] == 1

    # Check individual features
    by_type = {f["geometry_type"]: f for f in data["features"]}

    # Polygon has area
    poly_feat = by_type["Polygon"]
    assert poly_feat["projected_crs"] == "EPSG:32618"
    assert poly_feat["status"] == "MEASURED"
    assert poly_feat["measurements"]["area_sq_meters"] > 0

    # LineString has length
    line_feat = by_type["LineString"]
    assert line_feat["projected_crs"] == "EPSG:32618"
    assert line_feat["status"] == "MEASURED"
    assert line_feat["measurements"]["length_meters"] > 0

    # Point has no measurement
    point_feat = by_type["Point"]
    assert point_feat["status"] == "SKIPPED"
    assert point_feat["measurements"] == {}
    assert "No measurement required" in point_feat["notes"]


def test_get_nonexistent_file_404(client):
    res = client.get("/api/files/nonexistent_uuid/")
    assert res.status_code == 404
    assert res.json()["error_type"] == "ResourceNotFoundError"


def test_upload_invalid_extension_400(client):
    res = client.post(
        "/api/files/",
        files={"file": ("document.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


def test_upload_empty_file_400(client):
    res = client.post(
        "/api/files/",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")}
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_list_files_pagination(client, sample_polygons_zip, sample_survey_kml):
    with open(sample_polygons_zip, "rb") as f:
        client.post("/api/files/", files={"file": ("sample_polygons.zip", f, "application/zip")})
    with open(sample_survey_kml, "rb") as f:
        client.post("/api/files/", files={"file": ("sample_survey.kml", f, "application/xml")})

    res = client.get("/api/files/?skip=0&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_export_geojson(client, sample_survey_kml):
    with open(sample_survey_kml, "rb") as f:
        upload_res = client.post(
            "/api/files/",
            files={"file": ("sample_survey.kml", f, "application/xml")}
        )
    file_id = upload_res.json()["id"]

    res = client.get(f"/api/files/{file_id}/geojson/")
    assert res.status_code == 200
    data = res.json()
    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 3
    for feat in data["features"]:
        assert feat["type"] == "Feature"
        assert "geometry" in feat
        assert "properties" in feat


def test_delete_file(client, sample_polygons_zip):
    with open(sample_polygons_zip, "rb") as f:
        upload_res = client.post(
            "/api/files/",
            files={"file": ("sample_polygons.zip", f, "application/zip")}
        )
    file_id = upload_res.json()["id"]

    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 200

    # Ensure it no longer exists
    get_res = client.get(f"/api/files/{file_id}/")
    assert get_res.status_code == 404
