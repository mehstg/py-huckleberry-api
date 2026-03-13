"""Pump feeding tests for Huckleberry API."""

import asyncio
import time

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI


class TestPumpFeeding:
    """Test pump feeding functionality."""

    async def _find_recent_pump_interval(
        self,
        api: HuckleberryAPI,
        child_uid: str,
        *,
        created_after: float,
        entry_mode: str,
        units: str,
        left_amount: float | None = None,
        right_amount: float | None = None,
        amount: float | None = None,
    ) -> dict[str, object]:
        """Find the pump interval written by the current test.

        Queries a small set of latest intervals and matches on timestamp and payload
        to avoid cross-test race conditions with other pump writes.
        """
        db = await api._get_firestore_client()
        intervals_ref = db.collection("pump").document(child_uid).collection("intervals")

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

                if interval_data.get("entryMode") != entry_mode:
                    continue

                if interval_data.get("units") != units:
                    continue

                # Match amounts based on entry mode
                if entry_mode == "leftright":
                    if left_amount is not None and interval_data.get("leftAmount") != left_amount:
                        continue
                    if right_amount is not None and interval_data.get("rightAmount") != right_amount:
                        continue
                elif entry_mode == "total":
                    # For total mode, the amount is stored in leftAmount (no separate 'amount' field)
                    if amount is not None and interval_data.get("leftAmount") != amount / 2.0:
                        continue

                return interval_data

            await asyncio.sleep(0.5)

        # Debug: print last 10 intervals for troubleshooting
        recent_intervals = intervals_ref.order_by("start", direction=firestore.Query.DESCENDING).limit(10)
        intervals_list = list(await recent_intervals.get())
        print(f"Recent intervals: {[doc.to_dict() for doc in intervals_list]}")
        raise AssertionError("No matching recent pump interval found")

    async def test_log_pump_total_ml(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging total pump mode with ml units."""
        created_after = time.time()
        await api.log_pump(
            child_uid,
            entry_mode="total",
            amount=120,
            units="ml",
            duration=1800.0,
            notes="Morning pumping session",
        )
        await asyncio.sleep(1)

        # Verify the interval was created
        interval = await self._find_recent_pump_interval(
            api,
            child_uid,
            created_after=created_after,
            entry_mode="total",
            units="ml",
            amount=120,
        )
        assert interval is not None
        assert interval["entryMode"] == "total"
        assert interval["leftAmount"] == 60
        assert interval["rightAmount"] == 60
        assert interval["units"] == "ml"
        assert interval["duration"] == 1800.0
        assert interval["notes"] == "Morning pumping session"

        # Verify prefs were updated
        db = await api._get_firestore_client()
        pump_doc = await db.collection("pump").document(child_uid).get()
        data = pump_doc.to_dict()
        assert data is not None
        assert "lastPump" in data.get("prefs", {})
        assert data["prefs"]["lastPump"]["entryMode"] == "total"
        assert data["prefs"]["lastPump"]["leftAmount"] == 60
        assert data["prefs"]["lastPump"]["rightAmount"] == 60

    async def test_log_pump_leftright_ml(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging left/right pump mode with ml units."""
        created_after = time.time()
        await api.log_pump(
            child_uid,
            entry_mode="leftright",
            left_amount=85.0,
            right_amount=95.0,
            units="ml",
            duration=2100.0,
        )
        await asyncio.sleep(1)

        interval = await self._find_recent_pump_interval(
            api,
            child_uid,
            created_after=created_after,
            entry_mode="leftright",
            units="ml",
            left_amount=85.0,
            right_amount=95.0,
        )
        assert interval is not None
        assert interval["entryMode"] == "leftright"
        assert interval["leftAmount"] == 85.0
        assert interval["rightAmount"] == 95.0

        # Verify prefs were updated
        db = await api._get_firestore_client()
        pump_doc = await db.collection("pump").document(child_uid).get()
        data = pump_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastPump"]["entryMode"] == "leftright"
        assert data["prefs"]["lastPump"]["leftAmount"] == 85.0
        assert data["prefs"]["lastPump"]["rightAmount"] == 95.0

    async def test_log_pump_ounces(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging pump with ounce units."""
        created_after = time.time()
        await api.log_pump(
            child_uid,
            entry_mode="total",
            amount=6.0,
            units="oz",
            duration=1500.0,
        )
        await asyncio.sleep(1)

        interval = await self._find_recent_pump_interval(
            api,
            child_uid,
            created_after=created_after,
            entry_mode="total",
            units="oz",
            amount=6.0,
        )
        assert interval is not None
        assert interval["units"] == "oz"
        assert interval["leftAmount"] == 3.0
        assert interval["rightAmount"] == 3.0

    async def test_log_pump_leftright_ounces(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging left/right pump mode with ounce units."""
        created_after = time.time()
        await api.log_pump(
            child_uid,
            entry_mode="leftright",
            left_amount=4.5,
            right_amount=4.8,
            units="oz",
        )
        await asyncio.sleep(1)

        interval = await self._find_recent_pump_interval(
            api,
            child_uid,
            created_after=created_after,
            entry_mode="leftright",
            units="oz",
            left_amount=4.5,
            right_amount=4.8,
        )
        assert interval is not None
        assert interval["entryMode"] == "leftright"
        assert interval["leftAmount"] == 4.5
        assert interval["rightAmount"] == 4.8

    async def test_list_pump_intervals(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test listing pump intervals within a date range."""
        from huckleberry_api.firebase_types import FirebasePumpIntervalData

        created_after = time.time()

        # Create some pump intervals
        for i in range(3):
            await api.log_pump(
                child_uid,
                entry_mode="total",
                amount=100.0 + i * 20,
                units="ml",
            )
            await asyncio.sleep(0.2)

        # Wait for intervals to be indexed
        await asyncio.sleep(1)

        # Get all intervals
        end_time = time.time()
        intervals = await api.list_pump_intervals(child_uid, created_after, end_time)
        assert len(intervals) >= 3

        # Verify interval data
        assert all(isinstance(interval, FirebasePumpIntervalData) for interval in intervals)
        assert all(interval.entryMode == "total" for interval in intervals)
        assert all(interval.units == "ml" for interval in intervals)
