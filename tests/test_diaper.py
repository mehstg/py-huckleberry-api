"""Diaper tracking tests for Huckleberry API."""

import asyncio

from huckleberry_api import HuckleberryAPI


class TestDiaperTracking:
    """Test diaper tracking functionality."""

    async def test_log_diaper_pee(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging pee-only diaper change."""
        await api.log_diaper(child_uid, mode="pee", pee_amount="medium")
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
        await api.log_diaper(child_uid, mode="poo", poo_amount="big", color="yellow", consistency="solid")
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "poo"

    async def test_log_diaper_both(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging both pee and poo."""
        await api.log_diaper(
            child_uid, mode="both", pee_amount="medium", poo_amount="medium", color="green", consistency="runny"
        )
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "both"

    async def test_log_diaper_dry(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging dry diaper check."""
        await api.log_diaper(child_uid, mode="dry")
        await asyncio.sleep(1)

        db = await api._get_firestore_client()
        diaper_doc = await db.collection("diaper").document(child_uid).get()
        data = diaper_doc.to_dict()
        assert data is not None
        assert data["prefs"]["lastDiaper"]["mode"] == "dry"
