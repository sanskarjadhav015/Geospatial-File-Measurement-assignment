import pytest
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point, GeometryCollection
from app.services.measurement_service import MeasurementService


def test_polygon_area_in_projected_crs():
    # Polygon in Manhattan: approx 400m x 400m = ~160,000 m²
    poly = Polygon([
        (-73.9625, 40.7850),
        (-73.9580, 40.7865),
        (-73.9575, 40.7820),
        (-73.9620, 40.7815),
        (-73.9625, 40.7850)
    ])
    measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
        poly, "EPSG:4326"
    )

    assert status == "MEASURED"
    assert proj_crs == "EPSG:32618"
    assert "area_sq_meters" in measurements
    assert "area_hectares" in measurements
    assert "area_sq_km" in measurements
    assert "perimeter_meters" in measurements
    # Area should be realistic (in the order of 150,000 - 200,000 m²)
    assert 100_000 < measurements["area_sq_meters"] < 250_000
    assert measurements["area_hectares"] > 10.0


def test_linestring_length_in_projected_crs():
    line = LineString([(-73.9855, 40.7580), (-73.9830, 40.7600), (-73.9800, 40.7630)])
    measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
        line, "EPSG:4326"
    )

    assert status == "MEASURED"
    assert proj_crs == "EPSG:32618"
    assert "length_meters" in measurements
    assert "length_km" in measurements
    # Realistic length ~700m
    assert 500 < measurements["length_meters"] < 1000


def test_point_geometry_is_skipped():
    pt = Point(-73.985131, 40.758896)
    measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
        pt, "EPSG:4326"
    )

    assert status == "SKIPPED"
    assert measurements is None
    assert "No measurement required for Point geometry" in notes


def test_unsupported_geometry_handled_gracefully():
    # Unsupported geometry: mixed collection
    geom_col = GeometryCollection([Point(0, 0), LineString([(0, 0), (1, 1)])])
    measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
        geom_col, "EPSG:4326"
    )

    assert status == "UNSUPPORTED"
    assert measurements is None
    assert "not supported for measurement" in notes


def test_empty_geometry_handled():
    empty_poly = Polygon()
    measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
        empty_poly, "EPSG:4326"
    )

    assert status == "ERROR"
    assert measurements is None


def test_calculate_file_summary():
    features = [
        {
            "status": "MEASURED",
            "geometry_type": "Polygon",
            "measurements": {"area_sq_meters": 10000.0}
        },
        {
            "status": "MEASURED",
            "geometry_type": "LineString",
            "measurements": {"length_meters": 500.0}
        },
        {
            "status": "SKIPPED",
            "geometry_type": "Point",
            "measurements": None
        },
        {
            "status": "UNSUPPORTED",
            "geometry_type": "GeometryCollection",
            "measurements": None
        }
    ]
    summary = MeasurementService.calculate_file_summary(features)
    assert summary["total_features"] == 4
    assert summary["polygons_count"] == 1
    assert summary["total_area_sq_meters"] == 10000.0
    assert summary["total_area_hectares"] == 1.0
    assert summary["linestrings_count"] == 1
    assert summary["total_length_meters"] == 500.0
    assert summary["points_count"] == 1
    assert summary["unsupported_count"] == 1


def test_multipolygon_and_multilinestring_measurements():
    poly1 = Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])
    poly2 = Polygon([(2, 2), (3, 2), (3, 3), (2, 3), (2, 2)])
    mp = MultiPolygon([poly1, poly2])
    meas, crs, desc, status, _ = MeasurementService.process_feature_measurement(mp, "EPSG:4326")
    assert status == "MEASURED"
    assert meas["area_sq_meters"] > 0

    l1 = LineString([(0, 0), (1, 1)])
    l2 = LineString([(2, 2), (3, 3)])
    ml = MultiLineString([l1, l2])
    meas_l, crs_l, desc_l, status_l, _ = MeasurementService.process_feature_measurement(ml, "EPSG:4326")
    assert status_l == "MEASURED"
    assert meas_l["length_meters"] > 0

