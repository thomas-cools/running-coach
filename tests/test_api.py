from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from running_coach.auth import authenticate_athlete
from running_coach.database import Base
from running_coach.main import app, get_session

FIXTURES = Path(__file__).parent / "fixtures"


def test_upload_requires_authentication() -> None:
    with TestClient(app) as client:
        response = client.post("/activities/import", files={"file": ("run.tcx", b"content")})

    assert response.status_code == 401


def test_authenticated_upload_uses_athlete_identity() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    async def athlete() -> str:
        return "athlete-1"

    def session() -> Session:
        with Session(engine) as database_session:
            yield database_session

    app.dependency_overrides[authenticate_athlete] = athlete
    app.dependency_overrides[get_session] = session
    try:
        with TestClient(app) as client:
            response = client.post(
                "/activities/import",
                files={
                    "file": (
                        "run.tcx",
                        (FIXTURES / "running-rich.tcx").read_bytes(),
                        "application/vnd.garmin.tcx+xml",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["activity_id"]