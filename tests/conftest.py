"""Shared fixtures for integration tests.

These fixtures are automatically discovered by pytest and available to all test files.
"""

import os
from collections.abc import AsyncIterator

import aiohttp
import pytest
import pytest_asyncio

from huckleberry_api import HuckleberryAPI


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
    await api_instance.authenticate()

    yield api_instance

    # Cleanup: stop all listeners
    await api_instance.stop_all_listeners()


@pytest_asyncio.fixture
async def child_uid(api: HuckleberryAPI) -> str:
    """Get child UID for testing."""
    user_doc = await api.get_user_document()
    if not user_doc or not user_doc.childList:
        pytest.skip("No children found in test account")
    return user_doc.childList[0].cid
