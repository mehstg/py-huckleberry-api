"""Solids feeding tests for Huckleberry API."""
import time

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI


class TestSolidsFeeding:
    """Test solid food feeding functionality."""

    def test_log_solids_single_food(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging solids with a single food item."""
        api.log_solids(child_uid, foods=["banana"])
        time.sleep(2)

        intervals_ref = (
            api._get_firestore_client()
            .collection("feed")
            .document(child_uid)
            .collection("intervals")
        )

        recent_intervals = (
            intervals_ref
            .order_by("start", direction=firestore.Query.DESCENDING)
            .limit(1)
            .get()
        )

        intervals_list = list(recent_intervals)
        assert len(intervals_list) > 0

        data = intervals_list[0].to_dict()
        assert data is not None
        assert data["mode"] == "solids"
        assert "start" in data
        assert "lastUpdated" in data
        assert "offset" in data
        assert "foods" in data

        # Check foods structure
        foods = data["foods"]
        assert len(foods) == 1
        food_entry = next(iter(foods.values()))
        assert food_entry["source"] == "custom"
        assert food_entry["created_name"] == "banana"

    def test_log_solids_multiple_foods_with_notes_and_reaction(
        self, api: HuckleberryAPI, child_uid: str
    ) -> None:
        """Test logging solids with multiple foods, notes, and reaction."""
        api.log_solids(
            child_uid,
            foods=["broccoli", "rice", "potato"],
            notes="First time trying broccoli",
            reaction="LOVED",
        )
        time.sleep(2)

        intervals_ref = (
            api._get_firestore_client()
            .collection("feed")
            .document(child_uid)
            .collection("intervals")
        )

        recent_intervals = (
            intervals_ref
            .order_by("start", direction=firestore.Query.DESCENDING)
            .limit(1)
            .get()
        )

        intervals_list = list(recent_intervals)
        assert len(intervals_list) > 0

        data = intervals_list[0].to_dict()
        assert data is not None
        assert data["mode"] == "solids"
        assert len(data["foods"]) == 3
        assert data.get("notes") == "First time trying broccoli"
        assert data.get("reactions") == {"LOVED": True}

        # Check all food names are present
        food_names = {v["created_name"] for v in data["foods"].values()}
        assert food_names == {"broccoli", "rice", "potato"}

    def test_get_solids_intervals(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test retrieving solids intervals."""
        # Log a solids entry
        api.log_solids(child_uid, foods=["oatmeal"])
        time.sleep(2)

        end_ts = int(time.time()) + 60
        start_ts = end_ts - 300

        entries = api.get_solids_intervals(child_uid, start_ts, end_ts)
        assert len(entries) > 0
        assert entries[-1]["mode"] == "solids"
        assert "foods" in entries[-1]

    def test_solids_in_calendar_events(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test that solids entries appear in calendar events."""
        # Log a solids entry
        api.log_solids(child_uid, foods=["apple"])
        time.sleep(2)

        end_ts = int(time.time()) + 60
        start_ts = end_ts - 300

        cal = api.get_calendar_events(child_uid, start_ts, end_ts)
        assert "solids" in cal
        assert len(cal["solids"]) > 0
