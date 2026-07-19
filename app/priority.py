"""Priority policy v1: детерминированная, без модели данных под будущие коэффициенты.

100 — карточка максимально приоритетна, 0 — хорошо закреплена.
"""

MAX_PRIORITY = 100
MIN_PRIORITY = 0

_DECREMENTS = {1: 1, 2: 10, 3: 25}
_DEFAULT_DECREMENT = 50


def apply_answer(priority: int, recall_streak: int, remembered: bool) -> tuple[int, int]:
    """Возвращает (new_priority, new_streak)."""
    if not remembered:
        return MAX_PRIORITY, 0
    new_streak = recall_streak + 1
    decrement = _DECREMENTS.get(new_streak, _DEFAULT_DECREMENT)
    return max(MIN_PRIORITY, priority - decrement), new_streak
