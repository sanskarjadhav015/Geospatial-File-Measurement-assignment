import io
import zipfile
import pytest
import pyproj
from shapely.geometry import Polygon, MultiPolygon, LineString, MultiLineString, Point
from app.services.parser_service import GeospatialParserService
from app.services.measurement_service import MeasurementService
from app.core.crs_transformer import CRSTransformerService
from app.models.database import get_db


def test_kml_multigeometry_parsing():
    kml_str = """<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
      <Document>
        <Placemark>
          <name>Multi Poly</name>
          <MultiGeometry>
            <Polygon>
              <outerBoundaryIs><LinearRing><coordinates>0,0,0 1,0,0 1,1,0 0,1,0 0,0,0</coordinates></LinearRing></outerBoundaryIs>
            </Polygon>
            <Polygon>
              <outerBoundaryIs><LinearRing><coordinates>2,2,0 3,2,0 3,3,0 2,3,0 2,2,0</coordinates></LinearRing></outerBoundaryIs>
            </Polygon>
          </MultiGeometry>
        </Placemark>
        <Placemark>
          <name>Multi Line</name>
          <MultiGeometry>
            <LineString><coordinates>0,0,0 1,1,0</coordinates></LineString>
            <LineString><coordinates>2,2,0 3,3,0</coordinates></LineString>
          </MultiGeometry>
        </Placemark>
      </Document>
    </kml>"""
    features, crs, ftype = GeospatialParserService.parse_file("multi.kml", kml_str.encode("utf-8"))
    assert len(features) == 2
    assert features[0].geometry_type == "MultiPolygon"
    assert features[1].geometry_type == "MultiLineString"


def test_kmz_archive_parsing():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("doc.kml", """<?xml version="1.0" encoding="UTF-8"?>
        <kml xmlns="http://www.opengis.net/kml/2.2">
          <Placemark>
            <name>Test KMZ Point</name>
            <Point><coordinates>10,20,0</coordinates></Point>
          </Placemark>
        </kml>""")
    features, crs, ftype = GeospatialParserService.parse_file("test.kmz.zip", buf.getvalue())
    assert ftype == "kml"
    assert len(features) == 1
    assert features[0].geometry_type == "Point"


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


def test_get_db_generator():
    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        next(gen)
    except StopIteration:
        pass
