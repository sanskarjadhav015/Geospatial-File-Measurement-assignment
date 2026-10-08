class GeospatialAppException(Exception):
    """Base exception for the Geospatial API application."""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

class FileUploadError(GeospatialAppException):
    """Raised when file upload validation fails."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=400)

class FileProcessingError(GeospatialAppException):
    """Raised when file reading, extracting, or parsing fails."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)

class CRSError(GeospatialAppException):
    """Raised when CRS detection, parsing, or transformation fails."""
    def __init__(self, message: str):
        super().__init__(message=message, status_code=422)

class ResourceNotFoundError(GeospatialAppException):
    """Raised when a requested resource (e.g., file ID) is not found."""
    def __init__(self, message: str = "Requested file not found"):
        super().__init__(message=message, status_code=404)
