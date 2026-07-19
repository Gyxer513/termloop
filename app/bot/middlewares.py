import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Сессия на update; commit после успешного хендлера, rollback — контекст-менеджером."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            result = await handler(event, data)
            await session.commit()
            return result


class AllowlistMiddleware(BaseMiddleware):
    """Необязательный закрытый режим: игнорировать всех вне allowlist Telegram ID."""

    def __init__(self, allowed_ids: frozenset[int]):
        self.allowed_ids = allowed_ids

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        if from_user is None or from_user.id not in self.allowed_ids:
            return None
        return await handler(event, data)


class RateLimitMiddleware(BaseMiddleware):
    """Простой in-memory rate limit на команды: лишние сообщения молча отбрасываются."""

    def __init__(self, limit: int = 20, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self.buckets: dict[int, deque[float]] = defaultdict(deque)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        if from_user is not None:
            bucket = self.buckets[from_user.id]
            now = time.monotonic()
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.limit:
                logger.warning("rate limit exceeded for telegram_user_id=%s", from_user.id)
                return None
            bucket.append(now)
        return await handler(event, data)
