import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Ensure test settings point to real PostgreSQL test database
os.environ["DATABASE_URL"] = "postgresql://postgres:postgrespassword@localhost:5432/lenny_growth_test"
os.environ["APP_ENV"] = "test"

from app.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app

# Connect to real PostgreSQL test database with pgvector
test_engine = create_engine(
    settings.test_database_url or settings.database_url,
    pool_pre_ping=True,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Ensure pgvector extension and tables exist on real PostgreSQL test database."""
    with test_engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=test_engine)
    yield
    # Tables are left intact or can be dropped


@pytest.fixture
def db():
    """Provide a clean database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        # Clean data between tests
        with test_engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE messages, artifacts, sessions, transcript_chunks CASCADE;"))
        session.close()


@pytest.fixture
def client(db):
    """Provide a FastAPI TestClient using the real PostgreSQL test database."""
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
