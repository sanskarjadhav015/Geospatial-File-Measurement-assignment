import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.models.database import Base


def generate_uuid():
    return uuid.uuid4().hex[:12]


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String(32), primary_key=True, default=generate_uuid, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(32), nullable=False)  # 'shapefile' or 'kml'
    file_size_bytes = Column(Integer, nullable=False)
    feature_count = Column(Integer, default=0)
    crs = Column(String(100), default="EPSG:4326")
    status = Column(String(32), default="PROCESSING")  # 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    features = relationship(
        "FeatureRecord",
        back_populates="file",
        cascade="all, delete-orphan",
        order_by="FeatureRecord.feature_index"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size_bytes": self.file_size_bytes,
            "feature_count": self.feature_count,
            "crs": self.crs,
            "status": self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
        }


class FeatureRecord(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(32), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    geometry_type = Column(String(64), nullable=False)
    geometry_geojson = Column(JSON, nullable=False)
    properties = Column(JSON, default=dict)
    source_crs = Column(String(100), default="EPSG:4326")
    projected_crs = Column(String(100), nullable=True)
    projection_method = Column(String(255), nullable=True)
    measurements = Column(JSON, nullable=True)
    status = Column(String(32), default="MEASURED")  # 'MEASURED', 'UNSUPPORTED', 'ERROR'
    notes = Column(Text, nullable=True)

    file = relationship("FileRecord", back_populates="features")

    def to_dict(self):
        return {
            "feature_id": self.feature_index,
            "geometry_type": self.geometry_type,
            "geometry": self.geometry_geojson,
            "properties": self.properties or {},
            "source_crs": self.source_crs,
            "projected_crs": self.projected_crs,
            "projection_method": self.projection_method,
            "measurements": self.measurements or {},
            "status": self.status,
            "notes": self.notes
        }
