"""Unit tests for timezone offset calculation."""

from zoneinfo import ZoneInfoNotFoundError

import aiohttp
import pytest

from huckleberry_api import HuckleberryAPI


class TestTimezoneOffset:
    """Unit tests for timezone offset calculation."""

    async def test_utc_returns_zero(self, websession: aiohttp.ClientSession):
        """UTC timezone should return 0 offset."""
        api = HuckleberryAPI(email="test", password="test", timezone="UTC", websession=websession)
        assert await api._get_timezone_offset_minutes() == 0.0

    async def test_fixed_offset_positive_utc(self, websession: aiohttp.ClientSession):
        """Fixed offset timezone east of UTC (e.g., UTC+2 = -120 minutes)."""
        # Etc/GMT-2 is actually UTC+2 (POSIX convention is inverted)
        api = HuckleberryAPI(email="test", password="test", timezone="Etc/GMT-2", websession=websession)
        assert await api._get_timezone_offset_minutes() == -120.0

    async def test_fixed_offset_negative_utc(self, websession: aiohttp.ClientSession):
        """Fixed offset timezone west of UTC (e.g., UTC-5 = +300 minutes)."""
        # Etc/GMT+5 is actually UTC-5 (POSIX convention is inverted)
        api = HuckleberryAPI(email="test", password="test", timezone="Etc/GMT+5", websession=websession)
        assert await api._get_timezone_offset_minutes() == 300.0

    async def test_invalid_timezone_raises_error(self, websession: aiohttp.ClientSession):
        """Invalid timezone string should raise ZoneInfoNotFoundError."""
        with pytest.raises(ZoneInfoNotFoundError):
            HuckleberryAPI(email="test", password="test", timezone="Invalid/Timezone", websession=websession)

    async def test_real_timezone_reasonable_range(self, websession: aiohttp.ClientSession):
        """Real timezone should return offset in reasonable range."""
        api = HuckleberryAPI(email="test", password="test", timezone="America/New_York", websession=websession)
        offset = await api._get_timezone_offset_minutes()
        # New York is UTC-5 (300) or UTC-4 (240) depending on DST
        assert 240 <= offset <= 300

    async def test_real_timezone_europe(self, websession: aiohttp.ClientSession):
        """European timezone should return expected offset range."""
        api = HuckleberryAPI(email="test", password="test", timezone="Europe/Berlin", websession=websession)
        offset = await api._get_timezone_offset_minutes()
        # Berlin is UTC+1 (-60) or UTC+2 (-120) depending on DST
        assert -120 <= offset <= -60
