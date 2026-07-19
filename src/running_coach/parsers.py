from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from io import BytesIO
from math import asin, cos, radians, sin, sqrt
from typing import Protocol
from xml.etree import ElementTree

import fitdecode
import gpxpy

from running_coach.domain import (
    ActivityLap,
    ActivitySample,
    ImportErrorCode,
    ImportFailure,
    ParsedActivity,
    SourceFormat,
)


def detect_format(content: bytes, filename: str | None = None) -> SourceFormat:
    """Determine the format from content and reject a declared-type mismatch."""
    detected: SourceFormat | None = None
    if len(content) >= 12 and content[8:12] == b".FIT":
        detected = SourceFormat.FIT
    elif content.lstrip().startswith(b"<"):
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise ImportFailure(
                ImportErrorCode.MALFORMED_FILE, "The XML activity file is malformed."
            ) from exc
        local_name = root.tag.rsplit("}", 1)[-1].lower()
        if local_name == "gpx":
            detected = SourceFormat.GPX
        elif local_name == "trainingcenterdatabase":
            detected = SourceFormat.TCX

    if detected is None:
        raise ImportFailure(
            ImportErrorCode.UNSUPPORTED_FORMAT, "Upload a FIT, GPX, or TCX activity file."
        )

    if filename and "." in filename:
        extension = filename.rsplit(".", 1)[-1].lower()
        declared = {"fit": SourceFormat.FIT, "gpx": SourceFormat.GPX, "tcx": SourceFormat.TCX}.get(
            extension
        )
        if declared is not None and declared != detected:
            raise ImportFailure(
                ImportErrorCode.MALFORMED_FILE, "The file extension does not match its content."
            )
    return detected


class ActivityParser(Protocol):
    source_format: SourceFormat
    name: str
    version: str

    def parse(self, content: bytes) -> ParsedActivity: ...


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return _as_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _child_text(node: ElementTree.Element, name: str) -> str | None:
    child = next((item for item in node.iter() if item.tag.rsplit("}", 1)[-1] == name), None)
    return child.text if child is not None else None


def _haversine_distance_meters(samples: Iterable[ActivitySample]) -> float:
    total = 0.0
    previous: ActivitySample | None = None
    for sample in samples:
        if previous and None not in (
            previous.latitude,
            previous.longitude,
            sample.latitude,
            sample.longitude,
        ):
            latitude_delta = radians(sample.latitude - previous.latitude)  # type: ignore[operator]
            longitude_delta = radians(sample.longitude - previous.longitude)  # type: ignore[operator]
            a = (
                sin(latitude_delta / 2) ** 2
                + cos(radians(previous.latitude))
                * cos(radians(sample.latitude))
                * sin(longitude_delta / 2) ** 2
            )
            total += 6_371_000 * 2 * asin(sqrt(a))
        previous = sample
    return total


def _sample_from_gpx(point: object) -> ActivitySample:
    extensions = getattr(point, "extensions", [])
    extension_values = {
        item.tag.rsplit("}", 1)[-1].lower(): item.text
        for item in extensions
        if item.text is not None
    }
    heart_rate = extension_values.get("hr")
    cadence = extension_values.get("cad")
    point_time = getattr(point, "time", None)
    if point_time is None:
        raise ImportFailure(
            ImportErrorCode.MISSING_REQUIRED_DATA, "The activity is missing sample timestamps."
        )
    return ActivitySample(
        timestamp=_as_utc(point_time),
        latitude=getattr(point, "latitude"),
        longitude=getattr(point, "longitude"),
        elevation_meters=getattr(point, "elevation", None),
        heart_rate_bpm=int(heart_rate) if heart_rate else None,
        cadence_spm=int(cadence) if cadence else None,
    )


class GpxParser:
    source_format = SourceFormat.GPX
    name = "gpxpy"
    version = getattr(gpxpy, "__version__", "unknown")

    def parse(self, content: bytes) -> ParsedActivity:
        try:
            document = gpxpy.parse(content.decode("utf-8"))
        except (UnicodeDecodeError, Exception) as exc:
            raise ImportFailure(
                ImportErrorCode.MALFORMED_FILE, "The GPX file cannot be parsed."
            ) from exc
        tracks = document.tracks
        sport = next((track.type for track in tracks if track.type), "").strip().lower()
        if sport != "running":
            raise ImportFailure(
                ImportErrorCode.UNSUPPORTED_ACTIVITY_TYPE,
                "The GPX activity is not identified as running.",
            )
        samples = [
            _sample_from_gpx(point)
            for track in tracks
            for segment in track.segments
            for point in segment.points
        ]
        if len(samples) < 2:
            raise ImportFailure(
                ImportErrorCode.MISSING_REQUIRED_DATA,
                "The GPX activity needs at least two timed samples.",
            )
        distance = _haversine_distance_meters(samples)
        return ParsedActivity(
            sport=sport,
            started_at=samples[0].timestamp,
            duration_seconds=(samples[-1].timestamp - samples[0].timestamp).total_seconds(),
            distance_meters=distance,
            samples=samples,
        )


