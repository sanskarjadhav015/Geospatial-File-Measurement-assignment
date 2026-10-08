from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    DESCRIPTION: str = (
        "Production-grade backend service for processing geospatial files "
        "(Shapefiles and KML) and calculating high-precision geometric measurements "
        "with intelligent CRS reprojection."
    )
    
    # Base paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    DATA_DIR: Path = BASE_DIR / "data"
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'geospatial.db'}"
    
    # Upload limits
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: set = {".zip", ".kml"}
    
    model_config = SettingsConfigDict(case_sensitive=True)

settings = Settings()

# Ensure required directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
