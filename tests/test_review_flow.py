from datetime import timedelta

from app.services.review import (
    STATE_ANSWER,
    STATE_QUESTION,
    show_definition,
    start_review,
    submit_answer,
)
from app.util import utcnow
from tests.conftest import make_word

TTL = timedelta(minutes=30)


async def test_go_creates_pending(session, user):
    word = await make_word(session, user, 1)
    card = await start_review(session, user)
    assert card is not None
    assert card.word.id == word.id
    assert card.state == STATE_QUESTION
    assert user.pending_word_id == word.id
    assert user.pending_review_token == card.token
    assert user.pending_since is not None


async def test_repeated_go_returns_same_card(session, user):
    await make_word(session, user, 1)
    await make_word(session, user, 2)
    first = await start_review(session, user)
    second = await start_review(session, user)
    assert second.word.id == first.word.id
    assert second.token == first.token


async def test_no_cards_returns_none(session, user):
    assert await start_review(session, user) is None


async def test_answer_before_definition_rejected(session, user):
    await make_word(session, user, 1)
    card = await start_review(session, user)
    result = await submit_answer(session, user, card.word.id, card.token, True)
    assert result is None
    assert user.pending_state == STATE_QUESTION


async def test_full_flow_updates_priority(session, user):
    word = await make_word(session, user, 1)
    card = await start_review(session, user)
    shown = await show_definition(session, user, card.word.id, card.token)
    assert shown is not None
    assert user.pending_state == STATE_ANSWER
    result = await submit_answer(session, user, card.word.id, card.token, True)
    assert result is not None
    assert (result.old_priority, result.new_priority) == (100, 99)
    assert word.recall_streak == 1
    assert word.review_count == 1
    assert word.last_reviewed_at is not None
    assert user.pending_word_id is None


async def test_double_callback_changes_priority_once(session, user):
    word = await make_word(session, user, 1)
    card = await start_review(session, user)
    await show_definition(session, user, card.word.id, card.token)
    first = await submit_answer(session, user, card.word.id, card.token, True)
    second = await submit_answer(session, user, card.word.id, card.token, True)
    assert first is not None
    assert second is None
    assert word.priority == 99
    assert word.review_count == 1


async def test_wrong_token_rejected(session, user):
    await make_word(session, user, 1)
    card = await start_review(session, user)
    assert await show_definition(session, user, card.word.id, "deadbeefdeadbeef") is None
    assert user.pending_state == STATE_QUESTION


async def test_old_token_rejected_after_new_attempt(session, user):
    await make_word(session, user, 1)
    card1 = await start_review(session, user)
    await show_definition(session, user, card1.word.id, card1.token)
    await submit_answer(session, user, card1.word.id, card1.token, True)
    card2 = await start_review(session, user)
    assert card2.token != card1.token
    assert await show_definition(session, user, card1.word.id, card1.token) is None


async def test_expired_attempt_resets(session, user):
    await make_word(session, user, 1)
    started_at = utcnow()
    card = await start_review(session, user, now=started_at)
    late = started_at + TTL + timedelta(minutes=1)
    result = await submit_answer(session, user, card.word.id, card.token, True, now=late)
    assert result is None
    assert user.pending_word_id is None
    new_card = await start_review(session, user, now=late)
    assert new_card is not None
    assert new_card.token != card.token


async def test_show_definition_is_idempotent(session, user):
    await make_word(session, user, 1)
    card = await start_review(session, user)
    first = await show_definition(session, user, card.word.id, card.token)
    second = await show_definition(session, user, card.word.id, card.token)
    assert first is not None and second is not None
    assert user.pending_state == STATE_ANSWER
