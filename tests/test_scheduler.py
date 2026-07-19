from datetime import timedelta

from app.config import Config
from app.scheduler import send_scheduled_reviews
from tests.conftest import make_word


def _config() -> Config:
    return Config(
        bot_token="test",
        database_url="sqlite+aiosqlite://",
        timezone="Europe/Moscow",
        review_times=((10, 0),),
        pending_ttl=timedelta(minutes=30),
        allowed_telegram_ids=frozenset(),
        scheduler_concurrency=2,
    )


class FakeBot:
    def __init__(self, fail_chat_ids=()):
        self.sent: list[int] = []
        self.fail_chat_ids = set(fail_chat_ids)

    async def send_message(self, chat_id, text, reply_markup=None):
        if chat_id in self.fail_chat_ids:
            raise RuntimeError("telegram unavailable")
        self.sent.append(chat_id)


async def test_one_user_error_does_not_stop_others(session_factory):
    from app.models import User

    async with session_factory() as session:
        good1 = User(telegram_user_id=1001)
        bad = User(telegram_user_id=1002)
        good2 = User(telegram_user_id=1003)
        disabled = User(telegram_user_id=1004, notifications_enabled=False)
        session.add_all([good1, bad, good2, disabled])
        await session.flush()
        for u in (good1, bad, good2, disabled):
            await make_word(session, u, 1)
        await session.commit()

    bot = FakeBot(fail_chat_ids={1002})
    await send_scheduled_reviews(bot, session_factory, _config())
    assert sorted(bot.sent) == [1001, 1003]

    # у обработанных пользователей появилась pending review, у выключенного — нет
    from sqlalchemy import select

    from app.models import User as U

    async with session_factory() as session:
        users = {u.telegram_user_id: u for u in (await session.scalars(select(U))).all()}
        assert users[1001].pending_word_id is not None
        assert users[1003].pending_word_id is not None
        assert users[1004].pending_word_id is None


async def test_scheduler_reuses_existing_pending(session_factory):
    from app.models import User
    from app.services.review import start_review

    async with session_factory() as session:
        u = User(telegram_user_id=2001)
        session.add(u)
        await session.flush()
        await make_word(session, u, 1)
        card = await start_review(session, u, source="manual")
        await session.commit()
        pending_id, pending_token = u.pending_word_id, u.pending_review_token
        assert card is not None

    bot = FakeBot()
    await send_scheduled_reviews(bot, session_factory, _config())
    assert bot.sent == [2001]  # напомнил про ту же карточку

    from sqlalchemy import select

    from app.models import User as U

    async with session_factory() as session:
        u = await session.scalar(select(U).where(U.telegram_user_id == 2001))
        assert u.pending_word_id == pending_id
        assert u.pending_review_token == pending_token
