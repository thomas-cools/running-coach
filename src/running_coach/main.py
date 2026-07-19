from fastapi import Depends, FastAPI, UploadFile, status
from sqlalchemy.orm import Session

from running_coach.auth import authenticate_athlete
from running_coach.config import Settings
from running_coach.database import create_session_factory, sessions
from running_coach.domain import ImportResult
from running_coach.services import ActivityImportService

app = FastAPI(title="Running Coach", version="0.1.0")
app.state.settings = Settings()
app.state.session_factory = create_session_factory(app.state.settings)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


def get_session() -> Session:
    yield from sessions(app.state.session_factory)


@app.post("/activities/import", response_model=ImportResult, status_code=status.HTTP_201_CREATED)
async def import_activity(
    file: UploadFile,
    athlete_id: str = Depends(authenticate_athlete),
    session: Session = Depends(get_session),
) -> ImportResult:
    content = await file.read(app.state.settings.max_upload_bytes + 1)
    result = await ActivityImportService(session, app.state.settings).import_upload(
        athlete_id, file.filename, content
    )
    if result.error_code is not None:
        return result
    return result
