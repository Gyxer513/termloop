import asyncio
import logging
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.bot.handlers import router
from app.bot.middlewares import AllowlistMiddleware, DbSessionMiddleware, RateLimitMiddleware
from app.config import load_config
from app.db import create_engine_and_factory
from app.scheduler import send_scheduled_reviews

logger = logging.getLogger(__name__)

BOT_COMMANDS = [
    BotCommand(command="go", description="Начать или продолжить повторение"),
    BotCommand(command="add", description="Добавить карточку"),
    BotCommand(command="list", description="Список карточек"),
    BotCommand(command="topics", description="Список тем"),
    BotCommand(command="notify", description="Напоминания on/off"),
    BotCommand(command="cancel", description="Сбросить активную попытку"),
    BotCommand(command="start", description="Справка"),
]


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = load_config()
    engine, session_factory = create_engine_and_factory(config.database_url)

    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(config=config)
    dp.update.middleware(DbSessionMiddleware(session_factory))
    if config.allowed_telegram_ids:
        allowlist = AllowlistMiddleware(config.allowed_telegram_ids)
        dp.message.outer_middleware(allowlist)
        dp.callback_query.outer_middleware(allowlist)
        logger.info("allowlist enabled: %s ids", len(config.allowed_telegram_ids))
    dp.message.middleware(RateLimitMiddleware())
    dp.include_router(router)

    scheduler = AsyncIOScheduler(timezone=ZoneInfo(config.timezone))
    for hour, minute in config.review_times:
        scheduler.add_job(
            send_scheduled_reviews,
            CronTrigger(hour=hour, minute=minute),
            args=(bot, session_factory, config),
        )
    scheduler.start()
    logger.info(
        "scheduler: %s @ %s",
        ",".join(f"{h:02d}:{m:02d}" for h, m in config.review_times),
        config.timezone,
    )

    await bot.set_my_commands(BOT_COMMANDS)
    # Long polling, публичного webhook endpoint нет.
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
