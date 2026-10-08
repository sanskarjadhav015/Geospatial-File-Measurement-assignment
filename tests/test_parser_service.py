import io
import zipfile
import pytest
from app.services.parser_service import GeospatialParserService
from app.core.exceptions import FileProcessingError


def test_parse_shapefile_zip(sample_polygons_zip):
    with open(sample_polygons_zip, "rb") as f:
        data = f.read()

    features, detected_crs, ftype = GeospatialParserService.parse_file("sample_polygons.zip", data)
    assert ftype == "shapefile"
    assert "4326" in detected_crs
    assert len(features) == 2
    assert features[0].geometry_type == "Polygon"
    assert "name" in features[0].properties
    assert features[0].properties["name"] == "Central Park Reservoir"


def test_parse_linestring_shapefile_zip(sample_lines_zip):
    with open(sample_lines_zip, "rb") as f:
        data = f.read()

    features, detected_crs, ftype = GeospatialParserService.parse_file("sample_lines.zip", data)
    assert ftype == "shapefile"
    assert len(features) == 2
    assert features[0].geometry_type == "LineString"
    assert features[0].properties["road_name"] == "Broadway North"


def test_parse_kml_file(sample_survey_kml):
    with open(sample_survey_kml, "rb") as f:
        data = f.read()

    features, detected_crs, ftype = GeospatialParserService.parse_file("sample_survey.kml", data)
    assert ftype == "kml"
    assert detected_crs == "EPSG:4326"
    assert len(features) == 3

    types = [f.geometry_type for f in features]
    assert "Polygon" in types
    assert "LineString" in types
    assert "Point" in types


def test_parse_kml_with_hole(sample_donut_kml):
    with open(sample_donut_kml, "rb") as f:
        data = f.read()

    features, detected_crs, ftype = GeospatialParserService.parse_file("sample_donut.kml", data)
    assert len(features) == 1
    poly = features[0].shapely_geom
    assert poly.geom_type == "Polygon"
    assert len(poly.interiors) == 1  # Verify interior hole was parsed


def test_zip_slip_security_prevention():
    # Construct malicious zip with ../
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("../etc/passwd", "malicious payload")
        zf.writestr("test.shp", "dummy")

    with pytest.raises(FileProcessingError, match="prohibited path traversal"):
        GeospatialParserService.parse_file("bad.zip", buf.getvalue())


def test_incomplete_shapefile_zip_error():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.shp", "dummy")  # Missing .shx and .dbf

    with pytest.raises(FileProcessingError, match="Missing required companion files"):
        GeospatialParserService.parse_file("test.zip", buf.getvalue())


def test_unsupported_file_extension():
    with pytest.raises(FileProcessingError, match="Unsupported file format"):
        GeospatialParserService.parse_file("data.csv", b"a,b,c\n1,2,3")
