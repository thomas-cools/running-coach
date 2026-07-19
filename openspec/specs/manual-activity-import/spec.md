## Purpose

Define how athletes upload completed running activity files for normalization and later coaching analysis.

## Requirements

### Requirement: Supported completed-activity uploads
The system SHALL accept athlete-selected completed activity files in FIT, GPX, and TCX formats and SHALL identify the parser using the file's content as well as its declared type. The system SHALL accept only activities identified as running.

#### Scenario: Supported running file is uploaded
- **WHEN** an athlete uploads a valid FIT, GPX, or TCX file containing a completed running activity
- **THEN** the system begins validation and parsing using the matching format parser

#### Scenario: Unsupported file is uploaded
- **WHEN** an athlete uploads a file that is not a supported FIT, GPX, or TCX activity file
- **THEN** the system rejects the upload with an unsupported-format error and creates no activity

#### Scenario: Non-running activity is uploaded
- **WHEN** an athlete uploads a valid supported file containing an activity other than running
- **THEN** the system rejects the upload with an unsupported-activity-type error and creates no activity

### Requirement: Validated atomic import
The system SHALL validate file limits and completed-activity data before persisting an imported activity. The system SHALL create an analyzable activity only after parsing and normalization complete successfully.

#### Scenario: Malformed or incomplete activity file is uploaded
- **WHEN** an athlete uploads a malformed file or a file without the required completed-activity data
- **THEN** the system reports a validation error and creates no partial or analyzable activity

#### Scenario: Processing limit is exceeded
- **WHEN** an uploaded file exceeds configured resource or size limits during validation or parsing
- **THEN** the system stops processing, reports a processing-limit error, and creates no activity

### Requirement: Canonical completed-activity data
The system SHALL normalize every successfully imported activity into a source-independent completed-activity record containing source format, parser provenance, start time, duration, distance, and available lap, route, elevation, and sensor data. The system SHALL represent unavailable optional metrics as absent rather than as zero or inferred values.

#### Scenario: Rich activity data is normalized
- **WHEN** a valid imported running file includes GPS samples, laps, elevation, heart rate, or cadence
- **THEN** the completed-activity record contains the corresponding ordered samples, laps, summaries, and available metrics

#### Scenario: Optional metric is not supplied by the file
- **WHEN** a valid imported running file does not contain heart-rate data
- **THEN** the completed-activity record marks heart rate as unavailable and does not store it as a zero-value measurement

### Requirement: Idempotent manual imports
The system SHALL identify duplicate successful uploads for the same athlete by the original-file checksum and SHALL not create a second completed-activity record for the same file.

#### Scenario: Previously imported file is uploaded again
- **WHEN** an athlete uploads a file that matches a previously successful import for that athlete
- **THEN** the system returns the existing completed activity and does not create a duplicate

### Requirement: Actionable import outcomes
The system SHALL return an import outcome that distinguishes successful imports from unsupported formats, malformed files, unsupported activity types, missing required activity data, and processing-limit failures.

#### Scenario: Parsing fails
- **WHEN** parsing cannot complete for a supported-format upload
- **THEN** the system returns the applicable categorized error without exposing parser implementation details