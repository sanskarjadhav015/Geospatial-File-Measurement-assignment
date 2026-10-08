import pytest
import pyproj
from shapely.geometry import Point, Polygon, LineString

from app.core.crs_transformer import CRSTransformerService
from app.core.exceptions import CRSError


def test_parse_crs_standard_inputs():
    crs_wgs84 = CRSTransformerService.parse_crs("EPSG:4326")
    assert crs_wgs84.to_epsg() == 4326

    crs_numeric = CRSTransformerService.parse_crs("3857")
    assert crs_numeric.to_epsg() == 3857

    crs_default = CRSTransformerService.parse_crs("")
    assert crs_default.to_epsg() == 4326


def test_parse_crs_invalid_input():
    with pytest.raises(CRSError):
        CRSTransformerService.parse_crs("INVALID_CRS_STRING_12345")


def test_utm_zone_selection_global_locations():
    src_crs = pyproj.CRS.from_epsg(4326)

    # 1. New York City (-73.98, 40.75) -> Zone 18N (EPSG:32618)
    ny_poly = Polygon([(-74.0, 40.7), (-73.9, 40.7), (-73.9, 40.8), (-74.0, 40.8), (-74.0, 40.7)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(ny_poly, src_crs)
    assert target_crs.to_epsg() == 32618
    assert "18N" in desc

    # 2. London (-0.12, 51.5) -> Zone 30N (EPSG:32630)
    london_pt = Polygon([(-0.2, 51.4), (-0.05, 51.4), (-0.05, 51.6), (-0.2, 51.6), (-0.2, 51.4)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(london_pt, src_crs)
    assert target_crs.to_epsg() == 32630
    assert "30N" in desc

    # 3. Sydney (151.2, -33.8) -> Zone 56S (EPSG:32756)
    sydney_poly = Polygon([(151.1, -33.9), (151.3, -33.9), (151.3, -33.7), (151.1, -33.7), (151.1, -33.9)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(sydney_poly, src_crs)
    assert target_crs.to_epsg() == 32756
    assert "56S" in desc


def test_polar_region_fallbacks():
    src_crs = pyproj.CRS.from_epsg(4326)

    # Extreme North (lat > 84) -> UPS North (EPSG:32661)
    north_pole_poly = Polygon([(0.0, 85.0), (1.0, 85.0), (1.0, 86.0), (0.0, 86.0), (0.0, 85.0)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(north_pole_poly, src_crs)
    assert target_crs.to_epsg() == 32661

    # Extreme South (lat < -80) -> UPS South (EPSG:32761)
    south_pole_poly = Polygon([(0.0, -82.0), (1.0, -82.0), (1.0, -83.0), (0.0, -83.0), (0.0, -82.0)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(south_pole_poly, src_crs)
    assert target_crs.to_epsg() == 32761


def test_wide_span_feature_fallback():
    src_crs = pyproj.CRS.from_epsg(4326)
    # Feature spanning 15 degrees longitude (crossing multiple UTM zones)
    wide_poly = Polygon([(10.0, 45.0), (25.0, 45.0), (25.0, 48.0), (10.0, 48.0), (10.0, 45.0)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(wide_poly, src_crs)
    assert target_crs.to_epsg() == 6933  # World Cylindrical Equal Area


def test_already_projected_crs_retained():
    src_crs = pyproj.CRS.from_epsg(32618)  # Already projected UTM 18N
    poly = Polygon([(580000, 4510000), (581000, 4510000), (581000, 4511000), (580000, 4511000), (580000, 4510000)])
    target_crs, desc = CRSTransformerService.determine_optimal_projected_crs(poly, src_crs)
    assert target_crs.to_epsg() == 32618
    assert "already projected" in desc.lower()


def test_geometry_transformation():
    src_crs = pyproj.CRS.from_epsg(4326)
    tgt_crs = pyproj.CRS.from_epsg(32618)
    ny_line = LineString([(-73.985, 40.758), (-73.980, 40.763)])

    transformed = CRSTransformerService.transform_geometry(ny_line, src_crs, tgt_crs)
    assert transformed.geom_type == "LineString"
    assert transformed.coords[0][0] > 100_000  # Linear meters in UTM
    assert transformed.coords[0][1] > 1_000_000
