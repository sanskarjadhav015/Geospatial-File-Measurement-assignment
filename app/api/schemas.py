from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class FileResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Detected file type ('shapefile' or 'kml')")
    file_size_bytes: int = Field(..., description="Size of uploaded file in bytes")
    feature_count: int = Field(..., description="Total number of extracted geospatial features")
    crs: str = Field(..., description="Detected or default Coordinate Reference System")
    status: str = Field(..., description="Processing status ('COMPLETED', 'FAILED', 'PROCESSING')")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    created_at: Optional[str] = Field(None, description="ISO timestamp of upload")
    processed_at: Optional[str] = Field(None, description="ISO timestamp of processing completion")

    model_config = ConfigDict(from_attributes=True)


class FeatureMeasurementItem(BaseModel):
    feature_id: int = Field(..., description="Zero-based feature index")
    geometry_type: str = Field(..., description="Geometry type (e.g. Polygon, LineString, Point)")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON geometry representation")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Feature attributes and metadata")
    source_crs: str = Field(..., description="Source Coordinate Reference System")
    projected_crs: Optional[str] = Field(None, description="Projected CRS used for measurement")
    projection_method: Optional[str] = Field(None, description="Strategy/description for CRS projection")
    measurements: Optional[Dict[str, Any]] = Field(None, description="Calculated measurements (area/length/perimeter)")
    status: str = Field(..., description="Measurement status ('MEASURED', 'SKIPPED', 'UNSUPPORTED', 'ERROR')")
    notes: Optional[str] = Field(None, description="Informational notes or explanation")

    model_config = ConfigDict(from_attributes=True)


class MeasurementSummary(BaseModel):
    total_features: int = Field(..., description="Total features in the file")
    polygons_count: int = Field(..., description="Number of Polygon / MultiPolygon features")
    total_area_sq_meters: float = Field(..., description="Total cumulative area in square meters")
    total_area_hectares: float = Field(..., description="Total cumulative area in hectares")
    total_area_sq_km: float = Field(..., description="Total cumulative area in square kilometers")
    linestrings_count: int = Field(..., description="Number of LineString / MultiLineString features")
    total_length_meters: float = Field(..., description="Total cumulative length in meters")
    total_length_km: float = Field(..., description="Total cumulative length in kilometers")
    points_count: int = Field(..., description="Number of Point / MultiPoint features")
    unsupported_count: int = Field(..., description="Number of unsupported geometry features")
    errors_count: int = Field(..., description="Number of features that encountered errors")


class FileMeasurementsResponse(BaseModel):
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Uploaded file name")
    file_type: str = Field(..., description="Geospatial file type")
    source_crs: str = Field(..., description="Source CRS")
    status: str = Field(..., description="Overall file status")
    total_features: int = Field(..., description="Total number of features")
    summary: MeasurementSummary = Field(..., description="Cumulative measurement statistics")
    features: List[FeatureMeasurementItem] = Field(..., description="List of measured features")


class FileListResponse(BaseModel):
    total: int = Field(..., description="Total number of files")
    skip: int = Field(..., description="Pagination offset")
    limit: int = Field(..., description="Pagination limit")
    items: List[FileResponse] = Field(..., description="List of files")


class MessageResponse(BaseModel):
    message: str
    detail: Optional[str] = None
