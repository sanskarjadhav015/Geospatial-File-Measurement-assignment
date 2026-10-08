import math
from typing import Optional, Tuple
import numpy as np
import pyproj
import shapely
from shapely.geometry.base import BaseGeometry

from app.core.exceptions import CRSError


class CRSTransformerService:
    """
    Handles CRS detection and coordinate transformations.
    Converts coordinates from geographic (degrees like EPSG:4326) to an appropriate
    projected CRS (like UTM) so that area and length can be accurately measured in meters.
    """

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> pyproj.CRS:
        """
        Parses a CRS from an EPSG string, PROJ string, or WKT.
        Defaults to EPSG:4326 if not provided or empty.
        """
        if not crs_input or not crs_input.strip():
            return pyproj.CRS.from_epsg(4326)

        crs_str = crs_input.strip()
        try:
            # Handle plain numbers like '4326' or 'EPSG:4326'
            if crs_str.isdigit():
                return pyproj.CRS.from_epsg(int(crs_str))
            return pyproj.CRS.from_user_input(crs_str)
        except Exception as e:
            try:
                # Attempt to parse as WKT
                return pyproj.CRS.from_wkt(crs_str)
            except Exception:
                raise CRSError(f"Unable to parse CRS definition '{crs_str}': {str(e)}")

    @staticmethod
    def determine_optimal_projected_crs(
        geometry: BaseGeometry,
        source_crs: pyproj.CRS
    ) -> Tuple[pyproj.CRS, str]:
        """
        Determines the optimal projected coordinate system for a given geometry.
        
        Strategy:
        1. If source CRS is already projected, retain it if in linear meters/feet.
        2. If source CRS is geographic:
           - Calculate geometry centroid (lon, lat).
           - For polar latitudes (> 84° N or < -80° S): UPS (Universal Polar Stereographic).
           - For standard latitudes: calculate exact UTM Zone (1-60), hemisphere (N/S).
           - For wide-spanning bounding boxes (> 6° longitude span): use World Cylindrical
             Equal Area (EPSG:6933) to preserve area accuracy across multiple zones.
        """
        if source_crs.is_projected:
            # Already projected
            epsg = source_crs.to_epsg()
            crs_name = f"EPSG:{epsg}" if epsg else source_crs.name
            return source_crs, f"Source CRS is already projected ({crs_name})"

        # Source is geographic; ensure we inspect coordinates in EPSG:4326
        if source_crs.to_epsg() != 4326:
            # Transform centroid to WGS84 to identify UTM zone
            to_wgs84 = pyproj.Transformer.from_crs(source_crs, pyproj.CRS.from_epsg(4326), always_xy=True)
            c = geometry.centroid
            cx, cy = to_wgs84.transform(c.x, c.y)
        else:
            c = geometry.centroid
            cx, cy = c.x, c.y

        # Check bounds span
        minx, miny, maxx, maxy = geometry.bounds
        lon_span = abs(maxx - minx)

        # Extreme polar regions
        if cy > 84.0:
            target_epsg = 32661  # UPS North
            return pyproj.CRS.from_epsg(target_epsg), "Universal Polar Stereographic North (EPSG:32661)"
        elif cy < -80.0:
            target_epsg = 32761  # UPS South
            return pyproj.CRS.from_epsg(target_epsg), "Universal Polar Stereographic South (EPSG:32761)"

        # Wide features spanning more than a single UTM zone (6 degrees)
        if lon_span > 6.0:
            # EPSG:6933 (World Cylindrical Equal Area) preserves equal area globally
            target_epsg = 6933
            return pyproj.CRS.from_epsg(target_epsg), "World Cylindrical Equal Area (EPSG:6933) for wide-span feature"

        # Standard UTM Zone calculation:
        # Longitude range -180 to 180 maps to zones 1 to 60
        zone = int((cx + 180) / 6) + 1
        zone = max(1, min(60, zone))

        if cy >= 0:
            target_epsg = 32600 + zone
            desc = f"UTM Zone {zone}N (EPSG:{target_epsg})"
        else:
            target_epsg = 32700 + zone
            desc = f"UTM Zone {zone}S (EPSG:{target_epsg})"

        return pyproj.CRS.from_epsg(target_epsg), desc

    @classmethod
    def transform_geometry(
        cls,
        geometry: BaseGeometry,
        source_crs: pyproj.CRS,
        target_crs: pyproj.CRS
    ) -> BaseGeometry:
        """
        Transforms a Shapely geometry from source_crs to target_crs using
        vectorized coordinate mapping with always_xy=True.
        Handles 2D and 3D coordinate geometries gracefully.
        """
        if source_crs == target_crs:
            return geometry

        transformer = pyproj.Transformer.from_crs(source_crs, target_crs, always_xy=True)

        def transform_coords(coords):
            # coords is a numpy array of shape (N, 2) or (N, 3)
            coords_arr = np.asarray(coords)
            x = coords_arr[:, 0]
            y = coords_arr[:, 1]
            tx, ty = transformer.transform(x, y)
            
            if coords_arr.shape[1] >= 3:
                # Preserve Z if present
                z = coords_arr[:, 2]
                return np.column_stack((tx, ty, z))
            return np.column_stack((tx, ty))

        try:
            return shapely.transform(geometry, transform_coords)
        except Exception as e:
            raise CRSError(f"Failed to transform geometry between CRS: {str(e)}")
