from app.services.review import start_review
from app.services.words import add_word, delete_word, list_topics
from tests.conftest import make_word


async def test_numbers_increment_per_user(session, user, other_user):
    w1 = await add_word(session, user, "a", "b", None)
    w2 = await add_word(session, user, "c", "d", None)
    w_other = await add_word(session, other_user, "e", "f", None)
    assert (w1.number, w2.number) == (1, 2)
    assert w_other.number == 1


async def test_delete_pending_word_clears_pending(session, user):
    word = await make_word(session, user, 1)
    await start_review(session, user)
    assert user.pending_word_id == word.id
    assert await delete_word(session, user, 1) is True
    assert user.pending_word_id is None


async def test_topics_with_counts(session, user):
    await make_word(session, user, 1, topic="Security")
    await make_word(session, user, 2, topic="Security")
    await make_word(session, user, 3, topic="Databases")
    await make_word(session, user, 4, topic=None)
    assert await list_topics(session, user) == [("Databases", 1), ("Security", 2)]
