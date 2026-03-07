# Huckleberry API — Minimal Agent Guide

This file is intentionally minimal.

## Source of Truth

- Firebase payload findings and schema discoveries live in:
  - `src/huckleberry_api/firebase_types.py`
- Behavior and write/read logic live in:
  - `src/huckleberry_api/api.py`

## Critical Rules

1. **Validate values before adding/changing them**
   - For enums, modes, units, state values, keys, or option lists originating from the app/Firebase schema, validate against APK/Firebase evidence first.
   - Never add guessed values.

2. **Keep types strict**
   - Prefer explicit strict models and constrained literals.
   - Avoid loosening to broad `Any`/open dicts/lists unless evidence requires it.

3. **Use `uv` for Python commands**
   - Run tests and Python commands with `uv` (for example: `uv run pytest ...`).

4. **Keep discoveries near code**
   - Add new schema findings as comments/docstrings on the relevant classes/fields in `firebase_types.py`.

## Reverse-Engineering Workflow

- Use: `.copilot/skills/huckleberry-apk-reverse/SKILL.md`
- Current decompilation context: `jadx output latest/`

## Maintenance

When discovering new payload structures or semantics:
- Update `src/huckleberry_api/firebase_types.py` first.
- Add/update tests as needed.
- Keep this file concise.
