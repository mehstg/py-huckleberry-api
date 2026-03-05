"""Feeding tracking tests for Huckleberry API."""

import asyncio

from google.cloud import firestore

from huckleberry_api import HuckleberryAPI


class TestFeedingTracking:
    """Test feeding tracking functionality."""

    async def test_start_and_cancel_feeding(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test starting and canceling feeding."""
        # Start nursing
        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(1)

        db = await api.get_firestore_client()

        feed_doc = await db.collection("feed").document(child_uid).get()
        assert feed_doc.exists
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is True
        assert data["timer"]["activeSide"] == "left"

        # Cancel nursing
        await api.cancel_nursing(child_uid)
        await asyncio.sleep(1)

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is False

    async def test_feeding_with_side_switch(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test feeding with side switching."""
        # Start nursing on left
        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(2)

        # Switch to right
        await api.switch_nursing_side(child_uid)
        await asyncio.sleep(2)

        db = await api.get_firestore_client()

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is True
        assert data["timer"]["activeSide"] == "right"
        assert data["timer"]["leftDuration"] > 0

        # Complete nursing
        await api.complete_nursing(child_uid)
        await asyncio.sleep(1)

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is False
        assert "lastNursing" in data.get("prefs", {})

    async def test_feeding_pause_resume(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test feeding pause and resume."""
        # Start nursing
        await api.start_nursing(child_uid, side="right")
        await asyncio.sleep(2)

        # Pause
        await api.pause_nursing(child_uid)
        await asyncio.sleep(1)

        db = await api.get_firestore_client()

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is True
        assert data["timer"]["paused"] is True

        # Resume
        await api.resume_nursing(child_uid)
        await asyncio.sleep(1)

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is True
        assert data["timer"]["paused"] is False

        # Cancel to cleanup
        await api.cancel_nursing(child_uid)

    async def test_resume_feeding_with_explicit_side(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test resuming feeding with explicit side parameter."""
        # Start nursing on left
        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(2)

        # Pause
        await api.pause_nursing(child_uid)
        await asyncio.sleep(1)

        # Resume on right (explicit side)
        await api.resume_nursing(child_uid, side="right")
        await asyncio.sleep(1)

        db = await api.get_firestore_client()

        feed_doc = await db.collection("feed").document(child_uid).get()
        data = feed_doc.to_dict()
        assert data is not None
        assert data["timer"]["active"] is True
        assert data["timer"]["paused"] is False
        assert data["timer"]["activeSide"] == "right"

        # Cancel to cleanup
        await api.cancel_nursing(child_uid)

    async def test_complete_feeding_creates_interval(self, api: HuckleberryAPI, child_uid: str) -> None:
        """Test that completing feeding creates interval document."""
        # Start and complete nursing
        await api.start_nursing(child_uid, side="left")
        await asyncio.sleep(3)
        await api.complete_nursing(child_uid)
        await asyncio.sleep(2)

        db = await api.get_firestore_client()

        # Check intervals subcollection
        intervals_ref = db.collection("feed").document(child_uid).collection("intervals")

        # Get most recent interval
        recent_intervals = intervals_ref.order_by("start", direction=firestore.Query.DESCENDING).limit(1)

        intervals_list = list(await recent_intervals.get())
        assert len(intervals_list) > 0

        interval_data = intervals_list[0].to_dict()
        assert interval_data is not None
        assert "start" in interval_data
        assert "mode" in interval_data
        assert interval_data["mode"] == "breast"
