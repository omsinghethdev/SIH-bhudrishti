"""Auth dependencies: current user resolution and role gating."""
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .core.security import decode_access_token
from .database import get_db
from .models import Role, User

bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated or token is invalid",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise CREDENTIALS_ERROR
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise CREDENTIALS_ERROR

    user_id = payload.get("sub")
    if user_id is None:
        raise CREDENTIALS_ERROR
    user = db.get(User, int(user_id))
    if user is None:
        raise CREDENTIALS_ERROR
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def require_roles(*roles: Role):
    """Dependency factory: allow only the given roles (planner is always allowed)."""
    allowed = set(roles) | {Role.planner}

    def _guard(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role.value}' is not permitted to access this resource",
            )
        return user

    return _guard


# Convenience guards matching the frontend's PERMISSION_MATRIX.
require_planner = require_roles()  # planner only
require_surveyor = require_roles(Role.surveyor)  # surveyor + planner
require_engineer = require_roles(Role.constructor)  # constructor + planner
require_staff = require_roles(Role.constructor, Role.surveyor)  # any non-public role

PlannerUser = Annotated[User, Depends(require_planner)]
SurveyorUser = Annotated[User, Depends(require_surveyor)]
EngineerUser = Annotated[User, Depends(require_engineer)]
StaffUser = Annotated[User, Depends(require_staff)]
