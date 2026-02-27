# QA Agent Memory — Label Stream Backend

## Project Quick Reference
- Backend: `/workspace/backend`, FastAPI + SQLAlchemy 2.0 async + Alembic + PostgreSQL
- Run tests: `cd /workspace/backend && uv run pytest -x -v --tb=short`
- Lint: `cd /workspace/backend && uv run ruff check . && uv run ruff format --check .`
- Smoke test server port: 8111 (used in Phase 2 QA)

## Phase 2 QA Results (2026-02-27) — PASS
All 44 tests pass. Lint clean (55 files). See `patterns.md` for detailed findings.

## Known Issues / Observations
1. **422 responses NOT envelope-wrapped**: FastAPI's default RequestValidationError handler
   returns `{"detail": [...]}` not `{"data": null, "error": "...", "meta": null}`.
   `main.py` only registers an `HTTPException` handler. Fix: add a
   `RequestValidationError` handler in `app/main.py`.
   - Confirmed for: `/api/v1/albums/not-a-uuid`, `/api/v1/tracks/not-a-uuid`
   - Tests pass because test_get_album_invalid_uuid etc. only check `status_code == 422`

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

## Recurring Lint Notes
- `uv` deprecation warning about `tool.uv.dev-dependencies` — harmless, will be
  resolved when pyproject.toml migrates to `dependency-groups.dev`

See also: `patterns.md` for architecture details.
