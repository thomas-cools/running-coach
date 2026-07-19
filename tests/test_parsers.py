from pathlib import Path

import pytest

from running_coach.config import Settings
from running_coach.domain import ImportErrorCode, ImportFailure, SourceFormat
from running_coach.normalization import normalize_activity
from running_coach.parsers import detect_format, parse_activity

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_gpx_running_activity_preserves_absent_sensor_metrics() -> None:
    parsed, parser = parse_activity(fixture("running-without-sensors.gpx"), "activity.gpx")

    normalized = normalize_activity(
        parsed, parser, "athlete-1", "checksum", Settings(database_url="sqlite+pysqlite:///:memory:")
    )

    assert normalized.provenance.source_format is SourceFormat.GPX
    assert normalized.metrics.route is True
    assert normalized.metrics.elevation is True
    assert normalized.metrics.heart_rate is False
    assert normalized.metrics.cadence is False
    assert all(sample.heart_rate_bpm is None for sample in normalized.samples)


def test_tcx_running_activity_normalizes_rich_metrics() -> None:
    parsed, parser = parse_activity(fixture("running-rich.tcx"), "activity.tcx")

    normalized = normalize_activity(
        parsed, parser, "athlete-1", "checksum", Settings(database_url="sqlite+pysqlite:///:memory:")
    )

    assert normalized.distance_meters == 155.0
    assert len(normalized.laps) == 1
    assert normalized.metrics.heart_rate is True
    assert normalized.metrics.cadence is True
    assert normalized.samples[0].heart_rate_bpm == 142


@pytest.mark.parametrize(
    ("name", "filename", "code"),
    [
        ("malformed.gpx", "activity.gpx", ImportErrorCode.MALFORMED_FILE),
        ("cycling.tcx", "activity.tcx", ImportErrorCode.UNSUPPORTED_ACTIVITY_TYPE),
    ],
)
def test_invalid_activity_files_return_categorized_error(
    name: str, filename: str, code: ImportErrorCode
) -> None:
    with pytest.raises(ImportFailure) as error:
        parse_activity(fixture(name), filename)

    assert error.value.code is code


def test_content_and_declared_type_must_match() -> None:
    with pytest.raises(ImportFailure) as error:
        detect_format(fixture("running-rich.tcx"), "activity.gpx")

    assert error.value.code is ImportErrorCode.MALFORMED_FILE


def test_fit_signature_is_detected_before_parser_selection() -> None:
    fit_header = b"00000000.FIT"

    assert detect_format(fit_header, "activity.fit") is SourceFormat.FIT