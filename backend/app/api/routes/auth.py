from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserRole
from app.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut, UserRoleUpdate
from app.services import audit

router = APIRouter(tags=["auth"])

# Simple in-process brute-force throttle (per email + client IP). For multi-replica
# deployments put a shared limiter (e.g. Redis / API gateway) in front.
_MAX_FAILURES = 5
_WINDOW_SECONDS = 900
_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _throttle_key(email: str, request: Request) -> str:
    return f"{email.lower()}|{audit.client_ip(request)}"


def _is_locked(key: str) -> bool:
    now = time.monotonic()
    with _lock:
        q = _failures[key]
        while q and now - q[0] > _WINDOW_SECONDS:
            q.popleft()
        return len(q) >= _MAX_FAILURES


def _record_failure(key: str) -> None:
    with _lock:
        _failures[key].append(time.monotonic())


def reset_throttle() -> None:
    with _lock:
        _failures.clear()


@router.post("/auth/register", response_model=UserOut, status_code=201)
def register(body: RegisterRequest, db: DbSession, request: Request) -> User:
    settings = get_settings()
    user_count = db.scalar(select(func.count()).select_from(User)) or 0
    if user_count > 0 and not settings.allow_registration:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Self-registration is disabled")
    if db.scalar(select(User).where(func.lower(User.email) == body.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=body.email.lower(),
        full_name=body.full_name,
        hashed_password=hash_password(body.password),
        # The very first account bootstraps the installation as administrator.
        role=UserRole.ADMIN.value if user_count == 0 else UserRole.MEMBER.value,
    )
    db.add(user)
    db.flush()
    audit.record(
        db,
        "user.register",
        actor=user,
        resource_type="user",
        resource_id=user.id,
        request=request,
        details={"role": user.role},
    )
    return user


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
    key = _throttle_key(body.email, request)
    if _is_locked(key):
        audit.record(
            db,
            "auth.login",
            actor_email=body.email,
            outcome="blocked",
            resource_type="user",
            request=request,
        )
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts, try again later"
        )
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.hashed_password)
    ):
        _record_failure(key)
        audit.record(
            db,
            "auth.login",
            actor_email=body.email,
            outcome="failure",
            resource_type="user",
            request=request,
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    audit.record(
        db, "auth.login", actor=user, resource_type="user", resource_id=user.id, request=request
    )
    settings = get_settings()
    token = create_access_token(str(user.id), {"role": user.role})
    return TokenResponse(access_token=token, expires_in=settings.access_token_expire_minutes * 60)


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: DbSession, _: AdminUser) -> list[User]:
    return list(db.scalars(select(User).order_by(User.id)))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int, body: UserRoleUpdate, db: DbSession, admin: AdminUser, request: Request
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id and (body.role == "member" or body.is_active is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Administrators cannot demote themselves")
    changes = body.model_dump(exclude_none=True)
    for field, value in changes.items():
        setattr(user, field, value)
    audit.record(
        db,
        "user.update",
        actor=admin,
        resource_type="user",
        resource_id=user.id,
        request=request,
        details=changes,
    )
    return user
