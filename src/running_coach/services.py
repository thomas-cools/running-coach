import asyncio
import hashlib
import logging

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from running_coach.config import Settings
from running_coach.database import ActivityRecord, activity_record
from running_coach.domain import ImportFailure, ImportResult
from running_coach.normalization import normalize_activity
from running_coach.parsers import parse_activity

logger = logging.getLogger(__name__)


class ActivityImportService:
    def __init__(self, session: Session, settings: Settings) -> None:
        self.session = session
        self.settings = settings

    async def import_upload(
        self, athlete_id: str, filename: str | None, content: bytes
    ) -> ImportResult:
        if len(content) > self.settings.max_upload_bytes:
            result = ImportResult(
                error_code="processing_limit_exceeded", message="The file exceeds the upload limit."
            )
            self._log_outcome(result)
            return result
        checksum = hashlib.sha256(content).hexdigest()
        existing = self.session.scalar(
            select(ActivityRecord).where(
                ActivityRecord.athlete_id == athlete_id, ActivityRecord.checksum == checksum
            )
        )
        if existing:
            return ImportResult(
                activity_id=existing.id,
                duplicate=True,
                message="This activity was already imported.",
            )
        try:
            async with asyncio.timeout(self.settings.parse_timeout_seconds):
                parsed, parser = await asyncio.to_thread(parse_activity, content, filename)
                activity = normalize_activity(parsed, parser, athlete_id, checksum, self.settings)
        except TimeoutError:
            result = ImportResult(
                error_code="processing_limit_exceeded", message="The file took too long to process."
            )
            self._log_outcome(result)
            return result
        except ImportFailure as exc:
            result = ImportResult(error_code=exc.code, message=exc.message)
            self._log_outcome(result)
            return result

        record = activity_record(activity)
        try:
            self.session.add(record)
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self.session.scalar(
                select(ActivityRecord).where(
                    ActivityRecord.athlete_id == athlete_id, ActivityRecord.checksum == checksum
                )
            )
            if existing:
                result = ImportResult(
                    activity_id=existing.id,
                    duplicate=True,
                    message="This activity was already imported.",
                )
                self._log_outcome(result)
                return result
            raise
        result = ImportResult(activity_id=record.id, message="Activity imported.")
        self._log_outcome(
            result, activity.provenance.source_format.value, activity.provenance.parser_name
        )
        return result

    @staticmethod
    def _log_outcome(
        result: ImportResult, source_format: str | None = None, parser_name: str | None = None
    ) -> None:
        logger.info(
            "activity_import outcome=%s duplicate=%s source_format=%s parser=%s",
            result.error_code.value if result.error_code else "success",
            result.duplicate,
            source_format,
            parser_name,
        )
