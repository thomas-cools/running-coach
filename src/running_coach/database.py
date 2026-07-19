from collections.abc import Generator
from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from running_coach.config import Settings
from running_coach.domain import CompletedActivity


class Base(DeclarativeBase):
    pass


class ActivityRecord(Base):
    __tablename__ = "completed_activities"
    __table_args__ = (
        UniqueConstraint("athlete_id", "checksum", name="uq_activity_athlete_checksum"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    athlete_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    import_status: Mapped[str] = mapped_column(String(16), nullable=False, default="imported")
    source_format: Mapped[str] = mapped_column(String(8), nullable=False)
    parser_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    distance_meters: Mapped[float] = mapped_column(Float, nullable=False)
    metrics: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    samples: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)
    laps: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False)


def create_session_factory(settings: Settings) -> sessionmaker[Session]:
    return sessionmaker(bind=create_engine(settings.database_url), expire_on_commit=False)


def sessions(factory: sessionmaker[Session]) -> Generator[Session]:
    with factory() as session:
        yield session


def activity_record(activity: CompletedActivity) -> ActivityRecord:
    return ActivityRecord(
        athlete_id=activity.athlete_id,
        checksum=activity.checksum,
        source_format=activity.provenance.source_format.value,
        parser_name=activity.provenance.parser_name,
        parser_version=activity.provenance.parser_version,
        started_at=activity.started_at,
        duration_seconds=activity.duration_seconds,
        distance_meters=activity.distance_meters,
        metrics=activity.metrics.model_dump(),
        samples=[sample.model_dump(mode="json") for sample in activity.samples],
        laps=[lap.model_dump(mode="json") for lap in activity.laps],
    )
