from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from running_coach.config import Settings
from running_coach.database import ActivityRecord, Base
from running_coach.domain import ImportErrorCode
from running_coach.services import ActivityImportService

FIXTURES = Path(__file__).parent / "fixtures"


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


@pytest.mark.asyncio
async def test_failed_import_does_not_create_a_partial_activity() -> None:
    session = make_session()
    service = ActivityImportService(session, Settings(database_url="sqlite+pysqlite:///:memory:"))

    result = await service.import_upload(
        "athlete-1", "bad.gpx", (FIXTURES / "malformed.gpx").read_bytes()
    )

    assert result.error_code is ImportErrorCode.MALFORMED_FILE
    assert session.scalars(select(ActivityRecord)).all() == []


@pytest.mark.asyncio
async def test_duplicate_upload_returns_existing_activity() -> None:
    session = make_session()
    service = ActivityImportService(session, Settings(database_url="sqlite+pysqlite:///:memory:"))
    content = (FIXTURES / "running-rich.tcx").read_bytes()

    first = await service.import_upload("athlete-1", "run.tcx", content)
    duplicate = await service.import_upload("athlete-1", "run.tcx", content)

    assert first.activity_id is not None
    assert duplicate.activity_id == first.activity_id
    assert duplicate.duplicate is True
    assert len(session.scalars(select(ActivityRecord)).all()) == 1


@pytest.mark.asyncio
async def test_upload_limit_fails_without_persisting() -> None:
    session = make_session()
    settings = Settings(database_url="sqlite+pysqlite:///:memory:", max_upload_bytes=10)
    service = ActivityImportService(session, settings)

    result = await service.import_upload(
        "athlete-1", "run.tcx", (FIXTURES / "running-rich.tcx").read_bytes()
    )

    assert result.error_code is ImportErrorCode.PROCESSING_LIMIT_EXCEEDED
    assert session.scalars(select(ActivityRecord)).all() == []