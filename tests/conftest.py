"""Shared fixtures for integration tests.

These fixtures are automatically discovered by pytest and available to all test files.
"""

import asyncio
import os
import time
from collections.abc import AsyncIterator
from typing import TypedDict

import aiohttp
import pytest
import pytest_asyncio

from huckleberry_api import HuckleberryAPI


class AuthSnapshot(TypedDict):
    """Cached authenticated session state reused across integration tests."""

    id_token: str
    refresh_token: str
    user_uid: str
    token_expires_at: float


_AUTH_CACHE: dict[tuple[str, str, str], AuthSnapshot] = {}
_AUTH_CACHE_LOCK = asyncio.Lock()


async def _load_auth_snapshot(api_instance: HuckleberryAPI, cache_key: tuple[str, str, str]) -> AuthSnapshot:
    """Authenticate once per credential set and reuse the resulting tokens across tests."""
    async with _AUTH_CACHE_LOCK:
        cached_snapshot = _AUTH_CACHE.get(cache_key)
        if cached_snapshot and cached_snapshot["token_expires_at"] > time.time() + 300:
            return cached_snapshot

        await api_instance.authenticate()
        assert api_instance.id_token is not None
        assert api_instance.refresh_token is not None
        assert api_instance.user_uid is not None
        assert api_instance.token_expires_at is not None

        new_snapshot: AuthSnapshot = {
            "id_token": api_instance.id_token,
            "refresh_token": api_instance.refresh_token,
            "user_uid": api_instance.user_uid,
            "token_expires_at": api_instance.token_expires_at,
        }
        _AUTH_CACHE[cache_key] = new_snapshot
        return new_snapshot


@pytest_asyncio.fixture
async def websession() -> AsyncIterator[aiohttp.ClientSession]:
    """Shared aiohttp websession for API client tests."""
    async with aiohttp.ClientSession() as session:
        yield session


@pytest_asyncio.fixture
async def api(websession: aiohttp.ClientSession) -> AsyncIterator[HuckleberryAPI]:
    """Create API instance with credentials from environment."""
    email = os.getenv("HUCKLEBERRY_EMAIL")
    password = os.getenv("HUCKLEBERRY_PASSWORD")
    timezone = os.getenv("HUCKLEBERRY_TIMEZONE")

    if not email or not password or not timezone:
        pytest.skip("HUCKLEBERRY_EMAIL, HUCKLEBERRY_PASSWORD, and HUCKLEBERRY_TIMEZONE environment variables required")

    api_instance = HuckleberryAPI(email=email, password=password, timezone=timezone, websession=websession)
    cache_key = (email, password, timezone)
    snapshot = await _load_auth_snapshot(api_instance, cache_key)
    api_instance.id_token = snapshot["id_token"]
    api_instance.refresh_token = snapshot["refresh_token"]
    api_instance.user_uid = snapshot["user_uid"]
    api_instance.token_expires_at = snapshot["token_expires_at"]

    yield api_instance

    # Cleanup: stop all listeners
    await api_instance.stop_all_listeners()

    if (
        api_instance.id_token is not None
        and api_instance.refresh_token is not None
        and api_instance.user_uid is not None
        and api_instance.token_expires_at is not None
    ):
        updated_snapshot: AuthSnapshot = {
            "id_token": api_instance.id_token,
            "refresh_token": api_instance.refresh_token,
            "user_uid": api_instance.user_uid,
            "token_expires_at": api_instance.token_expires_at,
        }
        _AUTH_CACHE[cache_key] = updated_snapshot


@pytest_asyncio.fixture
async def child_uid(api: HuckleberryAPI) -> str:
    """Get child UID for testing."""
    user_doc = await api.get_user()
    if not user_doc or not user_doc.childList:
        pytest.skip("No children found in test account")
    return user_doc.childList[0].cid
