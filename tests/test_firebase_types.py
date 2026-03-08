"""Unit tests for strict Firebase schema models."""

from huckleberry_api.firebase_types import (
    FirebaseDiaperDocumentData,
    FirebaseFeedDocumentData,
    FirebaseSleepDocumentData,
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
