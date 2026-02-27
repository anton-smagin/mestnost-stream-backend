# QA Agent Memory — Label Stream Backend

## Project Quick Reference
- Backend: `/workspace/backend`, FastAPI + SQLAlchemy 2.0 async + Alembic + PostgreSQL
- Run tests: `cd /workspace/backend && uv run pytest -x -v --tb=short`
- Lint: `cd /workspace/backend && uv run ruff check . && uv run ruff format --check .`
- Smoke test server port: 8111 (used in Phase 2 QA)

## Phase 2 QA Results (2026-02-27) — PASS
All 44 tests pass. Lint clean (55 files). See `patterns.md` for detailed findings.

## Phase 3 QA Results (2026-02-27) — PASS
All 55 tests pass (11 new). Lint clean (61 files). See review notes below.

## Known Issues / Observations
1. **422 responses NOW envelope-wrapped** (RESOLVED in Phase 3): `main.py` now registers
   a `RequestValidationError` handler that returns the standard envelope. Previously
   flagged as not wrapped — confirmed fixed.

2. **`import re` placed inside `_slugify()` body** (`app/services/admin.py` line 34):
   Minor style issue — `import re` should be at module top-level. ruff `PLC0415` does
   NOT flag this because `aioboto3` imports inside `if not settings.r2_endpoint` blocks
   are explicitly allowed via `# noqa: PLC0415`. But `import re` inside `_slugify` is
   an unnecessary inline import — stdlib `re` is always available. Does not affect
   correctness or tests; acceptable to leave but worth noting.

2. **list_playlists pagination mismatch**: Route accepts `page`/`per_page` query params
   but `services/playlist.py::list_playlists()` does not paginate — it returns ALL
   playlists for a user. `meta.total` equals `len(playlists)` (always exact count),
   but large collections could cause a performance issue. No functional bug yet.

3. **Trailing slash redirects (307)**: Routes registered with `@router.get("/")` redirect
   requests without the trailing slash. e.g., `GET /api/v1/artists` → 307 redirect to
   `/api/v1/artists/`. Same for `/api/v1/search`. Mobile clients must follow redirects.

4. **JWT expiry is 1 week** (`jwt_expire_minutes = 60 * 24 * 7`). Acceptable for dev;
   flag for production hardening.

5. **`debug=True` in production config default** — `app/core/config.py` sets
   `debug: bool = True`. Must be overridden in production via env var.

## Confirmed Patterns
- All models use UUID PKs via `TimestampMixin` in `app/models/base.py`
- All timestamps are `DateTime(timezone=True)` — UTC-aware
- Services properly raise `HTTPException`; global handler in `main.py` formats to envelope
- Password never returned in any response schema
- Ownership checks in playlist service (403 for non-owner mutations)
- `app/core/deps.py::get_db` commits on success, rolls back on exception

## Test Coverage Gaps
- No test for `DELETE /me/likes/{track_id}` with invalid (non-UUID) track_id
- No test for `PUT /playlists/{id}` with a non-existent playlist_id
- No test for `DELETE /playlists/{id}` ownership check (403 for non-owner)
- No test for `POST /playlists/{id}/tracks` with non-existent track_id
- No test for pagination on large datasets (list_playlists not paginated in service)
- No test for `GET /me/history` unauthorized access
- No test for `GET /me/likes` unauthorized access
- No test for `GET /tracks/{id}/stream` when track exists but `file_key` is NULL
  (test_get_stream_url_no_file_key does not actually exercise the None-file_key path;
  it re-tests the success path with fixture track1 which has a file_key)
- No test for `POST /admin/tracks` with `track_number < 1` or `duration_seconds < 1`
  (validation guards exist in the route but have no dedicated test)

## Recurring Lint Notes
- `uv` deprecation warning about `tool.uv.dev-dependencies` — harmless, will be
  resolved when pyproject.toml migrates to `dependency-groups.dev`

See also: `patterns.md` for architecture details.
