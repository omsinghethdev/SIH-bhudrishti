"""User & Role Management — planner (admin) only, plus the public permission matrix."""
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from ..core.security import hash_password
from ..dependencies import CurrentUser, DbSession, PlannerUser
from ..models import ROLE_LABELS, Role, User
from ..schemas.auth import MessageOut, UserAdminUpdate, UserCreate, UserOut
from ..schemas.cadastre import Page
from ..services.activity import log_activity, relative_time

router = APIRouter(prefix="/api/users", tags=["users"])

# Mirrors the frontend's PERMISSION_MATRIX and ROLE_NAV_ACCESS.
PERMISSION_MATRIX = [
    ("3D Cadastre Explorer", True, True, True, "Public view only"),
    ("Conflict Radar", True, True, False, False),
    ("Proposed Infrastructure", True, True, False, False),
    ("Vertical Stack", True, False, True, False),
    ("Underground / X-Ray", True, False, True, False),
    ("Survey & Data Intake", True, False, True, False),
    ("Property Search", True, True, True, True),
    ("Property Passport", True, True, False, "Masked data"),
    ("Analytics & Reports", True, True, False, False),
    ("User & Role Management", True, False, False, False),
]

ROLE_NAV_ACCESS = {
    Role.planner: "all",
    Role.constructor: ["overview", "explorer", "proposed", "conflicts", "analytics", "search", "passport"],
    Role.surveyor: ["explorer", "vstack", "underground", "intake", "search", "passport"],
    Role.public: ["explorer", "search", "passport"],
}

ROLE_DEFAULT_VIEW = {
    Role.planner: "overview",
    Role.constructor: "explorer",
    Role.surveyor: "explorer",
    Role.public: "explorer",
}


@router.get("/permissions")
def read_permissions(user: CurrentUser):
    """The permission matrix plus this user's own navigation access."""
    access = ROLE_NAV_ACCESS[user.role]
    return {
        "roles": [{"value": r.value, "label": ROLE_LABELS[r]} for r in Role],
        "matrix": [
            {
                "module": row[0],
                "planner": row[1],
                "constructor": row[2],
                "surveyor": row[3],
                "public": row[4],
            }
            for row in PERMISSION_MATRIX
        ],
        "my_role": user.role.value,
        "my_nav_access": access,
        "my_default_view": ROLE_DEFAULT_VIEW[user.role],
    }


@router.get("", response_model=Page[dict])
def list_users(
    admin: PlannerUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    role: Role | None = None,
    search: str | None = Query(None, max_length=120),
):
    stmt = select(User)
    count_stmt = select(func.count(User.id))
    if role is not None:
        stmt = stmt.where(User.role == role)
        count_stmt = count_stmt.where(User.role == role)
    if search:
        pattern = f"%{search.lower()}%"
        cond = func.lower(User.name).like(pattern) | func.lower(User.email).like(pattern)
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = db.scalar(count_stmt) or 0
    rows = db.scalars(stmt.order_by(User.name).offset((page - 1) * page_size).limit(page_size)).all()
    items = [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "role": u.role.value,
            "role_label": u.role_label,
            "org": u.organization or "—",
            "active": relative_time(u.last_active_at) if u.last_active_at else "Never",
            "status": "Active" if u.is_active else "Inactive",
        }
        for u in rows
    ]
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, admin: PlannerUser, db: DbSession):
    """'Add User' in User & Role Management."""
    if db.scalars(select(User).where(User.email == payload.email.lower())).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        )
    user = User(
        name=payload.name.strip(),
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role,
        organization=payload.organization,
    )
    db.add(user)
    db.flush()
    log_activity(db, f"{admin.name} created account for {user.name}", "info", admin)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, admin: PlannerUser, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut.model_validate(user)


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserAdminUpdate, admin: PlannerUser, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.name is not None:
        user.name = payload.name.strip()
    if payload.organization is not None:
        user.organization = payload.organization
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        if user.id == admin.id and payload.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate your own account"
            )
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)


@router.delete("/{user_id}", response_model=MessageOut)
def delete_user(user_id: int, admin: PlannerUser, db: DbSession):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot delete your own account"
        )
    db.delete(user)
    db.commit()
    return MessageOut(detail="User deleted")
