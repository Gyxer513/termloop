from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


async def get_user(session: AsyncSession, telegram_user_id: int) -> User | None:
    return await session.scalar(select(User).where(User.telegram_user_id == telegram_user_id))


async def get_or_create_user(session: AsyncSession, telegram_user_id: int) -> User:
    user = await get_user(session, telegram_user_id)
    if user is None:
        user = User(telegram_user_id=telegram_user_id)
        session.add(user)
        await session.flush()
    return user


def set_notifications(user: User, enabled: bool) -> None:
    user.notifications_enabled = enabled
