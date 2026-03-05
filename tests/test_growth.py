"""Growth tracking tests for Huckleberry API."""

import asyncio

from huckleberry_api import HuckleberryAPI


class TestGrowthTracking:
    """Test growth tracking functionality."""

    async def test_log_growth_metric(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging growth measurement in metric units."""
        await api.log_growth(child_uid, weight=5.2, height=52.0, head=35.0, units="metric")
        await asyncio.sleep(1)

        # Verify it was logged by checking health collection
        db = await api.get_firestore_client()
        health_doc = await db.collection("health").document(child_uid).get()
        data = health_doc.to_dict()
        assert data is not None
        assert "lastGrowthEntry" in data.get("prefs", {})

    async def test_log_growth_imperial(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test logging growth measurement in imperial units."""
        await api.log_growth(child_uid, weight=11.5, height=20.5, head=13.8, units="imperial")
        await asyncio.sleep(1)

        db = await api.get_firestore_client()
        health_doc = await db.collection("health").document(child_uid).get()
        data = health_doc.to_dict()
        assert data is not None
        assert "lastGrowthEntry" in data.get("prefs", {})

    async def test_get_growth_data(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test retrieving growth data."""
        growth_data = await api.get_growth_data(child_uid)
        if growth_data is None:
            return

        assert growth_data.mode == "growth"
        if growth_data.weightUnits is not None:
            assert growth_data.weightUnits in ("kg", "lbs")
        if growth_data.heightUnits is not None:
            assert growth_data.heightUnits in ("cm", "in")
        if growth_data.headUnits is not None:
            assert growth_data.headUnits in ("hcm", "hin")
