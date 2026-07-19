from datetime import UTC, datetime


def utcnow() -> datetime:
    """Naive UTC: SQLite хранит datetime без таймзоны, вся логика — в UTC."""
    return datetime.now(UTC).replace(tzinfo=None)
