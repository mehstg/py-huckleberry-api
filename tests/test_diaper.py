"""Diaper tracking tests for Huckleberry API."""

import asyncio
from datetime import datetime, timedelta, timezone

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI


class TestDiaperTracking:
    """Test diaper tracking functionality."""

    async def test_log_diaper_pee(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging pee-only diaper change."""
        await api.log_diaper(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            mode="pee",
            pee_amount="medium",
        )
        await asyncio.sleep(1)

        # Verify it was logged
        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert "lastDiaper" in data.get("prefs", {})
        assert data["prefs"]["lastDiaper"]["mode"] == "pee"

    async def test_log_diaper_poo(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging poo-only diaper change."""
        await api.log_diaper(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            mode="poo",
            poo_amount="big",
            color="yellow",
            consistency="solid",
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "poo"

    async def test_log_diaper_both(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging both pee and poo."""
        await api.log_diaper(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            mode="both",
            pee_amount="medium",
            poo_amount="medium",
            color="green",
            consistency="runny",
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "both"

    async def test_log_diaper_dry(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging dry diaper check."""
        await api.log_diaper(child_uid, start_time=datetime.now(timezone.utc).replace(microsecond=0), mode="dry")
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "dry"

    async def test_log_potty(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging a potty event into the shared diaper tracker."""
        await api.log_potty(
            child_uid,
            start_time=datetime.now(timezone.utc).replace(microsecond=0),
            mode="poo",
            how_it_happened="wentPotty",
            poo_amount="medium",
            color="brown",
            consistency="solid",
            notes="Morning potty success",
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_ref = db.collection("diaper").document(child_uid)
        diaper_doc = await diaper_ref.get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastPotty"]["mode"] == "poo"

        intervals = diaper_ref.collection("intervals").order_by("start", direction="DESCENDING").limit(1).stream()
        docs = [doc async for doc in intervals]
        assert docs
        latest = docs[0].to_dict()
        assert latest is not None
        assert latest["isPotty"] is True
        assert latest["howItHappened"] == "wentPotty"

    async def test_log_diaper_with_explicit_start_time(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging a diaper change with an explicit past timestamp."""
        start_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=2)

        await api.log_diaper(child_uid, start_time=start_time, mode="pee", pee_amount="little")
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        intervals_ref = db.collection("diaper").document(child_uid).collection("intervals")
        matching = list(
            await intervals_ref.where(filter=firestore.FieldFilter("start", "==", start_time.timestamp())).get()
        )

        assert matching
        interval_data = matching[0].to_dict()
        assert interval_data is not None
        assert interval_data["start"] == start_time.timestamp()
        assert interval_data["mode"] == "pee"

    async def test_log_potty_with_explicit_start_time(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging a potty event with an explicit past timestamp."""
        start_time = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(hours=3)

        await api.log_potty(
            child_uid,
            start_time=start_time,
            mode="pee",
            how_it_happened="accident",
            pee_amount="little",
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        intervals_ref = db.collection("diaper").document(child_uid).collection("intervals")
        matching = list(
            await intervals_ref.where(filter=firestore.FieldFilter("start", "==", start_time.timestamp())).get()
        )
        potty_entries = [doc.to_dict() for doc in matching if (doc.to_dict() or {}).get("isPotty") is True]

        assert potty_entries
        interval_data = potty_entries[0]
        assert interval_data is not None
        assert interval_data["howItHappened"] == "accident"
