from typing import Dict, Any, Tuple, Optional
import pyproj
from shapely.geometry.base import BaseGeometry

from app.core.crs_transformer import CRSTransformerService


class MeasurementService:
    """
    High-precision measurement calculation service.
    
    Adheres strictly to the requirement that geographic coordinates (degrees)
    are NEVER measured with Euclidean calculations. Automatically transforms
    geometries to an optimal projected CRS before computing planar area or length,
    and provides WGS84 geodesic metrics via pyproj.Geod for cross-validation.
    """

    SUPPORTED_AREA_TYPES = {"Polygon", "MultiPolygon"}
    SUPPORTED_LENGTH_TYPES = {"LineString", "MultiLineString"}
    POINT_TYPES = {"Point", "MultiPoint"}

    @classmethod
    def process_feature_measurement(
        cls,
        geom: Optional[BaseGeometry],
        source_crs_str: str
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str], str, Optional[str]]:
        """
        Calculates measurements for a single feature.
        
        Returns:
            (measurements_dict, projected_crs, projection_method, status, notes)
            status can be: 'MEASURED', 'SKIPPED', 'UNSUPPORTED', or 'ERROR'
        """
        if geom is None or geom.is_empty:
            return None, None, None, "ERROR", "Empty or null geometry provided"

        geom_type = geom.geom_type

        # 1. Point types: No measurement required
        if geom_type in cls.POINT_TYPES:
            return (
                None,
                source_crs_str,
                "No transformation needed for Point geometry",
                "SKIPPED",
                "No measurement required for Point geometry per specification."
            )

        # 2. Parse source CRS
        try:
            source_crs = CRSTransformerService.parse_crs(source_crs_str)
        except Exception as e:
            return None, None, None, "ERROR", f"CRS parsing error: {str(e)}"

        # 3. Polygon / MultiPolygon Area calculation
        if geom_type in cls.SUPPORTED_AREA_TYPES:
            try:
                target_crs, method_desc = CRSTransformerService.determine_optimal_projected_crs(
                    geom, source_crs
                )
                
                # Transform to projected CRS
                proj_geom = CRSTransformerService.transform_geometry(geom, source_crs, target_crs)
                
                area_m2 = proj_geom.area
                perimeter_m = proj_geom.length
                
                # Geodesic calculation if geographic source
                geodesic_area_m2 = None
                if source_crs.is_geographic:
                    try:
                        geod = pyproj.Geod(ellps="WGS84")
                        if geom_type == "Polygon":
                            # geod.geometry_area_perimeter returns (area, perimeter)
                            g_area, _ = geod.geometry_area_perimeter(geom)
                            geodesic_area_m2 = abs(g_area)
                    except Exception:
                        pass

                measurements = {
                    "area_sq_meters": round(area_m2, 2),
                    "area_hectares": round(area_m2 / 10_000.0, 4),
                    "area_sq_km": round(area_m2 / 1_000_000.0, 6),
                    "area_acres": round(area_m2 * 0.000247105, 4),
                    "perimeter_meters": round(perimeter_m, 2)
                }
                if geodesic_area_m2 is not None:
                    measurements["geodesic_area_sq_meters"] = round(geodesic_area_m2, 2)

                target_epsg = target_crs.to_epsg()
                target_crs_str = f"EPSG:{target_epsg}" if target_epsg else target_crs.name

                return measurements, target_crs_str, method_desc, "MEASURED", None

            except Exception as e:
                return None, None, None, "ERROR", f"Failed calculating polygon area: {str(e)}"

        # 4. LineString / MultiLineString Length calculation
        elif geom_type in cls.SUPPORTED_LENGTH_TYPES:
            try:
                target_crs, method_desc = CRSTransformerService.determine_optimal_projected_crs(
                    geom, source_crs
                )
                proj_geom = CRSTransformerService.transform_geometry(geom, source_crs, target_crs)
                
                length_m = proj_geom.length
                
                # Geodesic length if geographic source
                geodesic_length_m = None
                if source_crs.is_geographic:
                    try:
                        geod = pyproj.Geod(ellps="WGS84")
                        if geom_type == "LineString":
                            g_len = geod.geometry_length(geom)
                            geodesic_length_m = abs(g_len)
                    except Exception:
                        pass

                measurements = {
                    "length_meters": round(length_m, 2),
                    "length_km": round(length_m / 1000.0, 4),
                    "length_miles": round(length_m * 0.000621371, 4)
                }
                if geodesic_length_m is not None:
                    measurements["geodesic_length_meters"] = round(geodesic_length_m, 2)

                target_epsg = target_crs.to_epsg()
                target_crs_str = f"EPSG:{target_epsg}" if target_epsg else target_crs.name

                return measurements, target_crs_str, method_desc, "MEASURED", None

            except Exception as e:
                return None, None, None, "ERROR", f"Failed calculating linestring length: {str(e)}"

        # 5. Unsupported geometry types (handled gracefully per specification)
        else:
            return (
                None,
                source_crs_str,
                "No transformation applied",
                "UNSUPPORTED",
                f"Geometry type '{geom_type}' is not supported for measurement calculation."
            )

    @classmethod
    def calculate_file_summary(cls, features_data: list) -> Dict[str, Any]:
        """
        Aggregates measurements across all features of a file.
        """
        polygons_count = 0
        total_area_m2 = 0.0
        linestrings_count = 0
        total_length_m = 0.0
        points_count = 0
        unsupported_count = 0
        errors_count = 0

        for f in features_data:
            status = f.get("status")
            gtype = f.get("geometry_type")
            meas = f.get("measurements") or {}

            if status == "MEASURED":
                if gtype in cls.SUPPORTED_AREA_TYPES:
                    polygons_count += 1
                    total_area_m2 += meas.get("area_sq_meters", 0.0)
                elif gtype in cls.SUPPORTED_LENGTH_TYPES:
                    linestrings_count += 1
                    total_length_m += meas.get("length_meters", 0.0)
            elif status == "SKIPPED" or gtype in cls.POINT_TYPES:
                points_count += 1
            elif status == "UNSUPPORTED":
                unsupported_count += 1
            elif status == "ERROR":
                errors_count += 1

        return {
            "total_features": len(features_data),
            "polygons_count": polygons_count,
            "total_area_sq_meters": round(total_area_m2, 2),
            "total_area_hectares": round(total_area_m2 / 10_000.0, 4),
            "total_area_sq_km": round(total_area_m2 / 1_000_000.0, 6),
            "linestrings_count": linestrings_count,
            "total_length_meters": round(total_length_m, 2),
            "total_length_km": round(total_length_m / 1000.0, 4),
            "points_count": points_count,
            "unsupported_count": unsupported_count,
            "errors_count": errors_count
        }
