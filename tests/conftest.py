import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.database import Base, get_db

TEST_DIR = Path(__file__).resolve().parent
SAMPLE_DIR = TEST_DIR.parent / "sample_data"

# In-memory SQLite with StaticPool so all connections share the same database
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """Provides a fresh database session per test function with created schema."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Provides a TestClient with overridden database dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_polygons_zip():
    return SAMPLE_DIR / "sample_polygons.zip"


@pytest.fixture
def sample_lines_zip():
    return SAMPLE_DIR / "sample_lines.zip"


@pytest.fixture
def sample_points_zip():
    return SAMPLE_DIR / "sample_points.zip"


@pytest.fixture
def sample_survey_kml():
    return SAMPLE_DIR / "sample_survey.kml"


@pytest.fixture
def sample_donut_kml():
    return SAMPLE_DIR / "sample_donut.kml"
