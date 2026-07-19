from datetime import timedelta

from app.services.review import select_candidates, start_review
from app.services.words import add_word
from app.util import utcnow
from tests.conftest import make_word


async def test_candidates_limited_to_top_10_by_priority(session, user):
    for i in range(1, 16):
        await make_word(session, user, i, priority=i)  # 1..15
    candidates = await select_candidates(session, user, None)
    assert len(candidates) == 10
    assert [w.priority for w in candidates] == list(range(15, 5, -1))


async def test_topic_filter(session, user):
    await make_word(session, user, 1, topic="Security", priority=50)
    await make_word(session, user, 2, topic="Databases", priority=100)
    candidates = await select_candidates(session, user, "Security")
    assert [w.topic for w in candidates] == ["Security"]
    card = await start_review(session, user, "Security")
    assert card.word.topic == "Security"


async def test_tie_break_last_reviewed_then_number(session, user):
    now = utcnow()
    w_old = await make_word(session, user, 5, priority=80, last_reviewed_at=now - timedelta(days=2))
    w_new = await make_word(session, user, 1, priority=80, last_reviewed_at=now)
    w_never_a = await make_word(session, user, 3, priority=80)  # NULL — раньше всех
    w_never_b = await make_word(session, user, 4, priority=80)
    candidates = await select_candidates(session, user, None)
    assert [w.id for w in candidates] == [w_never_a.id, w_never_b.id, w_old.id, w_new.id]


async def test_selection_only_own_cards(session, user, other_user):
    await make_word(session, other_user, 1, priority=100)
    assert await select_candidates(session, user, None) == []


async def test_new_card_gets_priority_100(session, user):
    word = await add_word(
        session, user, "idempotency", "повторная обработка не меняет результат", None
    )
    assert word.priority == 100
    assert word.recall_streak == 0
