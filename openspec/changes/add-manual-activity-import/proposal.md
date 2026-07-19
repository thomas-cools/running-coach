## Why

Athletes need a simple way to bring completed runs into the coach before account connections to Strava or Garmin are available. Accepting common workout-file formats establishes a dependable source of detailed activity data for analysis without coupling the first release to external-provider access.

## What Changes

- Add manual upload of completed running activity files in FIT, GPX, and TCX formats.
- Validate files and report unsupported, malformed, or non-running activity data without creating a partial activity.
- Normalize supported files into a source-independent completed-activity record for coaching analysis, including available summary, lap, route, and sensor data.
- Preserve source and parsing metadata so analysis can distinguish available metrics from metrics absent in the uploaded file.
- Explicitly defer Strava/Garmin account connections, automatic sync, planned-workout imports, and training-calendar features.

## Capabilities

### New Capabilities
- `manual-activity-import`: Accept, validate, parse, and normalize athlete-uploaded completed running activities for analysis.

### Modified Capabilities
- None.

## Impact

- Adds an upload and parsing boundary, a canonical completed-activity data model, and validation/error reporting.
- Establishes Python 3.14 with FastAPI/Pydantic for backend and domain code, and Supabase-managed PostgreSQL for normalized activity data.
- Requires FIT, GPX, and TCX parsing support plus storage decisions for uploaded files and normalized activity data.
- Provides the activity input contract for future coaching analysis; it does not require external provider APIs or calendar integrations.