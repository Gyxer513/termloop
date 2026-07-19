"""State machine повторения: IDLE → QUESTION_SHOWN → ANSWER_SHOWN → IDLE.

Единственный use case start_review для обоих триггеров (/go и scheduler).
Callback — недоверенный ввод: принимается только при совпадении владельца,
pending_word_id, review_token и допустимого состояния. Повторный/старый
callback — безопасный no-op (функции возвращают None).
"""

import hmac
import logging
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Word
from app.priority import apply_answer
from app.util import utcnow

logger = logging.getLogger(__name__)

STATE_QUESTION = "QUESTION_SHOWN"
STATE_ANSWER = "ANSWER_SHOWN"

DEFAULT_TTL = timedelta(minutes=30)
CANDIDATE_POOL_SIZE = 10


@dataclass
class ReviewCard:
    word: Word
    token: str
    state: str


@dataclass
class AnswerResult:
    word: Word
    remembered: bool
    old_priority: int
    new_priority: int
    streak: int


def clear_pending(user: User) -> None:
    user.pending_word_id = None
    user.pending_review_token = None
    user.pending_state = None
    user.pending_since = None


def _pending_expired(user: User, now: datetime, ttl: timedelta) -> bool:
    return user.pending_since is None or now - user.pending_since > ttl


def _pending_matches(user: User, word_id: int, token: str) -> bool:
    return (
        user.pending_word_id == word_id
        and user.pending_review_token is not None
        and hmac.compare_digest(user.pending_review_token, token)
    )


async def select_candidates(
    session: AsyncSession, user: User, topic: str | None
) -> list[Word]:
    """Top-10 по priority; случайность применяется в приложении, не ORDER BY RANDOM()."""
    stmt = select(Word).where(Word.user_id == user.id)
    if topic is not None:
        stmt = stmt.where(Word.topic == topic)
    stmt = stmt.order_by(
        Word.priority.desc(), Word.last_reviewed_at.asc(), Word.number.asc()
    ).limit(CANDIDATE_POOL_SIZE)
    return list((await session.scalars(stmt)).all())


async def start_review(
    session: AsyncSession,
    user: User,
    topic: str | None = None,
    *,
    source: str = "manual",
    ttl: timedelta = DEFAULT_TTL,
    now: datetime | None = None,
) -> ReviewCard | None:
    now = now or utcnow()

    if user.pending_word_id is not None:
        if _pending_expired(user, now, ttl):
            clear_pending(user)
        else:
            word = await session.get(Word, user.pending_word_id)
            if word is not None and word.user_id == user.id:
                logger.info(
                    "start_review user=%s source=%s: resume pending state=%s",
                    user.id, source, user.pending_state,
                )
                return ReviewCard(word, user.pending_review_token, user.pending_state)
            clear_pending(user)

    candidates = await select_candidates(session, user, topic)
    if not candidates:
        return None
    word = random.choice(candidates)

    token = secrets.token_hex(8)
    user.pending_word_id = word.id
    user.pending_review_token = token
    user.pending_state = STATE_QUESTION
    user.pending_since = now
    await session.flush()
    logger.info("start_review user=%s source=%s: word_id=%s", user.id, source, word.id)
    return ReviewCard(word, token, STATE_QUESTION)


async def show_definition(
    session: AsyncSession,
    user: User,
    word_id: int,
    token: str,
    *,
    ttl: timedelta = DEFAULT_TTL,
    now: datetime | None = None,
) -> Word | None:
    now = now or utcnow()
    if user.pending_word_id is None:
        return None
    if _pending_expired(user, now, ttl):
        clear_pending(user)
        return None
    if not _pending_matches(user, word_id, token):
        return None
    if user.pending_state not in (STATE_QUESTION, STATE_ANSWER):
        return None

    word = await session.get(Word, word_id)
    if word is None or word.user_id != user.id:
        clear_pending(user)
        return None

    # Повторное нажатие «Показать определение» в ANSWER_SHOWN — идемпотентный re-show.
    user.pending_state = STATE_ANSWER
    return word


async def submit_answer(
    session: AsyncSession,
    user: User,
    word_id: int,
    token: str,
    remembered: bool,
    *,
    ttl: timedelta = DEFAULT_TTL,
    now: datetime | None = None,
) -> AnswerResult | None:
    now = now or utcnow()
    if user.pending_word_id is None:
        return None
    if _pending_expired(user, now, ttl):
        clear_pending(user)
        return None
    if not _pending_matches(user, word_id, token):
        return None
    if user.pending_state != STATE_ANSWER:
        return None

    word = await session.get(Word, word_id)
    if word is None or word.user_id != user.id:
        clear_pending(user)
        return None

    old_priority = word.priority
    new_priority, new_streak = apply_answer(word.priority, word.recall_streak, remembered)
    word.priority = new_priority
    word.recall_streak = new_streak
    word.review_count += 1
    word.last_reviewed_at = now
    clear_pending(user)
    await session.flush()
    return AnswerResult(word, remembered, old_priority, new_priority, new_streak)
