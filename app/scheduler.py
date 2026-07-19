"""Scheduled trigger: обходит пользователей с включёнными уведомлениями и вызывает
тот же start_review, что и /go. Своей логики выбора карточек не содержит.
Ошибка одного пользователя логируется и не останавливает остальных.
"""

import asyncio
import logging

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.render import card_message
from app.config import Config
from app.models import User
from app.services.review import start_review

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


async def _review_one_user(
    bot: Bot,
    session_factory: async_sessionmaker[AsyncSession],
    config: Config,
    user_id: int,
    semaphore: asyncio.Semaphore,
) -> None:
    async with semaphore:
        try:
            async with session_factory() as session:
                user = await session.get(User, user_id)
                if user is None or not user.notifications_enabled:
                    return
                card = await start_review(
                    session, user, None, source="scheduled", ttl=config.pending_ttl
                )
                await session.commit()
                chat_id = user.telegram_user_id
            if card is None:
                return
            text, markup = card_message(card)
            await bot.send_message(chat_id, text, reply_markup=markup)
        except Exception:
            logger.exception("scheduled review failed for user_id=%s", user_id)


async def send_scheduled_reviews(
    bot: Bot, session_factory: async_sessionmaker[AsyncSession], config: Config
) -> None:
    logger.info("scheduled review run started")
    semaphore = asyncio.Semaphore(config.scheduler_concurrency)
    processed = 0
    last_id = 0
    while True:
        async with session_factory() as session:
            user_ids = list(
                (
                    await session.scalars(
                        select(User.id)
                        .where(User.notifications_enabled.is_(True), User.id > last_id)
                        .order_by(User.id)
                        .limit(PAGE_SIZE)
                    )
                ).all()
            )
        if not user_ids:
            break
        await asyncio.gather(
            *(
                _review_one_user(bot, session_factory, config, user_id, semaphore)
                for user_id in user_ids
            )
        )
        processed += len(user_ids)
        last_id = user_ids[-1]
    logger.info("scheduled review run finished, users processed: %s", processed)
