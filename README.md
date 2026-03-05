# Huckleberry API

[![Integration Tests](https://github.com/Woyken/py-huckleberry-api/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/Woyken/py-huckleberry-api/actions/workflows/integration-tests.yml)

Python API client for the Huckleberry baby tracking app using Firebase Firestore.

## Overview

This is a reverse-engineered API client that connects directly to Huckleberry's Firebase backend using the official Google Cloud Firestore SDK. It provides programmatic access to baby tracking features including sleep, feeding, diaper changes, and growth measurements.

## Features

- 🔐 **Firebase Authentication**: Secure email/password authentication with automatic token refresh
- 💤 **Sleep Tracking**: Start, pause, resume, cancel, and complete sleep sessions
- 🍼 **Feeding Tracking**: Track breastfeeding with left/right side switching
- 🧷 **Diaper Changes**: Log pee, poo, both, or dry checks with color/consistency
- 📏 **Growth Measurements**: Record weight, height, and head circumference
- 🔄 **Real-time Updates**: Firebase snapshot listeners for instant synchronization
- 👶 **Child Management**: Support for multiple children profiles

## Installation

```bash
uv add huckleberry-api
# or
pip install huckleberry-api
```

## Quick Start

```python
import asyncio
import aiohttp

from huckleberry_api import HuckleberryAPI

async def main() -> None:
    async with aiohttp.ClientSession() as websession:
        api = HuckleberryAPI(
            email="your-email@example.com",
            password="your-password",
            timezone="Europe/London",
            websession=websession,
        )

        await api.authenticate()

        children = await api.get_children()
        child_uid = children[0].id_

        await api.start_sleep(child_uid)
        await api.complete_sleep(child_uid)

        await api.start_nursing(child_uid, side="left")
        await api.switch_nursing_side(child_uid)
        await api.complete_nursing(child_uid)

        await api.log_bottle_feeding(child_uid, amount=120.0, bottle_type="Formula", units="ml")
        await api.log_diaper(
            child_uid,
            mode="both",
            pee_amount="medium",
            poo_amount="medium",
            color="yellow",
            consistency="solid",
        )
        await api.log_growth(child_uid, weight=5.2, height=52.0, head=35.0, units="metric")


asyncio.run(main())
```

## Real-time Listeners

Set up real-time listeners for instant updates:

```python
import aiohttp

def on_sleep_update(data):
    timer = data.get("timer", {})
    print(f"Sleep active: {timer.get('active')}")
    print(f"Sleep paused: {timer.get('paused')}")

async def main() -> None:
    async with aiohttp.ClientSession() as websession:
        api = HuckleberryAPI(
            email="your-email@example.com",
            password="your-password",
            timezone="Europe/London",
            websession=websession,
        )
        await api.authenticate()
        children = await api.get_children()
        child_uid = children[0].id_

        await api.setup_realtime_listener(child_uid, on_sleep_update)
        await api.stop_all_listeners()
```

## API Methods

### Authentication
- `await authenticate()` - Authenticate with Firebase
- `await refresh_auth_token()` - Refresh expired token

### Children
- `await get_children()` - Get list of children with profiles

### Sleep Tracking
- `await start_sleep(child_uid)` - Start sleep session
- `await pause_sleep(child_uid)` - Pause active session
- `await resume_sleep(child_uid)` - Resume paused session
- `await cancel_sleep(child_uid)` - Cancel without saving
- `await complete_sleep(child_uid)` - Complete and save to history

### Feeding Tracking
- `await start_nursing(child_uid, side)` - Start breastfeeding session
- `await pause_nursing(child_uid)` - Pause active session
- `await resume_nursing(child_uid, side)` - Resume paused session
- `await switch_nursing_side(child_uid)` - Switch left/right
- `await cancel_nursing(child_uid)` - Cancel without saving
- `await complete_nursing(child_uid)` - Complete and save to history
- `await log_bottle_feeding(child_uid, amount, bottle_type, units)` - Log bottle feeding
  - `bottle_type`: "Breast Milk", "Formula", "Cow Milk", "Soy Milk", etc.
  - `amount`: Volume fed (e.g., 120.0)
  - `units`: "ml" or "oz"

### Diaper Tracking
- `await log_diaper(child_uid, mode, pee_amount, poo_amount, color, consistency)` - Log diaper change
  - `mode`: "pee", "poo", "both", or "dry"
  - `color`: "yellow", "green", "brown", "black", "red"
  - `consistency`: "runny", "soft", "solid", "hard"

### Growth Tracking
- `await log_growth(child_uid, weight, height, head, units)` - Log measurements
  - `units`: "metric" (kg/cm) or "imperial" (lbs/inches)
- `await get_growth_data(child_uid)` - Get latest measurements

### Real-time Listeners
- `await setup_realtime_listener(child_uid, callback)` - Listen to sleep updates
- `await setup_feed_listener(child_uid, callback)` - Listen to feeding updates
- `await setup_health_listener(child_uid, callback)` - Listen to health updates
- `await stop_all_listeners()` - Stop all active listeners

## Type Definitions

The package includes Pydantic models for type safety.

Canonical Firebase schema definitions are in `src/huckleberry_api/firebase_types.py`.

- `ChildData` - Child profile information
- `FirebaseChildDocument` - Child profile information
- `FirebaseSleepDocumentData` / `FirebaseSleepTimerData` - Sleep tracking data
- `FirebaseFeedDocumentData` / `FirebaseFeedTimerData` - Feeding tracking data
- `FirebaseHealthDocumentData` - Health tracking data
- `FirebaseGrowthData` - Growth measurements

## Architecture

This library uses:
- **Firebase Firestore Python SDK** - Official Google Cloud SDK (not REST API)
- **gRPC over HTTP/2** - Real-time communication protocol
- **Protocol Buffers** - Efficient data encoding
- **Firebase Authentication** - Secure token-based auth

### Why Not REST API?

Huckleberry's Firebase Security Rules block non-SDK requests. Direct REST API calls return `403 Forbidden`. This library uses the official Firebase SDK which uses gRPC, the same protocol as the Huckleberry mobile app.

## Requirements

- Python 3.9+
- `google-cloud-firestore>=2.11.0`
- `aiohttp>=3.10.0`
- `pydantic>=2.10.0`

## Development

### Running Tests

Integration tests require Huckleberry account credentials:

```bash
# Set environment variables
$env:HUCKLEBERRY_EMAIL = "test@example.com"
$env:HUCKLEBERRY_PASSWORD = "test-password"

# Run tests
.\run-tests.ps1
```

### Linting, Formatting, and Type Checking

```bash
# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check
uv run ty check --python-version 3.11 --ignore unknown-argument
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

### CI/CD

- PR Validation runs on pull requests and pushes to `main` and checks Ruff linting/formatting and Ty type checking.
- Integration tests run on GitHub Actions and require Huckleberry credentials.

## License

MIT License

## Disclaimer

This is an unofficial, reverse-engineered API client. It is not affiliated with, endorsed by, or connected to Huckleberry Labs Inc. Use at your own risk.

## Related Projects

- [Huckleberry Home Assistant Integration](https://github.com/Woyken/huckleberry-homeassistant) - Home automation integration using this library
