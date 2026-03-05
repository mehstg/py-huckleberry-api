"""Bottle feeding tests for Huckleberry API."""

import asyncio
import time

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI


class TestBottleFeeding:
    """Test bottle feeding functionality."""

    async def _find_recent_bottle_interval(
        self,
        api: HuckleberryAPI,
        child_uid: str,
        *,
        created_after: float,
        bottle_type: str,
        amount: float,
        units: str,
    ) -> dict[str, object]:
        """Find the bottle interval written by the current test.

        Queries a small set of latest intervals and matches on timestamp and payload
        to avoid cross-test race conditions with other feed writes.
        """
        db = await api.get_firestore_client()
        intervals_ref = db.collection("feed").document(child_uid).collection("intervals")

        for _ in range(10):
            recent_intervals = intervals_ref.order_by("start", direction=firestore.Query.DESCENDING).limit(10)
            intervals_list = list(await recent_intervals.get())

            for interval_doc in intervals_list:
                interval_data = interval_doc.to_dict()
                if not interval_data:
                    continue

                if interval_data.get("mode") != "bottle":
                    continue

                start_value = interval_data.get("start")
                if not isinstance(start_value, (int, float)) or float(start_value) < created_after:
                    continue

                if (
                    interval_data.get("bottleType") == bottle_type
                    and interval_data.get("amount") == amount
                    and interval_data.get("units") == units
                ):
                    return interval_data

            await asyncio.sleep(0.5)

        raise AssertionError("No matching recent bottle interval found")

    async def test_log_bottle_feeding_formula(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging formula bottle feeding."""
        # Log formula bottle
        created_after = time.time()
        await api.log_bottle_feeding(child_uid, amount=120.0, bottle_type="Formula", units="ml")
        await asyncio.sleep(2)

        interval_data = await self._find_recent_bottle_interval(
            api,
            child_uid,
            created_after=created_after,
            bottle_type="Formula",
            amount=120.0,
            units="ml",
        )
        assert interval_data["mode"] == "bottle"
        assert interval_data["bottleType"] == "Formula"
        assert interval_data["amount"] == 120.0
        assert interval_data["units"] == "ml"
        assert "start" in interval_data
        assert "lastUpdated" in interval_data
        assert "offset" in interval_data

        # Check prefs.lastBottle updated
        db = await api.get_firestore_client()
        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        prefs = data.get("prefs", {})
        assert "lastBottle" in prefs
        assert prefs["lastBottle"]["mode"] == "bottle"
        assert prefs["lastBottle"]["bottleType"] == "Formula"
        assert prefs["lastBottle"]["bottleAmount"] == 120.0
        assert prefs["lastBottle"]["bottleUnits"] == "ml"

    async def test_log_bottle_feeding_breast_milk(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging breast milk bottle feeding."""
        # Log breast milk bottle
        created_after = time.time()
        await api.log_bottle_feeding(child_uid, amount=90.0, bottle_type="Breast Milk", units="ml")
        await asyncio.sleep(2)

        interval_data = await self._find_recent_bottle_interval(
            api,
            child_uid,
            created_after=created_after,
            bottle_type="Breast Milk",
            amount=90.0,
            units="ml",
        )
        assert interval_data["mode"] == "bottle"
        assert interval_data["bottleType"] == "Breast Milk"
        assert interval_data["amount"] == 90.0
        assert interval_data["units"] == "ml"

    async def test_log_bottle_feeding_ounces(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging bottle feeding with ounces."""
        # Log with oz units
        created_after = time.time()
        await api.log_bottle_feeding(child_uid, amount=4.0, bottle_type="Formula", units="oz")
        await asyncio.sleep(2)

        interval_data = await self._find_recent_bottle_interval(
            api,
            child_uid,
            created_after=created_after,
            bottle_type="Formula",
            amount=4.0,
            units="oz",
        )
        assert interval_data["units"] == "oz"
        assert interval_data["amount"] == 4.0

    async def test_log_bottle_feeding_cow_milk(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging cow milk bottle feeding."""
        # Log cow milk bottle
        created_after = time.time()
        await api.log_bottle_feeding(child_uid, amount=100.0, bottle_type="Cow Milk", units="ml")
        await asyncio.sleep(2)

        interval_data = await self._find_recent_bottle_interval(
            api,
            child_uid,
            created_after=created_after,
            bottle_type="Cow Milk",
            amount=100.0,
            units="ml",
        )
        assert interval_data["mode"] == "bottle"
        assert interval_data["bottleType"] == "Cow Milk"
        assert interval_data["amount"] == 100.0

    async def test_log_bottle_feeding_default_params(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging bottle feeding with default parameters."""
        # Log with defaults (Formula, ml)
        created_after = time.time()
        await api.log_bottle_feeding(child_uid, amount=150.0)
        await asyncio.sleep(2)

        interval_data = await self._find_recent_bottle_interval(
            api,
            child_uid,
            created_after=created_after,
            bottle_type="Formula",
            amount=150.0,
            units="ml",
        )
        assert interval_data["mode"] == "bottle"
        assert interval_data["bottleType"] == "Formula"  # Default
        assert interval_data["units"] == "ml"  # Default
        assert interval_data["amount"] == 150.0

    async def test_bottle_feeding_updates_prefs(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test that bottle feeding updates document-level preferences."""
        # Log bottle feeding
        await api.log_bottle_feeding(child_uid, amount=110.0, bottle_type="Breast Milk", units="oz")
        await asyncio.sleep(2)

        # Check document-level prefs updated
        db = await api.get_firestore_client()
        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        prefs = data.get("prefs", {})

        # Check document-level defaults
        assert prefs.get("bottleType") == "Breast Milk"
        assert prefs.get("bottleAmount") == 110.0
        assert prefs.get("bottleUnits") == "oz"

        # Check lastBottle
        assert "lastBottle" in prefs
        assert prefs["lastBottle"]["bottleType"] == "Breast Milk"
        assert prefs["lastBottle"]["bottleAmount"] == 110.0
        assert prefs["lastBottle"]["bottleUnits"] == "oz"
