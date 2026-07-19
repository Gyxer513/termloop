"""users and words

Revision ID: 0001
Revises:
Create Date: 2026-07-19

"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "notifications_enabled", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("pending_word_id", sa.Integer(), nullable=True),
        sa.Column("pending_review_token", sa.String(length=32), nullable=True),
        sa.Column("pending_state", sa.String(length=16), nullable=True),
        sa.Column("pending_since", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("telegram_user_id", name="uq_users_telegram_user_id"),
    )
    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("term", sa.String(length=200), nullable=False),
        sa.Column("definition", sa.String(length=2000), nullable=False),
        sa.Column("topic", sa.String(length=50), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("recall_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("review_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "number", name="uq_words_user_number"),
        sa.CheckConstraint("priority BETWEEN 0 AND 100", name="ck_words_priority_range"),
        sa.CheckConstraint("recall_streak >= 0", name="ck_words_streak_nonneg"),
        sa.CheckConstraint("length(trim(term)) > 0", name="ck_words_term_not_empty"),
        sa.CheckConstraint(
            "length(trim(definition)) > 0", name="ck_words_definition_not_empty"
        ),
    )
    op.create_index(
        "ix_words_selection",
        "words",
        ["user_id", "topic", sa.text("priority DESC"), "last_reviewed_at", "number"],
    )


def downgrade() -> None:
    op.drop_index("ix_words_selection", table_name="words")
    op.drop_table("words")
    op.drop_table("users")
