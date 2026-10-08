from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, Query, status
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.file_service import FileService
from app.api.schemas import (
    FileResponse,
    FileMeasurementsResponse,
    FileListResponse,
    MessageResponse
)

router = APIRouter(prefix="/files", tags=["Files"])


@router.post(
    "/",
    response_model=FileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and process a geospatial file",
    description=(
        "Accepts a `.zip` archive containing a Shapefile (.shp, .shx, .dbf, .prj) "
        "or a `.kml` file. Validates, extracts features, detects CRS, and computes "
        "accurate geometric measurements."
    )
)
async def upload_file(
    file: UploadFile = File(..., description="Geospatial file (.zip Shapefile or .kml)"),
    db: Session = Depends(get_db)
):
    record = await FileService.process_uploaded_file(file, db)
    return record.to_dict()


@router.get(
    "/{file_id}/",
    response_model=FileResponse,
    summary="Get file information",
    description="Returns metadata and processing status for an uploaded file by its ID."
)
def get_file_info(
    file_id: str,
    db: Session = Depends(get_db)
):
    record = FileService.get_file_by_id(file_id, db)
    return record.to_dict()


@router.get(
    "/{file_id}/measurements/",
    response_model=FileMeasurementsResponse,
    summary="Get geometric measurements",
    description=(
        "Returns calculated measurements (Area for Polygons, Length for LineStrings) "
        "for all features in the file, along with aggregated statistics and CRS details."
    )
)
def get_file_measurements(
    file_id: str,
    db: Session = Depends(get_db)
):
    return FileService.get_file_measurements(file_id, db)


@router.get(
    "/",
    response_model=FileListResponse,
    summary="List uploaded files",
    description="Retrieves a paginated list of all uploaded geospatial files."
)
def list_files(
    skip: int = Query(0, ge=0, description="Offset index"),
    limit: int = Query(50, ge=1, le=100, description="Max files to return"),
    db: Session = Depends(get_db)
):
    records, total = FileService.list_files(db, skip=skip, limit=limit)
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": [r.to_dict() for r in records]
    }


@router.get(
    "/{file_id}/geojson/",
    summary="Export features as GeoJSON",
    description="Exports all features as a standard GeoJSON FeatureCollection."
)
def export_geojson(
    file_id: str,
    db: Session = Depends(get_db)
):
    record = FileService.get_file_by_id(file_id, db)
    geojson_features = []
    for feat in record.features:
        feat_dict = feat.to_dict()
        props = dict(feat_dict.get("properties") or {})
        props["feature_id"] = feat_dict.get("feature_id")
        props["status"] = feat_dict.get("status")
        props["projected_crs"] = feat_dict.get("projected_crs")
        props["measurements"] = feat_dict.get("measurements")

        geojson_features.append({
            "type": "Feature",
            "id": feat_dict.get("feature_id"),
            "geometry": feat_dict.get("geometry"),
            "properties": props
        })

    return {
        "type": "FeatureCollection",
        "file_id": record.id,
        "filename": record.filename,
        "crs": record.crs,
        "features": geojson_features
    }


@router.delete(
    "/{file_id}/",
    response_model=MessageResponse,
    summary="Delete a file",
    description="Deletes a file, its extracted features, and local disk storage."
)
def delete_file(
    file_id: str,
    db: Session = Depends(get_db)
):
    FileService.delete_file(file_id, db)
    return {"message": f"File '{file_id}' deleted successfully."}
