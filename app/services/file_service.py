import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import FileUploadError, FileProcessingError, ResourceNotFoundError
from app.models.db_models import FileRecord, FeatureRecord, generate_uuid
from app.services.parser_service import GeospatialParserService
from app.services.measurement_service import MeasurementService


class FileService:
    """Orchestrates file upload, parsing, measurement calculation, and persistence."""

    @classmethod
    async def process_uploaded_file(cls, upload_file: UploadFile, db: Session) -> FileRecord:
        """
        Validates, saves, parses, measures, and stores a geospatial file.
        """
        filename = upload_file.filename or "unnamed_file"
        fn_lower = filename.lower()
        suffix = Path(fn_lower).suffix

        if suffix not in settings.ALLOWED_EXTENSIONS:
            raise FileUploadError(
                f"Unsupported file extension '{suffix}'. Supported extensions are .zip (Shapefile) and .kml."
            )

        # Read file bytes in memory with size check
        file_bytes = await upload_file.read()
        file_size = len(file_bytes)

        if file_size == 0:
            raise FileUploadError("Uploaded file is empty (0 bytes).")

        if file_size > settings.MAX_FILE_SIZE_BYTES:
            raise FileUploadError(
                f"File size exceeds maximum allowable limit of {settings.MAX_FILE_SIZE_BYTES // (1024*1024)}MB."
            )

        file_id = generate_uuid()
        saved_path = settings.UPLOAD_DIR / f"{file_id}_{Path(filename).name}"

        # Persist raw uploaded file to disk
        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        # Initialize FileRecord
        file_record = FileRecord(
            id=file_id,
            filename=filename,
            file_type="unknown",
            file_size_bytes=file_size,
            status="PROCESSING",
            created_at=datetime.now(timezone.utc)
        )
        db.add(file_record)
        db.commit()

        try:
            # 1. Parse file features
            parsed_features, detected_crs, file_type = GeospatialParserService.parse_file(
                filename, file_bytes
            )

            file_record.file_type = file_type
            file_record.crs = detected_crs
            file_record.feature_count = len(parsed_features)

            # 2. Compute measurements for each feature
            feature_records: List[FeatureRecord] = []
            for pf in parsed_features:
                measurements, proj_crs, proj_method, status, notes = MeasurementService.process_feature_measurement(
                    pf.shapely_geom, pf.source_crs
                )

                feat_rec = FeatureRecord(
                    file_id=file_id,
                    feature_index=pf.feature_index,
                    geometry_type=pf.geometry_type,
                    geometry_geojson=pf.geometry_geojson,
                    properties=pf.properties,
                    source_crs=pf.source_crs,
                    projected_crs=proj_crs,
                    projection_method=proj_method,
                    measurements=measurements,
                    status=status if pf.is_valid else "ERROR",
                    notes=notes if pf.is_valid else pf.error_message
                )
                feature_records.append(feat_rec)

            db.add_all(feature_records)
            file_record.status = "COMPLETED"
            file_record.processed_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(file_record)
            return file_record

        except Exception as e:
            db.rollback()
            file_record.status = "FAILED"
            file_record.error_message = str(e)
            db.commit()
            raise FileProcessingError(f"Error processing geospatial file: {str(e)}")

    @classmethod
    def get_file_by_id(cls, file_id: str, db: Session) -> FileRecord:
        """Retrieves a file record by ID."""
        record = db.query(FileRecord).filter(FileRecord.id == file_id).first()
        if not record:
            raise ResourceNotFoundError(f"File with ID '{file_id}' not found.")
        return record

    @classmethod
    def get_file_measurements(cls, file_id: str, db: Session) -> dict:
        """
        Retrieves measurements and aggregated summary for all features in a file.
        """
        file_record = cls.get_file_by_id(file_id, db)
        features = [f.to_dict() for f in file_record.features]
        summary = MeasurementService.calculate_file_summary(features)

        return {
            "file_id": file_record.id,
            "filename": file_record.filename,
            "file_type": file_record.file_type,
            "source_crs": file_record.crs,
            "status": file_record.status,
            "total_features": file_record.feature_count,
            "summary": summary,
            "features": features
        }

    @classmethod
    def list_files(cls, db: Session, skip: int = 0, limit: int = 50) -> Tuple[List[FileRecord], int]:
        """Lists uploaded files with pagination."""
        total = db.query(FileRecord).count()
        records = (
            db.query(FileRecord)
            .order_by(FileRecord.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return records, total

    @classmethod
    def delete_file(cls, file_id: str, db: Session) -> bool:
        """Deletes a file record and its associated uploaded file."""
        file_record = cls.get_file_by_id(file_id, db)
        # Delete file on disk
        for p in settings.UPLOAD_DIR.glob(f"{file_id}_*"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass

        db.delete(file_record)
        db.commit()
        return True
