import os
from dataclasses import dataclass
from datetime import timedelta

TERM_MAX_LEN = 200
DEFINITION_MAX_LEN = 2000
TOPIC_MAX_LEN = 50


@dataclass(frozen=True)
class Config:
    bot_token: str
    database_url: str
    timezone: str
    review_times: tuple[tuple[int, int], ...]
    pending_ttl: timedelta
    allowed_telegram_ids: frozenset[int]
    scheduler_concurrency: int


def _parse_review_times(raw: str) -> tuple[tuple[int, int], ...]:
    times: list[tuple[int, int]] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        hour_str, minute_str = chunk.split(":")
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Некорректное время в REVIEW_TIMES: {chunk!r}")
        times.append((hour, minute))
    if not times:
        raise ValueError("REVIEW_TIMES пуст")
    return tuple(times)


def _parse_allowlist(raw: str) -> frozenset[int]:
    ids = {int(part) for part in raw.split(",") if part.strip()}
    return frozenset(ids)


def load_config() -> Config:
    bot_token = os.environ.get("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN не задан (см. .env.example)")
    return Config(
        bot_token=bot_token,
        database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/termloop.db"),
        timezone=os.environ.get("TIMEZONE", "Europe/Moscow"),
        review_times=_parse_review_times(os.environ.get("REVIEW_TIMES", "10:00,19:00")),
        pending_ttl=timedelta(minutes=int(os.environ.get("PENDING_TTL_MINUTES", "30"))),
        allowed_telegram_ids=_parse_allowlist(os.environ.get("ALLOWED_TELEGRAM_IDS", "")),
        scheduler_concurrency=int(os.environ.get("SCHEDULER_CONCURRENCY", "5")),
    )
