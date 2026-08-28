"""Password, JWT, and refresh-token digest utilities."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a password hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, role: str, session_id: str) -> str:
    """Create a short-lived access token."""
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "role": role,
        "sid": session_id,
        "exp": expires_at,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, session_id: str) -> str:
    """Create a refresh token for one server-side session."""
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "sid": session_id,
        "jti": str(uuid4()),
        "exp": expires_at,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JSON Web Token."""
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=[settings.JWT_ALGORITHM],
    )


def hash_refresh_token(token: str) -> str:
    """Return a non-reversible digest for refresh-token storage."""
    return sha256(token.encode("utf-8")).hexdigest()
