import asyncio

from sqlalchemy import select

from app.config import get_settings
from app.database import SessionFactory, engine
from app.models import User, UserRole
from app.security import hash_password


async def main() -> None:
    settings = get_settings()
    if not settings.admin_email or not settings.admin_password:
        raise RuntimeError("Set ADMIN_EMAIL and ADMIN_PASSWORD before seeding the admin")

    email = settings.admin_email.strip().lower()
    async with SessionFactory.begin() as session:
        existing = await session.scalar(select(User).where(User.email == email))
        if existing:
            print(f"Admin already exists: {email}")
        else:
            session.add(
                User(
                    email=email,
                    password_hash=hash_password(settings.admin_password),
                    role=UserRole.ADMIN,
                )
            )
            print(f"Admin created: {email}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
