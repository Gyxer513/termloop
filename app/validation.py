from app.config import DEFINITION_MAX_LEN, TERM_MAX_LEN, TOPIC_MAX_LEN


def validate_card_fields(term: str, definition: str, topic: str | None) -> str | None:
    """None — поля валидны, иначе текст ошибки для пользователя."""
    if not term or not definition:
        return "Термин и определение не могут быть пустыми."
    if len(term) > TERM_MAX_LEN:
        return f"Термин длиннее {TERM_MAX_LEN} символов."
    if len(definition) > DEFINITION_MAX_LEN:
        return f"Определение длиннее {DEFINITION_MAX_LEN} символов."
    if topic is not None and len(topic) > TOPIC_MAX_LEN:
        return f"Тема длиннее {TOPIC_MAX_LEN} символов."
    return None
