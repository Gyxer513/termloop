from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.util import utcnow


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Telegram ID отделён от внутреннего ID: доменная модель не зависит от identity provider.
    telegram_user_id: Mapped[int] = mapped_column(sa.BigInteger, nullable=False, unique=True)
    notifications_enabled: Mapped[bool] = mapped_column(
        nullable=False, default=True, server_default=sa.true()
    )
    # Не более одной активной попытки на пользователя — pending живёт прямо в users.
    # Без FK на words: избегаем циклической зависимости таблиц; валидация — в сервисе.
    pending_word_id: Mapped[int | None] = mapped_column(nullable=True)
    pending_review_token: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    pending_state: Mapped[str | None] = mapped_column(sa.String(16), nullable=True)
    pending_since: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(nullable=False)
    term: Mapped[str] = mapped_column(sa.String(200), nullable=False)
    definition: Mapped[str] = mapped_column(sa.String(2000), nullable=False)
    topic: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    priority: Mapped[int] = mapped_column(nullable=False, default=100, server_default="100")
    recall_streak: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    review_count: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    last_reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(nullable=False, default=utcnow, onupdate=utcnow)

    __table_args__ = (
        sa.UniqueConstraint("user_id", "number", name="uq_words_user_number"),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_words_priority_range"),
        sa.CheckConstraint("recall_streak >= 0", name="ck_words_streak_nonneg"),
        sa.CheckConstraint("length(trim(term)) > 0", name="ck_words_term_not_empty"),
        sa.CheckConstraint("length(trim(definition)) > 0", name="ck_words_definition_not_empty"),
        sa.Index(
            "ix_words_selection",
            "user_id",
            "topic",
            sa.text("priority DESC"),
            "last_reviewed_at",
            "number",
        ),
    )
