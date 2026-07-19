"""MCP-сервер TermLoop: запись терминов в словарь прямо из разговора с LLM.

Работает рядом с ботом над той же SQLite (WAL). Карточки пишутся в аккаунт
владельца (MCP_TELEGRAM_USER_ID) и попадают в общую ротацию повторения.
"""

import logging
import os
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.services.users import get_or_create_user
from app.services.words import add_word, list_topics, list_words
from app.validation import validate_card_fields

logger = logging.getLogger(__name__)

LIST_LIMIT = 200


@dataclass(frozen=True)
class McpConfig:
    database_url: str
    telegram_user_id: int
    host: str
    port: int
    auth_token: str


def load_mcp_config() -> McpConfig:
    raw_id = os.environ.get("MCP_TELEGRAM_USER_ID", "").strip()
    if not raw_id.lstrip("-").isdigit():
        raise RuntimeError("MCP_TELEGRAM_USER_ID не задан — чей словарь пополнять?")
    return McpConfig(
        database_url=os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./data/termloop.db"),
        telegram_user_id=int(raw_id),
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8210")),
        auth_token=os.environ.get("MCP_AUTH_TOKEN", "").strip(),
    )


async def add_term_impl(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user_id: int,
    term: str,
    definition: str,
    topic: str | None,
) -> str:
    term = term.strip()
    definition = definition.strip()
    topic = (topic or "").strip() or None
    error = validate_card_fields(term, definition, topic)
    if error:
        return f"Не сохранено: {error}"
    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_user_id)
        word = await add_word(session, user, term, definition, topic)
        await session.commit()
        suffix = f" (тема: {topic})" if topic else ""
        logger.info("mcp add_term: user=%s word_id=%s", user.id, word.id)
        return f"Добавлено в TermLoop: №{word.number} — {term}{suffix}"


async def list_terms_impl(
    session_factory: async_sessionmaker[AsyncSession],
    telegram_user_id: int,
    topic: str | None,
) -> str:
    topic = (topic or "").strip() or None
    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_user_id)
        words = await list_words(session, user, topic)
        await session.commit()
    if not words:
        return "Словарь пуст." if topic is None else f"В теме «{topic}» карточек нет."
    lines = [
        f"№{w.number} [{w.topic or '—'}] {w.term}: {w.definition} (prio {w.priority})"
        for w in words[:LIST_LIMIT]
    ]
    if len(words) > LIST_LIMIT:
        lines.append(f"…и ещё {len(words) - LIST_LIMIT}.")
    return "\n".join(lines)


async def list_topics_impl(
    session_factory: async_sessionmaker[AsyncSession], telegram_user_id: int
) -> str:
    async with session_factory() as session:
        user = await get_or_create_user(session, telegram_user_id)
        topics = await list_topics(session, user)
        await session.commit()
    if not topics:
        return "Тем пока нет."
    return "\n".join(f"{name} — {count}" for name, count in topics)


def create_mcp(
    config: McpConfig, session_factory: async_sessionmaker[AsyncSession]
) -> FastMCP:
    mcp = FastMCP(
        "Gyxer TermLoop",
        instructions=(
            "Личный словарь профессиональных терминов с интервальным повторением "
            "в Telegram. Когда пользователь просит запомнить/записать термин — "
            "вызывай add_term."
        ),
        host=config.host,
        port=config.port,
        stateless_http=True,
    )

    @mcp.tool()
    async def add_term(term: str, definition: str, topic: str | None = None) -> str:
        """Добавить карточку «термин — определение» в словарь TermLoop.

        term — сам термин (до 200 символов), definition — краткое определение
        (до 2000), topic — необязательная тема, например Architecture или Security.
        """
        return await add_term_impl(
            session_factory, config.telegram_user_id, term, definition, topic
        )

    @mcp.tool()
    async def list_terms(topic: str | None = None) -> str:
        """Показать карточки словаря TermLoop, опционально по теме."""
        return await list_terms_impl(session_factory, config.telegram_user_id, topic)

    @mcp.tool()
    async def list_terms_topics() -> str:
        """Показать список тем словаря TermLoop с количеством карточек."""
        return await list_topics_impl(session_factory, config.telegram_user_id)

    return mcp


class BearerAuthMiddleware:
    """Простейшая защита LAN-эндпоинта: статический Bearer-токен из env."""

    def __init__(self, app, token: str):
        self.app = app
        self.token = token

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {self.token}":
                await send(
                    {
                        "type": "http.response.start",
                        "status": 401,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": b"unauthorized"})
                return
        await self.app(scope, receive, send)
