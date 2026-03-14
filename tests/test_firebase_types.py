"""Unit tests for strict Firebase schema models."""

from huckleberry_api.firebase_types import (
    FirebaseGrowthData,
    FirebaseDiaperDocumentData,
    FirebaseFeedDocumentData,
    FirebaseSleepDocumentData,
    FirebasePumpDocumentData,
    FirebasePumpIntervalData,
    FirebasePumpPrefs,
    FirebasePumpMultiContainer,
    FirebaseLastPumpData,
)


def test_feed_document_accepts_empty_last_summary_maps() -> None:
    """Empty feed summary maps should validate after history is cleared."""
    model = FirebaseFeedDocumentData.model_validate(
        {
            "prefs": {
                "lastBottle": {},
                "lastNursing": {},
                "lastSolid": {},
            }
        }
    )

    assert model.prefs is not None
    assert model.prefs.lastBottle is not None
    assert model.prefs.lastBottle.mode is None
    assert model.prefs.lastBottle.bottleType is None
    assert model.prefs.lastNursing is not None
    assert model.prefs.lastNursing.mode is None
    assert model.prefs.lastNursing.duration is None
    assert model.prefs.lastSolid is not None
    assert model.prefs.lastSolid.mode is None
    assert model.prefs.lastSolid.foods is None


def test_sleep_and_diaper_documents_accept_empty_last_summary_maps() -> None:
    """Empty sleep and diaper summary maps should validate after deletions."""
    sleep_model = FirebaseSleepDocumentData.model_validate({"prefs": {"lastSleep": {}}})
    assert sleep_model.prefs is not None
    assert sleep_model.prefs.lastSleep is not None
    assert sleep_model.prefs.lastSleep.start is None
    assert sleep_model.prefs.lastSleep.duration is None

    diaper_model = FirebaseDiaperDocumentData.model_validate(
        {
            "prefs": {
                "lastDiaper": {},
                "lastPotty": {},
            }
        }
    )
    assert diaper_model.prefs is not None
    assert diaper_model.prefs.lastDiaper is not None
    assert diaper_model.prefs.lastDiaper.mode is None
    assert diaper_model.prefs.lastDiaper.start is None
    assert diaper_model.prefs.lastPotty is not None
    assert diaper_model.prefs.lastPotty.mode is None


def test_growth_model_accepts_live_app_imperial_summary_units() -> None:
    """Growth schema should accept the composite imperial units emitted by the live app."""
    model = FirebaseGrowthData.model_validate(
        {
            "_id": "1773175568582-ef0c64260d2686001e96",
            "head": 10.2,
            "headUnits": "hin",
            "height": 5.333333333333333,
            "heightUnits": "ft.in",
            "lastUpdated": 1773175568.582,
            "mode": "growth",
            "multientry_key": None,
            "offset": -120.0,
            "start": 1773175490.0,
            "type": "health",
            "weight": 14.125,
            "weightUnits": "lbs.oz",
        }
    )

    assert model.weightUnits == "lbs.oz"
    assert model.heightUnits == "ft.in"
    assert model.headUnits == "hin"


def test_growth_model_accepts_sparse_live_app_data_rows() -> None:
    """Growth data rows from the live app can omit summary-only fields like `_id` and `type`."""
    model = FirebaseGrowthData.model_validate(
        {
            "head": 30.9,
            "headUnits": "hcm",
            "height": 162.0,
            "heightUnits": "cm",
            "lastUpdated": 1773175665.799,
            "mode": "growth",
            "offset": -120.0,
            "start": 1773175645.668,
            "weight": 9.41,
            "weightUnits": "kg",
        }
    )

    assert model.id_ is None
    assert model.type is None
    assert model.isNight is None
    assert model.weightUnits == "kg"
    assert model.heightUnits == "cm"


def test_pump_interval_model() -> None:
    """Test pump interval data model with leftright mode."""
    model = FirebasePumpIntervalData.model_validate(
        {
            "start": 1773175490.0,
            "entryMode": "leftright",
            "leftAmount": 1.5,
            "rightAmount": 1.6,
            "units": "oz",
            "offset": 420.0,
            "duration": 1800.0,
            "lastUpdated": 1773175490.0,
        }
    )

    assert model.start == 1773175490.0
    assert model.entryMode == "leftright"
    assert model.leftAmount == 1.5
    assert model.rightAmount == 1.6
    assert model.units == "oz"
    assert model.offset == 420.0
    assert model.duration == 1800.0
    assert model.lastUpdated == 1773175490.0


