from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Word
from app.services.review import clear_pending


async def add_word(
    session: AsyncSession, user: User, term: str, definition: str, topic: str | None
) -> Word:
    next_number = (
        await session.scalar(
            select(func.coalesce(func.max(Word.number), 0)).where(Word.user_id == user.id)
        )
    ) + 1
    word = Word(
        user_id=user.id, number=next_number, term=term, definition=definition, topic=topic
    )
    session.add(word)
    await session.flush()
    return word


async def get_word_by_number(session: AsyncSession, user: User, number: int) -> Word | None:
    # Ownership прямо в запросе: чужая карточка неотличима от несуществующей.
    return await session.scalar(
        select(Word).where(Word.user_id == user.id, Word.number == number)
    )


async def edit_word(
    session: AsyncSession,
    user: User,
    number: int,
    term: str,
    definition: str,
    topic: str | None,
) -> Word | None:
    word = await get_word_by_number(session, user, number)
    if word is None:
        return None
    word.term = term
    word.definition = definition
    word.topic = topic
    await session.flush()
    return word


async def delete_word(session: AsyncSession, user: User, number: int) -> bool:
    word = await get_word_by_number(session, user, number)
    if word is None:
        return False
    if user.pending_word_id == word.id:
        clear_pending(user)
    await session.delete(word)
    await session.flush()
    return True


async def list_words(session: AsyncSession, user: User, topic: str | None = None) -> list[Word]:
    stmt = select(Word).where(Word.user_id == user.id)
    if topic is not None:
        stmt = stmt.where(Word.topic == topic)
    stmt = stmt.order_by(Word.number)
    return list((await session.scalars(stmt)).all())


async def list_topics(session: AsyncSession, user: User) -> list[tuple[str, int]]:
    stmt = (
        select(Word.topic, func.count())
        .where(Word.user_id == user.id, Word.topic.is_not(None))
        .group_by(Word.topic)
        .order_by(Word.topic)
    )
    return [(topic, count) for topic, count in (await session.execute(stmt)).all()]
