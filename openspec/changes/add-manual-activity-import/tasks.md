## 1. Import foundations

- [x] 1.1 Bootstrap a Python 3.14 FastAPI project with Pydantic domain models, dependency locking, and CI/runtime checks that enforce Python 3.14.
- [x] 1.2 Select maintained FIT, GPX, and TCX parsing libraries compatible with Python 3.14 and record their licensing and supported data fields.
- [x] 1.3 Define the canonical completed-activity, lap, sample, metric-availability, provenance, and categorized import-outcome models.
- [ ] 1.4 Provision Supabase PostgreSQL and define Alembic-compatible migrations for normalized activities, athlete ownership, checksum-based deduplication, parser version, and import status.
- [x] 1.5 Establish configuration for upload size, sample-count, activity-duration, memory, and processing-time limits.

## 2. Parsing and normalization

- [x] 2.1 Implement a parser-adapter interface and content-aware FIT, GPX, and TCX format detection.
- [x] 2.2 Implement FIT parsing into the format-neutral intermediate result, including available laps, route samples, elevation, heart rate, and cadence.
- [x] 2.3 Implement GPX and TCX parsing into the same intermediate result, preserving optional-field absence.
- [x] 2.4 Implement running-activity validation and canonical normalization without zero-filling or inferring unavailable metrics.

## 3. Manual import workflow

- [x] 3.1 Implement the authenticated athlete upload entry point with file type and configured resource-limit enforcement.
- [x] 3.2 Orchestrate validation, parsing, normalization, and persistence as an atomic import that exposes no partial activity on failure.
- [x] 3.3 Implement athlete-scoped checksum deduplication that returns the existing successful activity for a repeated upload.
- [x] 3.4 Map internal parsing failures to the specified actionable import outcomes without exposing implementation details.
- [x] 3.5 Decide and implement the original-file retention, access-control, and encryption policy before durable raw-upload storage is enabled.

## 4. Verification and operations

- [ ] 4.1 Add representative FIT, GPX, and TCX fixtures covering successful runs, optional metrics, unsupported sport, malformed content, and duplicate files.
- [x] 4.2 Add unit and integration tests for detection, parser adapters, normalization, validation, atomic persistence, and categorized errors.
- [x] 4.3 Add tests proving unavailable metrics remain absent and no partial activity is visible after every failure path.
- [x] 4.4 Add telemetry for import outcomes, source format, parser version, durations, and limit failures without logging sensitive route or health data.