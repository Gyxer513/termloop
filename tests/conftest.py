import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import Base, User, Word


@pytest.fixture
async def engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(session_factory):
    async with session_factory() as session:
        yield session


@pytest.fixture
async def user(session):
    user = User(telegram_user_id=111)
    session.add(user)
    await session.flush()
    return user


@pytest.fixture
async def other_user(session):
    user = User(telegram_user_id=222)
    session.add(user)
    await session.flush()
    return user


async def make_word(session, user, number, term="term", definition="def", **kwargs):
    word = Word(
        user_id=user.id, number=number, term=term, definition=definition, **kwargs
    )
    session.add(word)
    await session.flush()
    return word
