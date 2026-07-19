## Context

The product needs completed activity data before it can provide personalized coaching analysis. Strava and Garmin account integrations require external access, provider-specific lifecycle handling, and potentially partnership agreements, so the first ingestion path is athlete-selected file upload. FIT, GPX, and TCX encode overlapping running data with materially different structures and optional fields.

The backend and domain runtime is Python 3.14, using FastAPI and Pydantic. Normalized activity data will be stored in Supabase-managed PostgreSQL; the Python service will access it with server-side credentials and Alembic-compatible migrations. This decision does not assume Supabase Auth, browser-direct database access, or raw-file storage in Supabase Storage.

## Goals / Non-Goals

**Goals:**
- Accept completed running activities supplied as FIT, GPX, or TCX files.
- Produce one source-independent activity representation that downstream analysis can consume without format-specific branching.
- Preserve field availability and parser provenance so missing source data is not interpreted as zero or inferred data.
- Prevent invalid or partially parsed uploads from becoming analyzable activities.

**Non-Goals:**
- Strava or Garmin OAuth connections, provider synchronization, or webhooks.
- Importing planned workouts, training plans, or calendar events.
- Creating coaching recommendations, editing activities, or supporting sports other than running.
- Guaranteeing that every source format supplies every optional sensor metric.

## Decisions

### Use Python 3.14 for backend and domain code

The service will target Python 3.14 with FastAPI for HTTP boundaries and Pydantic for validated domain models. Python provides the strongest fit for activity parsing, time-series and scientific analysis, and future LLM or machine-learning integration.

Python 3.12 was considered as a more widely installed baseline but was rejected to keep the project current. Development containers, CI, and production images must explicitly provision Python 3.14; the current container's Python version is not the project-runtime contract.

### Use Supabase-managed PostgreSQL for normalized data

The canonical activity records, imports, ownership relations, checksums, and parser provenance will reside in a Supabase PostgreSQL project. The Python backend will use a server-side database connection and migrations, retaining a conventional relational data model while Supabase manages PostgreSQL operations.

Using a self-managed database was rejected because it adds operational work without helping the initial product capability. Supabase Auth, its client SDK, browser-direct access, and object storage are deferred decisions; they must not shape the import domain model until authentication and raw-file retention requirements are defined.

### Isolate source formats behind parser adapters

The upload service will select a FIT, GPX, or TCX parser after inspecting both file type and content signature, then ask the parser to produce a format-neutral intermediate result. A normalizer will convert that result to the canonical completed-activity model.

This keeps coaching analysis independent of source syntax and lets future provider APIs reuse the normalizer. Selecting parsers by filename extension alone was rejected because extensions are easily incorrect or spoofed.

### Persist a canonical completed-activity record

Each successful import will create one activity record with: ownership, source format, parser/version provenance, original-file checksum, start and end timestamps, sport, duration, distance, elevation summary, ordered location/sensor samples, laps, and explicit availability for optional metrics such as heart rate and cadence. Unavailable fields will remain absent rather than being stored as zero values.

Storing only raw files was rejected because it would leave every analysis workflow coupled to source parsers. The raw upload retention policy is intentionally left separate from the normalized record: it must be defined with privacy and storage requirements before implementation chooses durable raw-file storage.

### Validate and normalize atomically

The import pipeline is: accept upload, enforce size/type limits, inspect the content, parse, validate a completed running activity, normalize, deduplicate by athlete and file checksum, then persist the normalized activity. No activity record is visible to analysis until all preceding stages succeed.

Partial persistence was rejected because it makes a failed upload indistinguishable from a completed activity with sparse data. A duplicate upload will return the prior successfully imported activity rather than create another one.

### Make resource and error handling explicit

Parsing will occur with bounded input size, processing time, and memory use. Failures are categorized as unsupported format, malformed file, unsupported activity type, missing required activity data, or processing limit exceeded. User-facing responses will be actionable without exposing parser internals.

## Risks / Trade-offs

- [Large or adversarial files consume parser resources] -> Enforce upload-size, time, and memory limits; parse outside request-critical resources where needed.
- [FIT parser support varies by language/runtime] -> Select a maintained FIT library during implementation and validate it with representative device exports.
- [Python 3.14 adoption may precede library support] -> Verify every dependency and deployment image against Python 3.14 before implementation; pin compatible versions and select replacements where necessary.
- [Supabase configuration or credentials are exposed] -> Use server-side secrets only, least-privilege database roles, and migration automation that does not expose production credentials.
- [Source data quality differs] -> Retain provenance and optional-field availability; coaching analysis must distinguish absent metrics from measured values.
- [Duplicate activity uploads] -> Use athlete-scoped checksums and return the existing import idempotently.
- [Location and health data is sensitive] -> Define authorization, encryption, and retention rules before persisting raw uploads or exposing route data.

## Migration Plan

1. Introduce the canonical completed-activity schema and import status/error model.
2. Implement the parser adapter contract and supported FIT, GPX, and TCX adapters.
3. Release upload and normalization behind the activity-analysis boundary with validation limits and observability.
4. Add representative real-world fixtures and expand provider integrations later by mapping their payloads through the same normalizer.

Rollback consists of disabling new uploads while preserving successfully normalized activities for existing analysis. Parser-specific changes are versioned in import provenance to enable targeted reprocessing when required.

## Open Questions

- What maximum file size, activity duration, sample count, and parsing time are appropriate for the initial deployment?
- What identity and authorization model will associate an upload with an athlete?
- How long, if at all, should original uploaded files be retained after successful normalization?
- Which canonical fields are the minimum input contract for the first coaching-analysis feature?