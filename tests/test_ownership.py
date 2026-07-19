from sqlalchemy import select

from app.models import Word
from app.services.review import show_definition, start_review, submit_answer
from app.services.words import add_word, delete_word, edit_word, list_words
from tests.conftest import make_word


async def test_list_shows_only_own_cards(session, user, other_user):
    await make_word(session, user, 1, term="mine")
    await make_word(session, other_user, 1, term="theirs")
    words = await list_words(session, user)
    assert [w.term for w in words] == ["mine"]


async def test_cannot_edit_foreign_card(session, user, other_user):
    await make_word(session, other_user, 1, term="theirs")
    result = await edit_word(session, user, 1, "hacked", "hacked", None)
    assert result is None
    word = await session.scalar(select(Word).where(Word.user_id == other_user.id))
    assert word.term == "theirs"


async def test_cannot_delete_foreign_card(session, user, other_user):
    await make_word(session, other_user, 1)
    assert await delete_word(session, user, 1) is False
    assert await session.scalar(select(Word).where(Word.user_id == other_user.id)) is not None


async def test_forged_callback_with_foreign_word_rejected(session, user, other_user):
    """B подделывает callback с word_id и token активной попытки A."""
    await make_word(session, user, 1)
    card = await start_review(session, user)
    assert await show_definition(session, other_user, card.word.id, card.token) is None
    assert await submit_answer(session, other_user, card.word.id, card.token, True) is None
    assert card.word.priority == 100


async def test_sql_like_content_stored_as_text(session, user):
    payload = "'; DROP TABLE words;--"
    word = await add_word(session, user, payload, payload, None)
    stored = await session.scalar(select(Word).where(Word.id == word.id))
    assert stored.term == payload
    assert stored.definition == payload
    # таблица жива и запросы работают
    assert len(await list_words(session, user)) == 1
