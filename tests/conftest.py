"""Shared fixtures for integration tests.

These fixtures are automatically discovered by pytest and available to all test files.
"""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from huckleberry_api import HuckleberryAPI


@pytest_asyncio.fixture(scope="module")
async def api() -> AsyncIterator[HuckleberryAPI]:
    """Create API instance with credentials from environment."""
    email = os.getenv("HUCKLEBERRY_EMAIL")
    password = os.getenv("HUCKLEBERRY_PASSWORD")
    timezone = os.getenv("HUCKLEBERRY_TIMEZONE")

    if not email or not password or not timezone:
        pytest.skip("HUCKLEBERRY_EMAIL, HUCKLEBERRY_PASSWORD, and HUCKLEBERRY_TIMEZONE environment variables required")

    api_instance = HuckleberryAPI(email=email, password=password, timezone=timezone)
    await api_instance.authenticate()

    yield api_instance

    # Cleanup: stop all listeners
    await api_instance.stop_all_listeners()


@pytest_asyncio.fixture(scope="module")
async def child_uid(api: HuckleberryAPI) -> str:
    """Get child UID for testing."""
    children = await api.get_children()
    if not children:
        pytest.skip("No children found in test account")
    child_id = children[0].id_
    if not child_id:
        pytest.skip("No child id found in child document")
    return child_id
