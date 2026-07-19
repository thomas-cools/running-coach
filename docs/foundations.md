# Foundations

## Runtime and service boundary

The backend targets Python 3.14, FastAPI, and Pydantic. `uv.lock` is the resolved dependency lock and CI uses CPython 3.14.6. The application uses Supabase-managed PostgreSQL through a server-side SQLAlchemy connection and Alembic migrations. Browser-direct database access and Supabase Storage are not enabled by this change.

## Activity format libraries

| Format | Library | License | Data used |
| --- | --- | --- | --- |
| FIT | `fitdecode` | MIT | Session sport, timestamps, GPS, distance, elevation, heart rate, cadence, laps |
| GPX | `gpxpy` | Apache-2.0 | Track type, timestamps, GPS, elevation, heart rate and cadence extensions |
| TCX | Python `xml.etree.ElementTree` | PSF | Activity sport, timestamps, GPS, distance, elevation, heart rate, cadence, laps |

Original upload bytes are processed in memory and are not retained durably. Supabase project secrets belong only in server-side deployment configuration. The database role must be least-privilege and encrypted transport is required.