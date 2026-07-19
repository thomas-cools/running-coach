from running_coach.config import Settings
from running_coach.domain import (
    CompletedActivity,
    ImportErrorCode,
    ImportFailure,
    MetricAvailability,
    ParsedActivity,
    ParserProvenance,
)
from running_coach.parsers import ActivityParser


def normalize_activity(
    parsed: ParsedActivity,
    parser: ActivityParser,
    athlete_id: str,
    checksum: str,
    settings: Settings,
) -> CompletedActivity:
    if parsed.sport.lower() != "running":
        raise ImportFailure(
            ImportErrorCode.UNSUPPORTED_ACTIVITY_TYPE,
            "Only completed running activities are supported.",
        )
    if not parsed.started_at or not parsed.duration_seconds or parsed.distance_meters is None:
        raise ImportFailure(
            ImportErrorCode.MISSING_REQUIRED_DATA,
            "The activity is missing required timing or distance data.",
        )
    if parsed.duration_seconds > settings.max_activity_duration_seconds:
        raise ImportFailure(
            ImportErrorCode.PROCESSING_LIMIT_EXCEEDED, "The activity exceeds the duration limit."
        )
    if len(parsed.samples) > settings.max_sample_count:
        raise ImportFailure(
            ImportErrorCode.PROCESSING_LIMIT_EXCEEDED, "The activity exceeds the sample limit."
        )
    metrics = MetricAvailability(
        heart_rate=any(sample.heart_rate_bpm is not None for sample in parsed.samples),
        cadence=any(sample.cadence_spm is not None for sample in parsed.samples),
        elevation=any(sample.elevation_meters is not None for sample in parsed.samples),
        route=any(
            sample.latitude is not None and sample.longitude is not None
            for sample in parsed.samples
        ),
    )
    return CompletedActivity(
        athlete_id=athlete_id,
        checksum=checksum,
        started_at=parsed.started_at,
        duration_seconds=parsed.duration_seconds,
        distance_meters=parsed.distance_meters,
        samples=parsed.samples,
        laps=parsed.laps,
        metrics=metrics,
        provenance=ParserProvenance(
            source_format=parser.source_format,
            parser_name=parser.name,
            parser_version=parser.version,
        ),
    )
