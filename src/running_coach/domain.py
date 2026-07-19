from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


class SourceFormat(StrEnum):
    FIT = "fit"
    GPX = "gpx"
    TCX = "tcx"


class ImportErrorCode(StrEnum):
    UNSUPPORTED_FORMAT = "unsupported_format"
    MALFORMED_FILE = "malformed_file"
    UNSUPPORTED_ACTIVITY_TYPE = "unsupported_activity_type"
    MISSING_REQUIRED_DATA = "missing_required_data"
    PROCESSING_LIMIT_EXCEEDED = "processing_limit_exceeded"


class ImportFailure(Exception):
    def __init__(self, code: ImportErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MetricAvailability(BaseModel):
    heart_rate: bool = False
    cadence: bool = False
    elevation: bool = False
    route: bool = False


class ActivitySample(BaseModel):
    timestamp: datetime
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    elevation_meters: float | None = None
    distance_meters: float | None = Field(default=None, ge=0)
    heart_rate_bpm: int | None = Field(default=None, gt=0)
    cadence_spm: int | None = Field(default=None, gt=0)


class ActivityLap(BaseModel):
    started_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)


class ParsedActivity(BaseModel):
    sport: str
    started_at: datetime | None = None
    duration_seconds: float | None = Field(default=None, ge=0)
    distance_meters: float | None = Field(default=None, ge=0)
    samples: list[ActivitySample] = Field(default_factory=list)
    laps: list[ActivityLap] = Field(default_factory=list)


class ParserProvenance(BaseModel):
    source_format: SourceFormat
    parser_name: str
    parser_version: str


class CompletedActivity(BaseModel):
    athlete_id: str
    checksum: str
    started_at: datetime
    duration_seconds: float = Field(gt=0)
    distance_meters: float = Field(ge=0)
    samples: list[ActivitySample]
    laps: list[ActivityLap]
    metrics: MetricAvailability
    provenance: ParserProvenance

    @model_validator(mode="after")
    def metric_flags_match_measurements(self) -> CompletedActivity:
        samples = self.samples
        if self.metrics.heart_rate != any(sample.heart_rate_bpm is not None for sample in samples):
            raise ValueError("heart-rate availability must match supplied samples")
        if self.metrics.cadence != any(sample.cadence_spm is not None for sample in samples):
            raise ValueError("cadence availability must match supplied samples")
        return self


class ImportResult(BaseModel):
    activity_id: str | None = None
    duplicate: bool = False
    error_code: ImportErrorCode | None = None
    message: str
