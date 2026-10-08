import io
import os
import zipfile
from pathlib import Path
import shapefile

SAMPLE_DIR = Path(__file__).resolve().parent
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

WGS84_PRJ = (
    'GEOGCS["GCS_WGS_1984",'
    'DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],'
    'PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]]'
)

UTM18N_PRJ = (
    'PROJCS["WGS_1984_UTM_Zone_18N",'
    'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]],'
    'PROJECTION["Transverse_Mercator"],PARAMETER["False_Easting",500000.0],PARAMETER["False_Northing",0.0],PARAMETER["Central_Meridian",-75.0],'
    'PARAMETER["Scale_Factor",0.9996],PARAMETER["Latitude_Of_Origin",0.0],UNIT["Meter",1.0]]'
)


def create_polygon_shapefile_zip(output_path: Path):
    """Creates a Shapefile ZIP with 2 Polygons in EPSG:4326."""
    shp_io = io.BytesIO()
    shx_io = io.BytesIO()
    dbf_io = io.BytesIO()

    with shapefile.Writer(shp=shp_io, shx=shx_io, dbf=dbf_io) as w:
        w.field("name", "C", size=50)
        w.field("category", "C", size=30)
        w.field("zone_id", "N")

        # Feature 1: Central Park Reservoir
        w.poly([[
            [-73.9625, 40.7850],
            [-73.9580, 40.7865],
            [-73.9575, 40.7820],
            [-73.9620, 40.7815],
            [-73.9625, 40.7850]
        ]])
        w.record("Central Park Reservoir", "Water Body", 101)

        # Feature 2: Sheep Meadow
        w.poly([[
            [-73.9750, 40.7710],
            [-73.9720, 40.7725],
            [-73.9705, 40.7695],
            [-73.9740, 40.7680],
            [-73.9750, 40.7710]
        ]])
        w.record("Sheep Meadow", "Recreation", 102)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("parks.shp", shp_io.getvalue())
        zf.writestr("parks.shx", shx_io.getvalue())
        zf.writestr("parks.dbf", dbf_io.getvalue())
        zf.writestr("parks.prj", WGS84_PRJ)
    print(f"Created: {output_path}")


def create_linestring_shapefile_zip(output_path: Path):
    """Creates a Shapefile ZIP with 2 LineStrings in EPSG:4326."""
    shp_io = io.BytesIO()
    shx_io = io.BytesIO()
    dbf_io = io.BytesIO()

    with shapefile.Writer(shp=shp_io, shx=shx_io, dbf=dbf_io) as w:
        w.field("road_name", "C", size=50)
        w.field("speed_mph", "N")

        # Feature 1: Broadway Route
        w.line([[
            [-73.9855, 40.7580],
            [-73.9830, 40.7600],
            [-73.9800, 40.7630],
            [-73.9760, 40.7670]
        ]])
        w.record("Broadway North", 25)

        # Feature 2: 5th Avenue Segment
        w.line([[
            [-73.9730, 40.7640],
            [-73.9680, 40.7710],
            [-73.9630, 40.7780]
        ]])
        w.record("5th Avenue Corridor", 30)

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("routes.shp", shp_io.getvalue())
        zf.writestr("routes.shx", shx_io.getvalue())
        zf.writestr("routes.dbf", dbf_io.getvalue())
        zf.writestr("routes.prj", WGS84_PRJ)
    print(f"Created: {output_path}")


def create_point_shapefile_zip(output_path: Path):
    """Creates a Shapefile ZIP with Points."""
    shp_io = io.BytesIO()
    shx_io = io.BytesIO()
    dbf_io = io.BytesIO()

    with shapefile.Writer(shp=shp_io, shx=shx_io, dbf=dbf_io) as w:
        w.field("station", "C", size=50)
        w.point(-73.985131, 40.758896)
        w.record("Times Square Station")
        w.point(-73.9772, 40.7527)
        w.record("Grand Central Terminal")

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("stations.shp", shp_io.getvalue())
        zf.writestr("stations.shx", shx_io.getvalue())
        zf.writestr("stations.dbf", dbf_io.getvalue())
        zf.writestr("stations.prj", WGS84_PRJ)
    print(f"Created: {output_path}")


def create_sample_kml(output_path: Path):
    """Creates a rich KML with Polygons, LineStrings, and Points."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Manhattan Survey</name>
    <description>Sample geospatial survey dataset containing polygons, lines, and points.</description>
    
    <!-- Feature 1: Polygon (Bryant Park) -->
    <Placemark>
      <name>Bryant Park</name>
      <description>Public park located in Midtown Manhattan</description>
      <ExtendedData>
        <Data name="type"><value>Park</value></Data>
        <Data name="established"><value>1847</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.9835,40.7538,0
              -73.9818,40.7548,0
              -73.9828,40.7558,0
              -73.9845,40.7547,0
              -73.9835,40.7538,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Feature 2: LineString (High Line) -->
    <Placemark>
      <name>High Line Trail</name>
      <description>Elevated linear park trail</description>
      <ExtendedData>
        <Data name="surface"><value>Paved</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          -74.0078,40.7395,0
          -74.0065,40.7420,0
          -74.0048,40.7460,0
          -74.0020,40.7510,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Feature 3: Point (Empire State Building) -->
    <Placemark>
      <name>Empire State Building</name>
      <description>102-story Art Deco skyscraper</description>
      <Point>
        <coordinates>-73.985656,40.748441,381</coordinates>
      </Point>
    </Placemark>
  </Document>
</kml>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Created: {output_path}")


def create_polygon_with_hole_kml(output_path: Path):
    """Creates a KML polygon with an inner hole."""
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Donut Polygon Survey</name>
    <Placemark>
      <name>Courtyard Complex</name>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.9800,40.7500,0
              -73.9700,40.7500,0
              -73.9700,40.7600,0
              -73.9800,40.7600,0
              -73.9800,40.7500,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
        <innerBoundaryIs>
          <LinearRing>
            <coordinates>
              -73.9770,40.7530,0
              -73.9730,40.7530,0
              -73.9730,40.7570,0
              -73.9770,40.7570,0
              -73.9770,40.7530,0
            </coordinates>
          </LinearRing>
        </innerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(kml_content)
    print(f"Created: {output_path}")


def main():
    create_polygon_shapefile_zip(SAMPLE_DIR / "sample_polygons.zip")
    create_linestring_shapefile_zip(SAMPLE_DIR / "sample_lines.zip")
    create_point_shapefile_zip(SAMPLE_DIR / "sample_points.zip")
    create_sample_kml(SAMPLE_DIR / "sample_survey.kml")
    create_polygon_with_hole_kml(SAMPLE_DIR / "sample_donut.kml")
    print("All sample data generated successfully!")


if __name__ == "__main__":
    main()
