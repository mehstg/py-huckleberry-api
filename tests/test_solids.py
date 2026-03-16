"""Solids feeding tests for Huckleberry API."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import cast

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import FirebaseSolidsFeedIntervalData
from huckleberry_api.models import SolidsFoodReference


class TestSolidsFeeding:
    """Test solid food feeding functionality."""

    async def _next_solids_start_time(self, api: HuckleberryAPI, child_uid: str) -> datetime:
        """Return a solids timestamp newer than the current latest summary."""
        db = await api._get_firestore_client()
        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict() or {}
        last_solid = ((data.get("prefs") or {}).get("lastSolid") or {}).get("start")
        minimum_start = time.time()
        if isinstance(last_solid, int | float):
            minimum_start = max(minimum_start, float(last_solid) + 60.0)
        return datetime.fromtimestamp(minimum_start, tz=timezone.utc).replace(microsecond=0)

    async def _find_recent_solids_interval(
        self,
        api: HuckleberryAPI,
        child_uid: str,
        *,
        start_timestamp: float,
        food_count: int,
        notes: str | None = None,
        reactions: dict[str, bool] | None = None,
    ) -> dict[str, object]:
        """Find the solids interval written by the current test."""
        db = await api._get_firestore_client()
        intervals_ref = db.collection("feed").document(child_uid).collection("intervals")

        for _ in range(10):
            intervals_list = list(
                await intervals_ref.where(filter=firestore.FieldFilter("start", "==", start_timestamp)).get()
            )

            for interval_doc in intervals_list:
                interval_data = interval_doc.to_dict()
                if not interval_data or interval_data.get("mode") != "solids":
                    continue

                foods = interval_data.get("foods")
                if not isinstance(foods, dict) or len(foods) != food_count:
                    continue
                if notes is not None and interval_data.get("notes") != notes:
                    continue
                if reactions is not None and interval_data.get("reactions") != reactions:
                    continue

                return interval_data

            await asyncio.sleep(0.5)

        raise AssertionError("No matching recent solids interval found")

    async def test_get_curated_foods(self, api: HuckleberryAPI) -> None:
        """Test fetching curated solids catalog."""
        curated = await api.list_solids_curated_foods()

        assert len(curated) > 0
        first = curated[0]
        assert first.id
        assert first.name
        assert first.source == "curated"

    async def test_create_and_get_custom_foods(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test creating custom food and reading list from Firestore."""
        unique_name = f"api-test-{int(time.time())}"
        created = await api.create_solids_custom_food(child_uid, unique_name)

        assert created.id
        assert created.name == unique_name
        assert created.source == "custom"

        custom_foods = await api.list_solids_custom_foods(child_uid)
        assert any(food.id == created.id for food in custom_foods)

    async def test_log_solids_single_curated_food(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging solids with an existing curated food ID."""
        curated = await api.list_solids_curated_foods()
        assert curated
        start_time = await self._next_solids_start_time(api, child_uid)

        await api.log_solids(
            child_uid,
            start_time=start_time,
            foods=[SolidsFoodReference(id=curated[0].id, source="curated", name=curated[0].name, amount="small")],
        )
        await asyncio.sleep(2)

        db = await api._get_firestore_client()
        data = await self._find_recent_solids_interval(
            api,
            child_uid,
            start_timestamp=start_time.timestamp(),
            food_count=1,
        )
        assert data is not None
        assert data["mode"] == "solids"
        assert "start" in data
        assert "lastUpdated" in data
        assert "offset" in data
        assert "foods" in data

        feed_doc = (await db.collection("feed").document(child_uid).get()).to_dict() or {}
        last_solid = (feed_doc.get("prefs") or {}).get("lastSolid") or {}
        assert last_solid.get("mode") == "solids"
        assert isinstance(last_solid.get("start"), (int, float))
        assert isinstance(last_solid.get("foods"), dict)

        # Check foods structure
        foods = data["foods"]
        assert isinstance(foods, dict)
        assert len(foods) == 1
        food_entry = cast(dict[str, object], next(iter(foods.values())))
        assert food_entry["source"] == "curated"
        assert isinstance(food_entry["created_name"], str)
        assert food_entry["created_name"]

    async def test_log_solids_multiple_foods_with_custom_and_curated(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging solids with mixed curated/custom foods, notes, and reaction."""
        custom_food = await api.create_solids_custom_food(child_uid, f"api-custom-{int(time.time())}")
        curated = await api.list_solids_curated_foods()
        assert len(curated) >= 2
        start_time = await self._next_solids_start_time(api, child_uid)

        await api.log_solids(
            child_uid,
            start_time=start_time,
            foods=[
                SolidsFoodReference(id=curated[0].id, source="curated", name=curated[0].name, amount="small"),
                SolidsFoodReference(id=curated[1].id, source="curated", name=curated[1].name, amount="medium"),
                SolidsFoodReference(id=custom_food.id, source="custom", name=custom_food.name, amount="small"),
            ],
            notes="First time trying broccoli",
            reaction="LOVED",
        )
        await asyncio.sleep(2)

        db = await api._get_firestore_client()
        data = await self._find_recent_solids_interval(
            api,
            child_uid,
            start_timestamp=start_time.timestamp(),
            food_count=3,
            notes="First time trying broccoli",
            reactions={"LOVED": True},
        )
        assert data is not None
        assert data["mode"] == "solids"
        foods = data["foods"]
        assert isinstance(foods, dict)
        assert len(foods) == 3
        assert data.get("notes") == "First time trying broccoli"
        assert data.get("reactions") == {"LOVED": True}

        feed_doc = (await db.collection("feed").document(child_uid).get()).to_dict() or {}
        last_solid = (feed_doc.get("prefs") or {}).get("lastSolid") or {}
        assert last_solid.get("mode") == "solids"
        assert last_solid.get("notes") == "First time trying broccoli"
        assert last_solid.get("reactions") == {"LOVED": True}
        assert isinstance(last_solid.get("foods"), dict)

    async def test_log_solids_with_explicit_start_time(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging solids with an explicit past timestamp."""
        curated = await api.list_solids_curated_foods()
        start_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)

        await api.log_solids(
            child_uid,
            start_time=start_time,
            foods=[SolidsFoodReference(id=curated[0].id, source="curated", name=curated[0].name, amount="small")],
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        intervals_ref = db.collection("feed").document(child_uid).collection("intervals")
        matching = list(
            await intervals_ref.where(filter=firestore.FieldFilter("start", "==", start_time.timestamp())).get()
        )
        solids_entries = [doc.to_dict() for doc in matching if (doc.to_dict() or {}).get("mode") == "solids"]

        assert solids_entries
        interval_data = solids_entries[0]
        assert interval_data is not None
        assert interval_data["start"] == start_time.timestamp()

    async def test_solids_entries_are_in_feed_intervals(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test retrieving solids entries via feed intervals."""
        curated = await api.list_solids_curated_foods()
        await api.log_solids(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            foods=[SolidsFoodReference(id=curated[0].id, source="curated", name=curated[0].name, amount="small")],
        )
        await asyncio.sleep(2)

        end_time = datetime.fromtimestamp(time.time() + 60, tz=timezone.utc)
        start_time = end_time - timedelta(minutes=5)

        entries = await api.list_feed_intervals(child_uid, start_time, end_time)
        solids_entries = [entry for entry in entries if isinstance(entry, FirebaseSolidsFeedIntervalData)]
        assert len(solids_entries) > 0
        assert solids_entries[-1].foods is not None

    async def test_solids_in_feed_interval_events(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test that solids entries appear in feed interval queries."""
        curated = await api.list_solids_curated_foods()
        await api.log_solids(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            foods=[SolidsFoodReference(id=curated[0].id, source="curated", name=curated[0].name, amount="small")],
        )
        await asyncio.sleep(2)

        end_time = datetime.fromtimestamp(time.time() + 60, tz=timezone.utc)
        start_time = end_time - timedelta(minutes=5)

        feed_entries = await api.list_feed_intervals(child_uid, start_time, end_time)
        assert any(entry.mode == "solids" for entry in feed_entries)
