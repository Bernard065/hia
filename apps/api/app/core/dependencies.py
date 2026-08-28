"""Authentication and role checks shared by protected routes."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.models import User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)

DatabaseSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


def get_current_user(
    credentials: BearerCredentials,
    db: DatabaseSession,
) -> User:
    """Resolve an access token to its user, or reject the request."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="authentication is required")

    try:
        claims = decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid access token") from exc

    if claims.get("type") != "access":
        raise HTTPException(status_code=401, detail="invalid access token")

    user = db.get(User, claims.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="invalid access token")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: str) -> Callable[[CurrentUser], User]:
    """Create a dependency that permits only the supplied application roles."""

    def check(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="insufficient permissions")
        return user

    return check
