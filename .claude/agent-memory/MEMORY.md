# Backend Developer Agent Memory

## Project: Label Stream — FastAPI Backend

### Key File Paths
- App entry point: `/workspace/backend/app/main.py`
- Config (JWT, DB, R2): `/workspace/backend/app/core/config.py`
- DB engine/session: `/workspace/backend/app/core/database.py`
- Deps (get_db, CurrentUserID): `/workspace/backend/app/core/deps.py`
- Response helpers (ok/err): `/workspace/backend/app/core/response.py`
- Base model + TimestampMixin: `/workspace/backend/app/models/base.py`
- Test fixtures: `/workspace/backend/tests/conftest.py`

### Architecture Pattern
Routes (`app/api/v1/`) -> Services (`app/services/`) -> Models (`app/models/`)
Schemas in `app/schemas/`.

### Response Envelope
All responses: `{"data": T, "error": null, "meta": null}` via `ok()` helper.
Errors: `{"data": null, "error": "...", "meta": null}` — handled by global
`HTTPException` handler in `main.py` (added as part of auth layer).

### Password Hashing
Use `bcrypt` directly (NOT `passlib` — passlib 1.7 is incompatible with bcrypt >= 4.0).
Pattern from seed_db.py:
```python
import bcrypt
salt = bcrypt.gensalt()
hash = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")
verified = bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
```

### JWT
Use `python-jose`: `from jose import jwt`
Settings: `settings.jwt_secret`, `settings.jwt_algorithm` (HS256), `settings.jwt_expire_minutes` (1 week)

### pytest-asyncio Configuration (IMPORTANT)
Version 1.3.0 is installed. Must use session-scoped loops in `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```
Without this, second+ tests fail with "Future attached to a different loop" from asyncpg.

### Test DB Pattern
- Tests use the real PostgreSQL DB (no test DB isolation).
- HTTP endpoint tests commit data permanently — use UUID-based emails to avoid conflicts across runs.
- `db_session` fixture uses rollback for direct DB manipulation.
- `sample_user`, `auth_token`, `auth_headers`, `sample_artist` fixtures are in conftest.py.

### Cross-Session Test Fixtures (IMPORTANT)
The `db_session` fixture flushes but does NOT commit. This means data created in `db_session` is NOT visible to API requests, which open their own DB connections.
**Solution for fixtures tested via HTTP**: Use a separate `async_session()` context that commits, then use core DELETE on teardown:
```python
async with async_session() as session:
    session.add(obj); await session.commit()
yield obj
async with async_session() as session:
    await session.execute(delete(Model).where(Model.id == obj_id))
    await session.commit()
```
**Never** use `session.delete(orm_obj)` for teardown if the model has FK with NOT NULL + DB-level CASCADE but NO ORM-level cascade. The ORM emits SET NULL before deleting parent, violating NOT NULL. Use core DELETE to trigger DB CASCADE.

### SQLAlchemy 2.0 Relationship Ordering
`selectinload(Model.rel).order_by(...)` is NOT supported — raises `AttributeError: 'Load' object has no attribute 'order_by'`.
Workaround: sort in Python after loading: `obj.tracks.sort(key=lambda t: t.track_number)`

### Registered Routers (as of Phase 3.3)
- `/api/v1/auth` — POST /register, POST /login
- `/api/v1/artists` — GET / (paginated), GET /{slug} (with albums)
- `/api/v1/albums` — GET /{id} (with tracks sorted by track_number, with artist)
- `/api/v1/tracks` — GET /{id}, GET /{id}/stream (real R2 presigned URL, mock in dev)
- `/api/v1/search` — GET /?q= (ILIKE search across artists, albums, tracks; 5 results/type)
- `/api/v1/me` — GET / (profile), GET/POST /history, GET /likes, POST/DELETE /likes/{id}
- `/api/v1/playlists` — full CRUD + POST /{id}/tracks, DELETE /{id}/tracks/{track_id}
- `/api/v1/admin` — POST /artists, POST /albums, POST /tracks (multipart); all require auth

### R2 / Storage Service (Phase 3)
- File: `app/services/storage.py`
- Mock mode when `settings.r2_endpoint` is empty (dev/test safe — no real R2 calls)
- Mock URL format: `https://mock-r2.dev/{file_key}?expires=3600`
- Key format: `tracks/{artist_slug}/{album_slug}/{NN:02d}_{track_slug}.flac`
- `compute_file_key()` is pure sync; upload/delete/presign are async (import aioboto3 inside)
- aioboto3 is already in pyproject.toml dependencies

### Admin Service Patterns (Phase 3)
- File: `app/services/admin.py`
- All operations check for conflicts (409) before inserting
- Uses `db.flush()` + `db.refresh()` — NOT commit (that's done by get_db dependency)
- Track slugification: `_slugify()` — lowercase, spaces→hyphens, strip non-alphanumeric

### Multipart Form Upload Pattern (B008 noqa required)
```python
from fastapi import File, Form, UploadFile
title: str = Form(...),  # noqa: B008
audio_file: UploadFile = File(...),  # noqa: B008
audio_data = await audio_file.read()
content_type = audio_file.content_type or "audio/flac"
```

### Test: Duplicate Slug Test Pattern
Fixture track slugs have unique hex suffix (`first-track-{hex}`) — can't rely on fixture data for slug collisions. Instead: create a track via API, then attempt to create another with same title.

### Bulk Upload Script
- File: `scripts/upload_tracks.py`
- Uses sync SQLAlchemy + asyncio.run() for uploads
- Directory structure: `{root}/{artist-slug}/{album-slug}/{NN}_{track-slug}.flac`

### ORM Field vs. API Field Naming (PlaylistDetail)
`Playlist.playlist_tracks` (ORM) → `tracks` (API). Use Pydantic `Field(validation_alias=...)`:
```python
class PlaylistDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    tracks: list[PlaylistTrackEntry] = Field(validation_alias="playlist_tracks")
```

### Relationship Refresh After flush()
After `db.flush()`, relationships are NOT automatically populated.
Use: `await db.refresh(obj, attribute_names=["track"])` to eager-load a specific rel.

### sample_user Fixture Update (Phase 2.6)
The `sample_user` fixture was updated to commit (like `sample_artist`) so HTTP tests
can see the user. It now creates a uniquely-named user per test run using UUID prefix.

### Pydantic Email Validation
`pydantic[email]` required for `EmailStr`. Added to pyproject.toml as `"pydantic[email]>=2.0.0"`.

### ruff Rules
- Use `datetime.UTC` not `timezone.utc` (UP017)
- Keep imports isort-sorted with blank line between stdlib and app imports (I001)
