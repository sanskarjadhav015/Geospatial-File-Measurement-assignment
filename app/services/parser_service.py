import io
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Tuple, Optional
import pyproj
import shapefile
import shapely
from shapely.geometry import shape, Point, LineString, Polygon, MultiPolygon, MultiLineString, MultiPoint, GeometryCollection
from shapely.geometry.base import BaseGeometry
from shapely.validation import make_valid

from app.core.exceptions import FileProcessingError


class ParsedFeature:
    """Internal representation of a parsed geospatial feature."""
    def __init__(
        self,
        feature_index: int,
        geometry_type: str,
        shapely_geom: Optional[BaseGeometry],
        geometry_geojson: Dict[str, Any],
        properties: Dict[str, Any],
        source_crs: str,
        is_valid: bool = True,
        error_message: Optional[str] = None
    ):
        self.feature_index = feature_index
        self.geometry_type = geometry_type
        self.shapely_geom = shapely_geom
        self.geometry_geojson = geometry_geojson
        self.properties = properties
        self.source_crs = source_crs
        self.is_valid = is_valid
        self.error_message = error_message


class GeospatialParserService:
    """
    Parses geospatial files (Shapefile ZIPs and KML files) into normalized features.
    """

    @classmethod
    def parse_file(cls, filename: str, file_bytes: bytes) -> Tuple[List[ParsedFeature], str, str]:
        """
        Detects file type, parses content, and returns:
        (features, detected_crs, file_type)
        """
        fn_lower = filename.lower()
        if fn_lower.endswith(".zip"):
            # Could be Shapefile ZIP or KMZ
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                    names = [n.lower() for n in zf.namelist()]
                    if any(n.endswith(".shp") for n in names):
                        return cls.parse_shapefile_zip(file_bytes)
                    elif any(n.endswith(".kml") for n in names):
                        return cls.parse_kmz(file_bytes)
                    else:
                        raise FileProcessingError(
                            "ZIP archive does not contain a .shp Shapefile or .kml file."
                        )
            except zipfile.BadZipFile:
                raise FileProcessingError("Uploaded file is not a valid ZIP archive.")
        elif fn_lower.endswith(".kml"):
            return cls.parse_kml(file_bytes)
        else:
            raise FileProcessingError(
                f"Unsupported file format '{filename}'. Supported formats are: .zip (Shapefile) and .kml."
            )

    # =========================================================================
    # Shapefile Parser
    # =========================================================================

    @classmethod
    def parse_shapefile_zip(cls, zip_bytes: bytes) -> Tuple[List[ParsedFeature], str, str]:
        """
        Parses a Shapefile stored inside a ZIP archive in memory without disk pollution.
        Checks for path traversal security (Zip Slip).
        """
        try:
            zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        except Exception as e:
            raise FileProcessingError(f"Corrupted or invalid ZIP archive: {str(e)}")

        names = zf.namelist()
        # Security check: detect path traversal
        for n in names:
            if ".." in n or n.startswith("/") or n.startswith("\\"):
                raise FileProcessingError("Security alert: ZIP contains prohibited path traversal sequences.")

        shp_candidates = [n for n in names if n.lower().endswith(".shp")]
        if not shp_candidates:
            raise FileProcessingError("No .shp file found inside the ZIP archive.")

        shp_path = shp_candidates[0]
        base_name = shp_path[:-4]

        # Case-insensitive file finder inside ZIP
        lower_map = {n.lower(): n for n in names}
        shx_name = lower_map.get(f"{base_name.lower()}.shx")
        dbf_name = lower_map.get(f"{base_name.lower()}.dbf")
        prj_name = lower_map.get(f"{base_name.lower()}.prj")

        if not shx_name or not dbf_name:
            raise FileProcessingError(
                f"Incomplete Shapefile: Missing required companion files (.shx or .dbf) for '{shp_path}'."
            )

        # Detect CRS from .prj
        source_crs = "EPSG:4326"
        if prj_name:
            try:
                prj_text = zf.read(prj_name).decode("utf-8", errors="ignore").strip()
                if prj_text:
                    parsed_crs = pyproj.CRS.from_wkt(prj_text)
                    epsg = parsed_crs.to_epsg()
                    source_crs = f"EPSG:{epsg}" if epsg else parsed_crs.to_string()
            except Exception:
                # Fallback to EPSG:4326 if PRJ cannot be parsed
                source_crs = "EPSG:4326"

        try:
            shp_io = io.BytesIO(zf.read(shp_path))
            shx_io = io.BytesIO(zf.read(shx_name))
            dbf_io = io.BytesIO(zf.read(dbf_name))

            sf = shapefile.Reader(shp=shp_io, shx=shx_io, dbf=dbf_io, encoding="utf-8", encodingErrors="replace")
            features: List[ParsedFeature] = []

            for idx, sr in enumerate(sf.shapeRecords()):
                raw_shape = sr.shape
                props = sr.record.as_dict()

                if raw_shape.shapeType == shapefile.NULL:
                    features.append(ParsedFeature(
                        feature_index=idx,
                        geometry_type="NullShape",
                        shapely_geom=None,
                        geometry_geojson={"type": "GeometryCollection", "geometries": []},
                        properties=props,
                        source_crs=source_crs,
                        is_valid=False,
                        error_message="Feature contains NULL shape geometry"
                    ))
                    continue

                try:
                    geo_interface = raw_shape.__geo_interface__
                    geom = shape(geo_interface)
                    
                    # Validate geometry
                    if not geom.is_valid:
                        geom = make_valid(geom)
                    
                    features.append(ParsedFeature(
                        feature_index=idx,
                        geometry_type=geom.geom_type,
                        shapely_geom=geom,
                        geometry_geojson=shapely.geometry.mapping(geom),
                        properties=props,
                        source_crs=source_crs,
                        is_valid=True
                    ))
                except Exception as e:
                    features.append(ParsedFeature(
                        feature_index=idx,
                        geometry_type="Unknown",
                        shapely_geom=None,
                        geometry_geojson={},
                        properties=props,
                        source_crs=source_crs,
                        is_valid=False,
                        error_message=f"Failed to parse shape geometry: {str(e)}"
                    ))

            return features, source_crs, "shapefile"

        except Exception as e:
            if isinstance(e, FileProcessingError):
                raise
            raise FileProcessingError(f"Error parsing Shapefile records: {str(e)}")

    # =========================================================================
    # KML / KMZ Parser
    # =========================================================================

    @classmethod
    def parse_kmz(cls, kmz_bytes: bytes) -> Tuple[List[ParsedFeature], str, str]:
        """Parses a KMZ (Zipped KML) file."""
        with zipfile.ZipFile(io.BytesIO(kmz_bytes)) as zf:
            kml_files = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_files:
                raise FileProcessingError("No .kml file found inside KMZ archive.")
            kml_bytes = zf.read(kml_files[0])
            return cls.parse_kml(kml_bytes)

    @classmethod
    def parse_kml(cls, kml_bytes: bytes) -> Tuple[List[ParsedFeature], str, str]:
        """
        Parses a KML file into features.
        KML standard OGC 07-147r2 dictates WGS84 (EPSG:4326) coordinates.
        """
        try:
            # Strip XML namespace for clean XPath querying
            root = ET.fromstring(kml_bytes)
            for elem in root.iter():
                if "}" in elem.tag:
                    elem.tag = elem.tag.split("}", 1)[1]
        except Exception as e:
            raise FileProcessingError(f"Failed to parse KML XML document: {str(e)}")

        source_crs = "EPSG:4326"
        placemarks = root.findall(".//Placemark")
        features: List[ParsedFeature] = []

        for idx, pm in enumerate(placemarks):
            name_elem = pm.find("name")
            name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else f"Placemark_{idx}"

            desc_elem = pm.find("description")
            desc = desc_elem.text.strip() if (desc_elem is not None and desc_elem.text) else ""

            properties = {"name": name}
            if desc:
                properties["description"] = desc

            # ExtendedData: Data / SimpleData
            for data in pm.findall(".//ExtendedData/Data"):
                attr_name = data.get("name")
                val_node = data.find("value")
                if attr_name and val_node is not None and val_node.text:
                    properties[attr_name] = val_node.text.strip()

            for sdata in pm.findall(".//ExtendedData/SchemaData/SimpleData"):
                attr_name = sdata.get("name")
                if attr_name and sdata.text:
                    properties[attr_name] = sdata.text.strip()

            # Parse Geometries
            geom, geom_type, err = cls._extract_kml_geometry(pm)
            
            if geom is not None:
                if not geom.is_valid:
                    geom = make_valid(geom)
                geojson_geom = shapely.geometry.mapping(geom)
                features.append(ParsedFeature(
                    feature_index=idx,
                    geometry_type=geom.geom_type,
                    shapely_geom=geom,
                    geometry_geojson=geojson_geom,
                    properties=properties,
                    source_crs=source_crs,
                    is_valid=True
                ))
            else:
                features.append(ParsedFeature(
                    feature_index=idx,
                    geometry_type=geom_type or "Unknown",
                    shapely_geom=None,
                    geometry_geojson={},
                    properties=properties,
                    source_crs=source_crs,
                    is_valid=False,
                    error_message=err or "No recognizable geometry in Placemark"
                ))

        return features, source_crs, "kml"

    @classmethod
    def _extract_kml_geometry(cls, pm: ET.Element) -> Tuple[Optional[BaseGeometry], Optional[str], Optional[str]]:
        """Extracts Shapely geometry from a Placemark element."""
        # 1. Check MultiGeometry first
        mg_node = pm.find(".//MultiGeometry")
        if mg_node is not None:
            geoms = []
            for child in mg_node:
                tag = child.tag.lower()
                if tag == "polygon":
                    g = cls._parse_kml_polygon(child)
                    if g: geoms.append(g)
                elif tag == "linestring":
                    g = cls._parse_kml_linestring(child)
                    if g: geoms.append(g)
                elif tag == "point":
                    g = cls._parse_kml_point(child)
                    if g: geoms.append(g)
            
            if geoms:
                if all(g.geom_type == "Polygon" for g in geoms):
                    return MultiPolygon(geoms), "MultiPolygon", None
                elif all(g.geom_type == "LineString" for g in geoms):
                    return MultiLineString(geoms), "MultiLineString", None
                elif all(g.geom_type == "Point" for g in geoms):
                    return MultiPoint(geoms), "MultiPoint", None
                else:
                    return GeometryCollection(geoms), "GeometryCollection", None

        # 2. Polygon
        poly_node = pm.find(".//Polygon")
        if poly_node is not None:
            geom = cls._parse_kml_polygon(poly_node)
            if geom:
                return geom, "Polygon", None

        # 3. LineString
        line_node = pm.find(".//LineString")
        if line_node is not None:
            geom = cls._parse_kml_linestring(line_node)
            if geom:
                return geom, "LineString", None

        # 4. Point
        point_node = pm.find(".//Point")
        if point_node is not None:
            geom = cls._parse_kml_point(point_node)
            if geom:
                return geom, "Point", None

        return None, None, "No supported geometry found in Placemark"

    @staticmethod
    def _parse_coordinate_string(coords_str: str) -> List[Tuple[float, float]]:
        """Parses KML coordinate tuples: 'lon,lat,alt lon,lat,alt'."""
        points = []
        raw_items = coords_str.strip().split()
        for item in raw_items:
            tokens = [t.strip() for t in item.split(",") if t.strip()]
            if len(tokens) >= 2:
                try:
                    lon = float(tokens[0])
                    lat = float(tokens[1])
                    points.append((lon, lat))
                except ValueError:
                    continue
        return points

    @classmethod
    def _parse_kml_point(cls, point_node: ET.Element) -> Optional[Point]:
        coord_elem = point_node.find("coordinates")
        if coord_elem is not None and coord_elem.text:
            coords = cls._parse_coordinate_string(coord_elem.text)
            if coords:
                return Point(coords[0])
        return None

    @classmethod
    def _parse_kml_linestring(cls, line_node: ET.Element) -> Optional[LineString]:
        coord_elem = line_node.find("coordinates")
        if coord_elem is not None and coord_elem.text:
            coords = cls._parse_coordinate_string(coord_elem.text)
            if len(coords) >= 2:
                return LineString(coords)
        return None

    @classmethod
    def _parse_kml_polygon(cls, poly_node: ET.Element) -> Optional[Polygon]:
        outer_node = poly_node.find(".//outerBoundaryIs/LinearRing/coordinates")
        if outer_node is None or not outer_node.text:
            return None
        outer_coords = cls._parse_coordinate_string(outer_node.text)
        if len(outer_coords) < 3:
            return None

        # Parse interior holes if any
        inner_holes = []
        for inner_node in poly_node.findall(".//innerBoundaryIs/LinearRing/coordinates"):
            if inner_node.text:
                in_coords = cls._parse_coordinate_string(inner_node.text)
                if len(in_coords) >= 3:
                    inner_holes.append(in_coords)

        return Polygon(outer_coords, inner_holes)
