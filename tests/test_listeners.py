"""Real-time listener tests for Huckleberry API."""

import asyncio
from typing import Any

from huckleberry_api import HuckleberryAPI
from huckleberry_api.models import SolidsFoodReference


class TestRealtimeListeners:
    """Test real-time listener functionality."""

    async def test_sleep_listener(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test sleep real-time listener."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        await api.setup_realtime_listener(child_uid, callback)
        await asyncio.sleep(2)

        await api.start_sleep(child_uid)
        await asyncio.sleep(2)

        await api.cancel_sleep(child_uid)
        await api.stop_all_listeners()

        assert len(updates) > 0
        assert updates[-1]["timer"]["active"] is True

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
        assert updates[-1]["timer"]["active"] is True

    async def test_feed_listener_emits_nursing_and_solids_updates(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test feed listener emissions across nursing and solids updates."""
        updates: list[Any] = []

        def callback(data: Any) -> None:
            updates.append(data)

        curated = await api.get_solids_curated_list()
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
            timer = update.get("timer") if isinstance(update, dict) else None
            prefs = update.get("prefs") if isinstance(update, dict) else None

            timer_active = bool(timer.get("active")) if isinstance(timer, dict) else False
            active_side = timer.get("activeSide") if isinstance(timer, dict) else None
            has_last_nursing = isinstance(prefs, dict) and isinstance(prefs.get("lastNursing"), dict)
            has_last_solid = isinstance(prefs, dict) and isinstance(prefs.get("lastSolid"), dict)

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

        await api.setup_realtime_listener(child_uid, callback)
        await asyncio.sleep(2)

        initial_count = len(updates)

        await api.refresh_auth_token()
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
        assert "prefs" in last_update
        assert "lastGrowthEntry" in last_update.get("prefs", {})

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
        assert "prefs" in last_update
        assert "lastDiaper" in last_update.get("prefs", {})
