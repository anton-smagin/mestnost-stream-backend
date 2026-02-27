# Backend Context — FastAPI + PostgreSQL

## Stack
- Python 3.12, FastAPI, SQLAlchemy 2.0 (async), Alembic, Pydantic v2
- Package manager: uv
- Linting: ruff
- Testing: pytest + pytest-asyncio + httpx

## Patterns
- Routes: `app/api/v1/{resource}.py` — thin, calls service functions
- Services: `app/services/{resource}.py` — business logic, DB queries
- Models: `app/models/{resource}.py` — SQLAlchemy ORM models
- Schemas: `app/schemas/{resource}.py` — Pydantic (separate Create/Update/Response)
- Dependencies: `app/core/deps.py` — get_db, get_current_user

## Response Standard
Every endpoint returns:
```json
{ "data": <T or list[T]>, "error": null, "meta": { "page": 1, "total": 42 } }
```
For single items, `meta` can be omitted. For errors:
```json
{ "data": null, "error": "Not found", "meta": null }
```

## Database Conventions
- All PKs: `id UUID DEFAULT gen_random_uuid()`
- All tables: `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`
- Indexes on: all FKs, all columns in WHERE/ORDER BY, text search columns (gin_trgm)
- Soft delete: NO — use hard delete, keep listen_history for analytics

## Audio Streaming
- Files stored in R2: `tracks/{artist_slug}/{album_slug}/{track_number}_{slug}.flac`
- Endpoint `GET /api/v1/tracks/{id}/stream` returns `{ "url": "<presigned_url>" }`
- Presigned URLs expire in 1 hour
- NEVER proxy audio bytes through the backend

## Migration Workflow
1. Edit model
2. `uv run alembic revision --autogenerate -m "add xyz"`
3. Review generated migration (check it's not destructive)
4. `uv run alembic upgrade head`
5. Verify: `psql $DATABASE_URL_SYNC -c "\d tablename"`

## Testing Rules
- Async tests with `pytest-asyncio`
- Use `httpx.AsyncClient` with `app` for API tests
- Fixtures in `tests/conftest.py`: db_session, client, auth_headers, sample_artist, etc.
- Factory functions in `tests/factories.py`
- Every endpoint needs: test_success, test_not_found (if applicable), test_unauthorized
- Run: `uv run pytest -x -v --tb=short`

## Commands
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0    # dev server
uv run pytest -x -v                                      # tests
uv run ruff check .                                      # lint
uv run ruff format .                                     # format
uv run alembic upgrade head                              # migrate
uv run alembic downgrade -1                              # rollback one
```
