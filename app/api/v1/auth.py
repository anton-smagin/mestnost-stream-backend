"""Auth routes — /register and /login.

Mounted at /api/v1/auth in app.main.
"""

from fastapi import APIRouter

from app.core.deps import DB
from app.core.response import ok
from app.schemas.auth import LoginRequest, RegisterRequest, UserResponse
from app.services.auth import authenticate_user, register_user

router = APIRouter()


@router.post("/register")
async def register(body: RegisterRequest, db: DB) -> dict:
    """Register a new user and return the created user profile."""
    user = await register_user(
        db=db,
        email=body.email,
        password=body.password,
        display_name=body.display_name,
    )
    return ok(UserResponse.model_validate(user).model_dump(mode="json"))


@router.post("/login")
async def login(body: LoginRequest, db: DB) -> dict:
    """Authenticate credentials and return a bearer token."""
    token_dict = await authenticate_user(db=db, email=body.email, password=body.password)
    return ok(token_dict)
