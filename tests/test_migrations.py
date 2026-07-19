from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config as AlembicConfig

from alembic import command

ROOT = Path(__file__).resolve().parents[1]


def test_migrations_apply_on_clean_db(tmp_path, monkeypatch):
    db_path = tmp_path / "clean.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db_path.as_posix()}")

    cfg = AlembicConfig(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    command.upgrade(cfg, "head")

    engine = sa.create_engine(f"sqlite:///{db_path.as_posix()}")
    inspector = sa.inspect(engine)
    assert {"users", "words"} <= set(inspector.get_table_names())
    index_names = {ix["name"] for ix in inspector.get_indexes("words")}
    assert "ix_words_selection" in index_names
    engine.dispose()
