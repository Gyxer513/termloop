from sqlalchemy import select

from app.mcp_server import add_term_impl, list_terms_impl, list_topics_impl
from app.models import User, Word

TG_ID = 777


async def test_add_term_creates_card_for_configured_user(session_factory):
    message = await add_term_impl(session_factory, TG_ID, "CAP", "consistency…", "Distributed")
    assert "№1" in message and "CAP" in message

    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.telegram_user_id == TG_ID))
        word = await session.scalar(select(Word).where(Word.user_id == user.id))
        assert (word.term, word.topic, word.priority) == ("CAP", "Distributed", 100)


async def test_add_term_validates_fields(session_factory):
    message = await add_term_impl(session_factory, TG_ID, "  ", "def", None)
    assert message.startswith("Не сохранено")
    message = await add_term_impl(session_factory, TG_ID, "x" * 201, "def", None)
    assert message.startswith("Не сохранено")


async def test_list_terms_and_topics(session_factory):
    await add_term_impl(session_factory, TG_ID, "CAP", "def1", "Distributed")
    await add_term_impl(session_factory, TG_ID, "ACID", "def2", "Databases")
    listing = await list_terms_impl(session_factory, TG_ID, "Databases")
    assert "ACID" in listing and "CAP" not in listing
    topics = await list_topics_impl(session_factory, TG_ID)
    assert "Databases — 1" in topics and "Distributed — 1" in topics


async def test_list_terms_isolated_by_user(session_factory):
    await add_term_impl(session_factory, TG_ID, "CAP", "def", None)
    assert await list_terms_impl(session_factory, 999, None) == "Словарь пуст."