class TcxParser:
    source_format = SourceFormat.TCX
    name = "xml.etree.ElementTree"
    version = "stdlib"

    def parse(self, content: bytes) -> ParsedActivity:
        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError as exc:
            raise ImportFailure(
                ImportErrorCode.MALFORMED_FILE, "The TCX file cannot be parsed."
            ) from exc
        activity = next(
            (node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "Activity"), None
        )
        if activity is None:
            raise ImportFailure(
                ImportErrorCode.MISSING_REQUIRED_DATA, "The TCX file contains no activity."
            )
        sport = activity.attrib.get("Sport", "").lower()
        if sport != "running":
            raise ImportFailure(
                ImportErrorCode.UNSUPPORTED_ACTIVITY_TYPE, "The TCX activity is not running."
            )
        samples: list[ActivitySample] = []
        laps: list[ActivityLap] = []
        for lap_node in (node for node in activity if node.tag.rsplit("}", 1)[-1] == "Lap"):
            laps.append(
                ActivityLap(
                    started_at=_parse_time(lap_node.attrib.get("StartTime")),
                    duration_seconds=float(_child_text(lap_node, "TotalTimeSeconds") or 0),
                    distance_meters=float(_child_text(lap_node, "DistanceMeters") or 0),
                )
            )
        for point in (
            node for node in activity.iter() if node.tag.rsplit("}", 1)[-1] == "Trackpoint"
        ):
            timestamp = _parse_time(_child_text(point, "Time"))
            if timestamp is None:
                continue
            position = next(
                (node for node in point if node.tag.rsplit("}", 1)[-1] == "Position"), None
            )
            samples.append(
                ActivitySample(
                    timestamp=timestamp,
                    latitude=float(_child_text(position, "LatitudeDegrees"))
                    if position is not None and _child_text(position, "LatitudeDegrees")
                    else None,
                    longitude=float(_child_text(position, "LongitudeDegrees"))
                    if position is not None and _child_text(position, "LongitudeDegrees")
                    else None,
                    elevation_meters=float(_child_text(point, "AltitudeMeters"))
                    if _child_text(point, "AltitudeMeters")
                    else None,
                    distance_meters=float(_child_text(point, "DistanceMeters"))
                    if _child_text(point, "DistanceMeters")
                    else None,
                    heart_rate_bpm=int(_child_text(point, "Value"))
                    if _child_text(point, "Value")
                    else None,
                    cadence_spm=int(_child_text(point, "Cadence"))
                    if _child_text(point, "Cadence")
                    else None,
                )
            )
        if len(samples) < 2:
            raise ImportFailure(
                ImportErrorCode.MISSING_REQUIRED_DATA,
                "The TCX activity needs at least two timed samples.",
            )
        return ParsedActivity(
            sport=sport,
            started_at=samples[0].timestamp,
            duration_seconds=(samples[-1].timestamp - samples[0].timestamp).total_seconds(),
            distance_meters=samples[-1].distance_meters or _haversine_distance_meters(samples),
            samples=samples,
            laps=laps,
        )


class FitParser:
    source_format = SourceFormat.FIT
    name = "fitdecode"
    version = getattr(fitdecode, "__version__", "unknown")

    def parse(self, content: bytes) -> ParsedActivity:
        samples: list[ActivitySample] = []
        laps: list[ActivityLap] = []
        session: dict[str, object] = {}
        try:
            with fitdecode.FitReader(BytesIO(content)) as reader:
                for frame in reader:
                    if not isinstance(frame, fitdecode.records.FitDataMessage):
                        continue
                    values = {field.name: field.value for field in frame.fields}
                    if frame.name == "record" and values.get("timestamp"):
                        samples.append(
                            ActivitySample(
                                timestamp=_as_utc(values["timestamp"]),
                                latitude=values.get("position_lat") / 11930464.71
                                if values.get("position_lat") is not None
                                else None,
                                longitude=values.get("position_long") / 11930464.71
                                if values.get("position_long") is not None
                                else None,
                                elevation_meters=values.get(
                                    "enhanced_altitude", values.get("altitude")
                                ),
                                distance_meters=values.get(
                                    "enhanced_distance", values.get("distance")
                                ),
                                heart_rate_bpm=values.get("heart_rate"),
                                cadence_spm=values.get("cadence"),
                            )
                        )
                    elif frame.name == "lap":
                        laps.append(
                            ActivityLap(
                                started_at=_as_utc(values["start_time"])
                                if values.get("start_time")
                                else None,
                                duration_seconds=values.get("total_elapsed_time"),
                                distance_meters=values.get("total_distance"),
                            )
                        )
                    elif frame.name == "session":
                        session = values
        except Exception as exc:
            raise ImportFailure(
                ImportErrorCode.MALFORMED_FILE, "The FIT file cannot be parsed."
            ) from exc
        sport = str(session.get("sport", "")).lower()
        if sport != "running":
            raise ImportFailure(
                ImportErrorCode.UNSUPPORTED_ACTIVITY_TYPE, "The FIT activity is not running."
            )
        if len(samples) < 2:
            raise ImportFailure(
                ImportErrorCode.MISSING_REQUIRED_DATA,
                "The FIT activity needs at least two timed samples.",
            )
        return ParsedActivity(
            sport=sport,
            started_at=_as_utc(session["start_time"])
            if session.get("start_time")
            else samples[0].timestamp,
            duration_seconds=session.get("total_elapsed_time")
            or (samples[-1].timestamp - samples[0].timestamp).total_seconds(),
            distance_meters=session.get("total_distance")
            or samples[-1].distance_meters
            or _haversine_distance_meters(samples),
            samples=samples,
            laps=laps,
        )


PARSERS: dict[SourceFormat, ActivityParser] = {
    SourceFormat.FIT: FitParser(),
    SourceFormat.GPX: GpxParser(),
    SourceFormat.TCX: TcxParser(),
}


def parse_activity(
    content: bytes, filename: str | None = None
) -> tuple[ParsedActivity, ActivityParser]:
    source_format = detect_format(content, filename)
    parser = PARSERS[source_format]
    return parser.parse(content), parser
