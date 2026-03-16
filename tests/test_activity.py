"""Activity tests for Huckleberry API."""

import asyncio
import time
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import FirebaseActivityDocumentData, FirebaseActivityIntervalData

_LAST_FIELD_BY_MODE = {
    "bath": "lastBath",
    "brushTeeth": "lastBrushTeeth",
    "indoorPlay": "lastIndoorPlay",
    "outdoorPlay": "lastOutdoorPlay",
    "screenTime": "lastScreenTime",
    "skinToSkin": "lastSkinToSkin",
    "storyTime": "lastStoryTime",
    "tummyTime": "lastTummyTime",
}


class TestActivity:
    """Test activity functionality."""

    async def _get_latest_activity_summary(self, api: HuckleberryAPI, child_uid: str, mode: str):
        """Read the latest per-mode activity summary directly from the root document."""
        db = await api._get_firestore_client()
        activity_doc = await db.collection("activities").document(child_uid).get()
        if not activity_doc.exists:
            return None

        activity_data = activity_doc.to_dict() or {}
        activity_model = FirebaseActivityDocumentData.model_validate(activity_data)
        if activity_model.prefs is None:
            return None

        return getattr(activity_model.prefs, _LAST_FIELD_BY_MODE[mode], None)

    async def _next_start_time(self, api: HuckleberryAPI, child_uid: str, mode: str) -> datetime:
        """Choose a start time that will become the latest summary for the selected mode."""
        minimum_start = time.time()
        latest_activity = await self._get_latest_activity_summary(api, child_uid, mode)
        if latest_activity is not None and latest_activity.start is not None:
            minimum_start = max(minimum_start, float(latest_activity.start) + 60.0)
        return datetime.fromtimestamp(minimum_start, tz=timezone.utc)

    async def _find_recent_activity_interval(
        self,
        api: HuckleberryAPI,
        child_uid: str,
        *,
        created_after: float,
        mode: str,
        duration: float | None = None,
        notes: str | None = None,
    ) -> dict[str, object]:
        """Find the activity interval written by the current test."""
        db = await api._get_firestore_client()
        intervals_ref = db.collection("activities").document(child_uid).collection("intervals")

        for _ in range(10):
            recent_intervals = intervals_ref.order_by("start", direction=firestore.Query.DESCENDING).limit(10)
            intervals_list = list(await recent_intervals.get())

            for interval_doc in intervals_list:
                interval_data = interval_doc.to_dict()
                if not interval_data:
                    continue

                start_value = interval_data.get("start")
                if not isinstance(start_value, (int, float)) or float(start_value) < created_after:
                    continue

                if interval_data.get("mode") != mode:
                    continue

                if duration is not None and interval_data.get("duration") != duration:
                    continue

                if notes is not None and interval_data.get("notes") != notes:
                    continue

                return interval_data

            await asyncio.sleep(0.5)

        raise AssertionError("No matching recent activity interval found")

    async def test_log_activity_updates_history_and_latest_summary(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging an activity interval and updating the matching latest summary."""
        created_after = time.time()
        await api.log_activity(
            child_uid,
            mode="bath",
            start_time=await self._next_start_time(api, child_uid, "bath"),
            duration=900,
            notes="integration activity test",
        )
        await asyncio.sleep(1)

        interval = await self._find_recent_activity_interval(
            api,
            child_uid,
            created_after=created_after,
            mode="bath",
            duration=900.0,
            notes="integration activity test",
        )
        assert interval["mode"] == "bath"
        assert interval["duration"] == 900.0
        assert interval["notes"] == "integration activity test"

        latest = await self._get_latest_activity_summary(api, child_uid, "bath")
        assert latest is not None
        assert latest.duration == 900.0
        assert latest.end_offset is not None

    async def test_list_activity_intervals(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test listing activity intervals within a date range."""
        created_after = time.time()
        now = datetime.now(timezone.utc)
        first_note = f"activity-list-{int(created_after)}-1"
        second_note = f"activity-list-{int(created_after)}-2"

        await api.log_activity(
            child_uid,
            mode="storyTime",
            start_time=now,
            duration=300,
            notes=first_note,
        )
        await asyncio.sleep(0.5)
        await api.log_activity(
            child_uid,
            mode="brushTeeth",
            start_time=now + timedelta(minutes=2),
            duration=180,
            notes=second_note,
        )
        await asyncio.sleep(1)

        intervals = await api.list_activity_intervals(
            child_uid,
            datetime.fromtimestamp(created_after, tz=timezone.utc),
            datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc),
        )
        created_intervals = [
            interval
            for interval in intervals
            if float(interval.start) >= created_after and interval.notes in {first_note, second_note}
        ]

        assert len(created_intervals) >= 2
        assert all(isinstance(interval, FirebaseActivityIntervalData) for interval in created_intervals)

    async def test_log_older_activity_does_not_replace_latest_summary(
        self, api: HuckleberryAPI, child_uid: str
    ) -> None:
        """Test that backfilled activity entries do not replace the latest per-mode summary."""
        recent_start = await self._next_start_time(api, child_uid, "storyTime")
        older_start = recent_start - timedelta(hours=3)

        await api.log_activity(
            child_uid,
            mode="storyTime",
            start_time=recent_start,
            duration=420,
            notes="recent activity entry",
        )
        await asyncio.sleep(1)

        latest_after_recent = await self._get_latest_activity_summary(api, child_uid, "storyTime")
        assert latest_after_recent is not None
        assert latest_after_recent.start is not None
        assert abs(float(latest_after_recent.start) - recent_start.timestamp()) < 2.0

        await api.log_activity(
            child_uid,
            mode="storyTime",
            start_time=older_start,
            duration=120,
            notes="older activity entry",
        )
        await asyncio.sleep(1)

        latest_after_older = await self._get_latest_activity_summary(api, child_uid, "storyTime")
        assert latest_after_older is not None
        assert latest_after_older.start is not None
        assert abs(float(latest_after_older.start) - recent_start.timestamp()) < 2.0
        assert latest_after_older.duration == 420.0
