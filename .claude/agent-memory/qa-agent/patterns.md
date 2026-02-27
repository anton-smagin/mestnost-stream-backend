# Architecture Patterns — Label Stream Backend

## Response Envelope
`app/core/response.py` provides:
- `ok(data, page=1, total=None)` — sets `meta` only when `total` is not None
- `err(message, status_code=400)` — always returns `{data: null, error: msg, meta: null}`
- Global `HTTPException` handler in `app/main.py` uses `{data: null, error: exc.detail, meta: null}`
- MISSING: no `RequestValidationError` handler — 422s escape the envelope

## Route Layer Contract
Routes are thin: parse request, call service, call `ok()`. No direct DB access in routes.
Artists route is the only one that does a None-check and raises HTTPException directly
(acceptable pattern per CLAUDE.md).

## Service Layer Contract
Services receive `AsyncSession` and return ORM objects or raise `HTTPException`.
No HTTP concerns except raising HTTPException (acceptable per project conventions).

## Pagination Convention
- Paginated endpoints: `page` (1-based) + `per_page` (default 20, max 100)
- list_artists: paginated in both service and route
- list_listen_history: paginated in both service and route
- list_likes: paginated in both service and route
- list_playlists: ROUTE accepts page/per_page but SERVICE returns ALL (no offset/limit)

## Auth
- JWT via `python-jose`, HS256, 1-week expiry (configurable)
- `CurrentUserID = Annotated[str, Depends(get_current_user_id)]`
- `HTTPBearer` security scheme — returns 401 if missing or invalid
- Password hashed with bcrypt

## Model Base
`TimestampMixin` in `app/models/base.py` provides:
- `id: UUID` (primary key, default=uuid.uuid4)
- `created_at: DateTime(timezone=True)`
- `updated_at: DateTime(timezone=True)` with onupdate

## Seed Data
Seed data is present in DB (Bonobo, Kolinga, The Midnight artists with albums/tracks).
Test fixtures in `tests/conftest.py` create their own data and clean up after each test.
