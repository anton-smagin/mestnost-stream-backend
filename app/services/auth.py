"""Authentication service — password hashing, JWT creation, register/login logic."""

from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Return True if *password* matches the stored bcrypt *hashed* value."""
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(user_id: str) -> str:
    """Create a signed JWT with a ``sub`` claim set to *user_id*.

    Expiry is controlled by ``settings.jwt_expire_minutes``.
    """
    expire = datetime.now(tz=UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    display_name: str,
) -> User:
    """Create and persist a new User.

    Raises:
        HTTPException(409): if *email* is already registered.
    """
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{email}' is already registered.",
        )

    user = User(
        email=email,
        display_name=display_name,
        password_hash=hash_password(password),
    )
    db.add(user)
    await db.flush()  # populate id / timestamps without committing — get_db commits on exit
    await db.refresh(user)
    return user


async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict[str, str]:
    """Verify credentials and return a bearer token dict.

    Returns:
        ``{"access_token": "<jwt>", "token_type": "bearer"}``

    Raises:
        HTTPException(401): if credentials are invalid.
    """
    _invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        raise _invalid

    if not verify_password(password, user.password_hash):
        raise _invalid

    token = create_access_token(str(user.id))
    return {"access_token": token, "token_type": "bearer"}