def test_pump_interval_model_total_mode() -> None:
    """Test pump interval data model with total mode."""
    model = FirebasePumpIntervalData.model_validate(
        {
            "start": 1773175490.0,
            "entryMode": "total",
            "leftAmount": 1.55,
            "rightAmount": 1.55,
            "units": "oz",
            "offset": 420.0,
            "duration": 1500.0,
        }
    )

    assert model.entryMode == "total"
    assert model.leftAmount == 1.55
    assert model.rightAmount == 1.55
    assert model.units == "oz"
    assert model.offset == 420.0
    assert model.duration == 1500.0


def test_pump_interval_model_ml_units() -> None:
    """Test pump interval data model with ml units."""
    model = FirebasePumpIntervalData.model_validate(
        {
            "start": 1773175490.0,
            "entryMode": "leftright",
            "leftAmount": 45.0,
            "rightAmount": 50.0,
            "units": "ml",
            "offset": 0.0,
        }
    )

    assert model.leftAmount == 45.0
    assert model.rightAmount == 50.0
    assert model.units == "ml"


def test_last_pump_data_model() -> None:
    """Test last pump data model for prefs.lastPump structure."""
    model = FirebaseLastPumpData.model_validate(
        {
            "start": 1773175490.0,
            "entryMode": "total",
            "leftAmount": 1.6,
            "rightAmount": 1.6,
            "units": "oz",
            "duration": 1800.0,
            "offset": 420.0,
        }
    )

    assert model.start == 1773175490.0
    assert model.entryMode == "total"
    assert model.leftAmount == 1.6
    assert model.rightAmount == 1.6
    assert model.units == "oz"
    assert model.duration == 1800.0
    assert model.offset == 420.0


def test_pump_prefs_model() -> None:
    """Test pump preferences model."""
    model = FirebasePumpPrefs.model_validate(
        {
            "lastPump": {
                "start": 1773175490.0,
                "entryMode": "leftright",
                "leftAmount": 1.5,
                "rightAmount": 1.6,
                "units": "oz",
                "duration": 1800.0,
                "offset": 420.0,
            },
            "timestamp": {"seconds": 1773175490, "nanos": 0},
        }
    )

    assert model.lastPump is not None
    assert model.lastPump.entryMode == "leftright"
    assert model.lastPump.units == "oz"


def test_pump_document_data_model() -> None:
    """Test pump document data model."""
    model = FirebasePumpDocumentData.model_validate(
        {
            "prefs": {
                "lastPump": {
                    "start": 1773175490.0,
                    "entryMode": "total",
                    "leftAmount": 2.0,
                    "rightAmount": 2.0,
                    "units": "oz",
                    "duration": 2000.0,
                    "offset": 420.0,
                }
            }
        }
    )

    assert model.prefs is not None
    assert model.prefs.lastPump is not None
    assert model.prefs.lastPump.entryMode == "total"
    assert model.prefs.lastPump.units == "oz"


def test_pump_multi_container_model() -> None:
    """Test pump multi-container model for batched writes."""
    model = FirebasePumpMultiContainer.model_validate(
        {
            "multi": True,
            "hasMoreRoom": False,
            "data": {
                "interval1": {
                    "start": 1773175490.0,
                    "entryMode": "leftright",
                    "leftAmount": 1.5,
                    "rightAmount": 1.6,
                    "units": "oz",
                    "offset": 420.0,
                },
                "interval2": {
                    "start": 1773176490.0,
                    "entryMode": "total",
                    "leftAmount": 1.55,
                    "rightAmount": 1.55,
                    "units": "oz",
                    "offset": 420.0,
                },
            },
        }
    )

    assert model.multi is True
    assert model.data is not None
    assert len(model.data) == 2
    assert "interval1" in model.data
    assert "interval2" in model.data
    assert model.data["interval2"].leftAmount == 1.55
    assert model.data["interval2"].rightAmount == 1.55
