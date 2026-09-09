from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db_session
from app.models import GuestSession
from app.security import digest_token, new_opaque_token

router = APIRouter(prefix="/guest-session", tags=["guest session"])
settings = get_settings()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def check_guest_origin(request: Request) -> None:
    if request.headers.get("origin") != settings.frontend_origin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Origin not allowed")


def set_guest_cookies(
    response: Response,
    guest_token: str,
    csrf_token: str,
    max_age: int,
) -> None:
    response.set_cookie(
        "guest_token",
        guest_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=settings.api_v1_prefix,
        max_age=max_age,
    )
    response.set_cookie(
        "guest_csrf_token",
        csrf_token,
        httponly=False,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
        max_age=max_age,
    )


async def find_guest(
    session: AsyncSession,
    raw_token: str | None,
    *,
    lock: bool = False,
) -> GuestSession:
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest session required"
        )

    query = select(GuestSession).where(GuestSession.token_digest == digest_token(raw_token))
    if lock:
        query = query.with_for_update()
    guest = await session.scalar(query)

    if guest is None or guest.expires_at <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Guest session expired"
        )
    return guest


def check_guest_csrf(guest: GuestSession, csrf_token: str | None) -> None:
    if not csrf_token or not compare_digest(guest.csrf_digest, digest_token(csrf_token)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
async def ensure_guest_session(
    request: Request,
    response: Response,
    session: DatabaseSession,
    guest_token: Annotated[str | None, Cookie()] = None,
    guest_csrf_token: Annotated[str | None, Header(alias="X-Guest-CSRF-Token")] = None,
) -> None:
    check_guest_origin(request)
    now = datetime.now(UTC)
    guest = None

    if guest_token:
        guest = await session.scalar(
            select(GuestSession).where(GuestSession.token_digest == digest_token(guest_token))
        )
        if guest and guest.expires_at <= now:
            guest = None

    if guest is None:
        guest_token = new_opaque_token()
        guest_csrf_token = new_opaque_token()
        guest = GuestSession(
            token_digest=digest_token(guest_token),
            csrf_digest=digest_token(guest_csrf_token),
            expires_at=now + timedelta(days=settings.guest_session_days),
        )
        session.add(guest)
        await session.commit()
    elif not guest_csrf_token or not compare_digest(
        guest.csrf_digest, digest_token(guest_csrf_token)
    ):
        guest_csrf_token = new_opaque_token()
        guest.csrf_digest = digest_token(guest_csrf_token)
        await session.commit()

    max_age = max(0, int((guest.expires_at - now).total_seconds()))
    set_guest_cookies(response, guest_token, guest_csrf_token, max_age)
