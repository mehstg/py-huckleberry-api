"""Real-time listener tests for Huckleberry API."""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from huckleberry_api import HuckleberryAPI
from huckleberry_api.firebase_types import FirebasePumpDocumentData
from huckleberry_api.models import SolidsFoodReference


class TestRealtimeListeners:
    """Test real-time listener functionality."""

    async def test_sleep_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test sleep real-time listener."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_sleep_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.start_sleep(child_uid)
        await asyncio.sleep(2)

        await api.cancel_sleep(child_uid)
        await api.stop_all_listeners()

        assert len(updates) > 0
        assert updates[-1].timer is not None
        assert updates[-1].timer.active is True

    async def test_feed_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test feeding real-time listener."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_feed_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(2)

        await api.cancel_nursing(child_uid)
        await api.stop_all_listeners()

        assert len(updates) > 0
        assert updates[-1].timer is not None
        assert updates[-1].timer.active is True

    async def test_feed_listener_emits_nursing_and_solids_updates(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test feed listener emissions across nursing and solids updates."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        curated = await api.list_solids_curated_foods()
        assert curated

        await api.setup_feed_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(2)
        await api.complete_nursing(child_uid)
        await asyncio.sleep(2)

        await api.log_solids(
            child_uid,
            foods=[
                SolidsFoodReference(
                    id=curated[0].id,
                    source="curated",
                    name=curated[0].name,
                    amount="small",
                )
            ],
        )
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0

        saw_active_nursing = False
        saw_last_nursing = False
        saw_last_solid = False

        emitted_summary: list[dict[str, Any]] = []
        for update in updates:
            timer = getattr(update, "timer", None)
            prefs = getattr(update, "prefs", None)

            timer_active = bool(getattr(timer, "active", False)) if timer is not None else False
            active_side = getattr(timer, "activeSide", None) if timer is not None else None
            has_last_nursing = bool(getattr(prefs, "lastNursing", None)) if prefs is not None else False
            has_last_solid = bool(getattr(prefs, "lastSolid", None)) if prefs is not None else False

            saw_active_nursing = saw_active_nursing or timer_active
            saw_last_nursing = saw_last_nursing or has_last_nursing
            saw_last_solid = saw_last_solid or has_last_solid

            emitted_summary.append(
                {
                    "timer_active": timer_active,
                    "active_side": active_side,
                    "has_last_nursing": has_last_nursing,
                    "has_last_solid": has_last_solid,
                }
            )

        print("Feed listener emitted updates:")
        for index, summary in enumerate(emitted_summary, start=1):
            print(f"  [{index}] {summary}")

        assert saw_active_nursing
        assert saw_last_nursing
        assert saw_last_solid

    async def test_listener_survives_token_refresh(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test that listeners survive token refresh."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_sleep_listener(child_uid, callback)
        await asyncio.sleep(2)

        initial_count = len(updates)

        await api.refresh_session_token()
        await asyncio.sleep(2)

        await api.start_sleep(child_uid)
        await asyncio.sleep(2)

        await api.cancel_sleep(child_uid)
        await api.stop_all_listeners()

        assert len(updates) > initial_count

    async def test_health_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test health/growth real-time listener."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_health_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.log_growth(child_uid, weight=5.5, units="metric")
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0
        last_update = updates[-1]
        assert last_update.prefs is not None
        assert last_update.prefs.lastGrowthEntry is not None

    async def test_health_listener_imperial_growth(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test health listener emits imperial growth updates."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_health_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.log_growth(child_uid, weight=11.5, head=13.8, units="imperial")
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0

        growth_updates = [
            update.prefs.lastGrowthEntry
            for update in updates
            if getattr(update, "prefs", None) is not None and getattr(update.prefs, "lastGrowthEntry", None) is not None
        ]

        assert growth_updates
        last_growth = growth_updates[-1]
        assert last_growth.id_ is not None
        assert last_growth.weight == 11.5
        assert last_growth.weightUnits == "lbs.oz"
        assert last_growth.height is None
        assert last_growth.heightUnits is None
        assert last_growth.head == 13.8
        assert last_growth.headUnits == "hin"

    async def test_diaper_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test diaper real-time listener."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_diaper_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.log_diaper(child_uid, mode="pee")
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0
        last_update = updates[-1]
        assert last_update.prefs is not None
        assert last_update.prefs.lastDiaper is not None

    async def test_diaper_listener_emits_potty_updates(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test diaper listener also emits potty updates from the shared document."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_diaper_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.log_potty(child_uid, mode="pee", how_it_happened="accident", pee_amount="little")
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0
        last_update = updates[-1]
        assert last_update.prefs is not None
        assert last_update.prefs.lastPotty is not None
        assert last_update.prefs.lastPotty.mode == "pee"

    async def test_pump_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test pump real-time listener."""
        updates: list[Any] = []
        minimum_start = time.time()
        db = await api._get_firestore_client()
        pump_doc = await db.collection("pump").document(child_uid).get()
        pump_data = pump_doc.to_dict() or {}
        pump_model = FirebasePumpDocumentData.model_validate(pump_data)
        latest_pump = pump_model.prefs.lastPump if pump_model.prefs else None
        if latest_pump is not None and latest_pump.start is not None:
            minimum_start = max(minimum_start, float(latest_pump.start) + 60.0)

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_pump_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.log_pump(
            child_uid,
            start_time=datetime.fromtimestamp(minimum_start, tz=timezone.utc),
            total_amount=25.0,
            duration=900,
            notes="listener test",
        )
        await asyncio.sleep(2)

        await api.stop_all_listeners()

        assert len(updates) > 0
        last_update = updates[-1]
        assert last_update.prefs is not None
        assert last_update.prefs.lastPump is not None
        assert last_update.prefs.lastPump.duration == 900.0
        assert last_update.prefs.lastPump.entryMode == "total"
