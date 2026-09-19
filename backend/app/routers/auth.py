"""Registration, login, current user, profile update, logout."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..config import settings
from ..core.security import create_access_token, hash_password, verify_password
from ..dependencies import CurrentUser, DbSession
from ..models import User
from ..schemas.auth import MessageOut, TokenOut, UserCreate, UserLogin, UserOut, UserUpdate
from ..services.activity import log_activity

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _token_response(user: User) -> TokenOut:
    token = create_access_token(user.id, user.role.value)
    return TokenOut(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserOut.model_validate(user),
    )


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession):
    """Create an account. Returns an access token so the user is signed in immediately."""
    existing = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        )
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        organization=payload.organization,
        last_active_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()
    log_activity(db, f"{user.name} registered as {user.role_label}", "info", user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(payload: UserLogin, db: DbSession):
    user = db.scalars(select(User).where(User.email == payload.email.lower())).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        # Same message either way so the endpoint doesn't leak which emails exist.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated")
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def read_current_user(user: CurrentUser):
    return UserOut.model_validate(user)


@router.patch("/me", response_model=UserOut)
def update_current_user(payload: UserUpdate, user: CurrentUser, db: DbSession):
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.organization is not None:
        user.organization = payload.organization
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/logout", response_model=MessageOut)
def logout(user: CurrentUser, db: DbSession):
    """JWTs are stateless — the client discards the token. We only record the sign-out."""
    user.last_active_at = datetime.now(timezone.utc)
    db.commit()
    return MessageOut(detail="Logged out. Discard the access token on the client.")
