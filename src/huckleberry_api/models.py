"""API input models.

Return models are defined in `firebase_types.py` to keep API outputs Firebase-native.
"""

from __future__ import annotations

from .firebase_types import (
    FirebaseDiaperData,
    FirebaseFeedIntervalData,
    FirebaseSleepIntervalData,
    FirebaseSolidsFeedIntervalData,
    HealthDataEntry,
    Number,
    SolidsFoodSource,
    StrictModel,
)


class SolidsFoodReference(StrictModel):
    """Reference to an existing curated/custom food."""

    id: str
    source: SolidsFoodSource
    name: str
    amount: str | Number


class CalendarEvents(StrictModel):
    """Calendar events grouped by tracker type with Firebase-validated payloads."""

    sleep: list[FirebaseSleepIntervalData]
    feed: list[FirebaseFeedIntervalData]
    solids: list[FirebaseSolidsFeedIntervalData]
    diaper: list[FirebaseDiaperData]
    health: list[HealthDataEntry]
