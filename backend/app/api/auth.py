from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from time import monotonic
from typing import Annotated

import jwt
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.models import RefreshSession, RefreshToken, User, UserRole
from app.schemas import AdminRead, AuthResponse, LoginRequest
from app.security import (
    create_access_token,
    decode_access_token,
    digest_token,
    new_opaque_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
settings = get_settings()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
bearer = HTTPBearer(auto_error=False)
dummy_password_hash = (
    "$argon2id$v=19$m=65536,t=3,p=4$Y2hhbmdlLW1l$4n7J8ux9k6sY6lLYIFQeU41dnw2LA2gFcX2N5f6e/Go"
)
rate_attempts: dict[str, deque[float]] = defaultdict(deque)


def check_rate_limit(key: str, *, limit: int, window_seconds: int = 60) -> None:
    now = monotonic()
    attempts = rate_attempts[key]
    while attempts and attempts[0] <= now - window_seconds:
        attempts.popleft()
    if len(attempts) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts; try again shortly",
            headers={"Retry-After": str(window_seconds)},
        )
    attempts.append(now)


def reject_request(detail: str = "Invalid or expired session") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def check_origin(request: Request) -> None:
    if request.headers.get("origin") != settings.frontend_origin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")


def set_session_cookies(response: Response, refresh_token: str, csrf_token: str) -> None:
    max_age = settings.refresh_session_days * 24 * 60 * 60
    response.set_cookie(
        "refresh_token",
        refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth",
        max_age=max_age,
    )
    response.set_cookie(
        "csrf_token",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


def clear_session_cookies(response: Response) -> None:
    path = f"{settings.api_v1_prefix}/auth"
    response.delete_cookie("refresh_token", path=path)
    response.delete_cookie("csrf_token", path="/")


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user),
        user=AdminRead(id=user.id, email=user.email, role=user.role.value),
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    session: DatabaseSession,
) -> AuthResponse:
    check_origin(request)
    client_host = request.client.host if request.client else "unknown"
    check_rate_limit(f"login:{client_host}:{body.email.lower()}", limit=10)
    user = await session.scalar(select(User).where(User.email == body.email.lower()))

    stored_hash = user.password_hash if user else dummy_password_hash
    password_matches = verify_password(body.password, stored_hash)
    if user is None or not password_matches:
        raise reject_request("Invalid email or password")

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=settings.refresh_session_days)
    csrf_token = new_opaque_token()
    family = RefreshSession(
        user_id=user.id,
        csrf_digest=digest_token(csrf_token),
        absolute_expires_at=expires_at,
    )
    session.add(family)
    await session.flush()

    raw_refresh_token = new_opaque_token()
    session.add(
        RefreshToken(
            session_id=family.id,
            token_digest=digest_token(raw_refresh_token),
            expires_at=expires_at,
        )
    )
    await session.commit()
    set_session_cookies(response, raw_refresh_token, csrf_token)
    return auth_response(user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthResponse:
    check_origin(request)
    client_host = request.client.host if request.client else "unknown"
    check_rate_limit(f"refresh:{client_host}", limit=30)
    if not refresh_token or not csrf_token:
        raise reject_request()

    stored_token = await session.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_digest == digest_token(refresh_token))
        .with_for_update()
    )
    if stored_token is None:
        raise reject_request()

    family = await session.get(RefreshSession, stored_token.session_id, with_for_update=True)
    if family is None:
        raise reject_request()

    now = datetime.now(UTC)
    if family.revoked_at is not None or family.absolute_expires_at <= now:
        raise reject_request()

    if not compare_digest(family.csrf_digest, digest_token(csrf_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    if stored_token.consumed_at is not None:
        family.revoked_at = now
        await session.commit()
        raise reject_request("Refresh token reuse detected; please sign in again")

    if stored_token.expires_at <= now:
        raise reject_request()

    user = await session.get(User, family.user_id)
    if user is None:
        raise reject_request()

    replacement = new_opaque_token()
    next_token = RefreshToken(
        session_id=family.id,
        token_digest=digest_token(replacement),
        expires_at=family.absolute_expires_at,
    )
    session.add(next_token)
    await session.flush()
    stored_token.consumed_at = now
    stored_token.replacement_token_id = next_token.id
    await session.commit()

    set_session_cookies(response, replacement, csrf_token)
    return auth_response(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: DatabaseSession,
    refresh_token: Annotated[str | None, Cookie()] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    check_origin(request)
    if not refresh_token or not csrf_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")

    stored_token = await session.scalar(
        select(RefreshToken).where(RefreshToken.token_digest == digest_token(refresh_token))
    )
    if stored_token is not None:
        family = await session.get(RefreshSession, stored_token.session_id)
        if family and not compare_digest(family.csrf_digest, digest_token(csrf_token)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
        if family:
            family.revoked_at = datetime.now(UTC)
            await session.commit()

    clear_session_cookies(response)


async def get_current_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: DatabaseSession,
) -> User:
    if credentials is None:
        raise reject_request("Authentication required")

    try:
        claims = decode_access_token(credentials.credentials)
        user_id = int(claims["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise reject_request("Invalid access token") from None

    if claims.get("type") != "access" or claims.get("role") != UserRole.ADMIN.value:
        raise reject_request("Invalid access token")

    user = await session.get(User, user_id)
    if user is None or user.role != UserRole.ADMIN:
        raise reject_request("Invalid access token")
    return user


@router.get("/me", response_model=AdminRead)
async def current_admin(
    user: Annotated[User, Depends(get_current_admin)],
) -> AdminRead:
    return AdminRead(id=user.id, email=user.email, role=user.role.value)
