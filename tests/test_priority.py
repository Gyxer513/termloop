from app.priority import apply_answer


def test_first_remember_decreases_by_one():
    assert apply_answer(100, 0, remembered=True) == (99, 1)


def test_degradation_sequence():
    priority, streak = 100, 0
    priority, streak = apply_answer(priority, streak, True)
    assert (priority, streak) == (99, 1)
    priority, streak = apply_answer(priority, streak, True)
    assert (priority, streak) == (89, 2)
    priority, streak = apply_answer(priority, streak, True)
    assert (priority, streak) == (64, 3)
    priority, streak = apply_answer(priority, streak, True)
    assert (priority, streak) == (14, 4)
    priority, streak = apply_answer(priority, streak, True)
    assert (priority, streak) == (0, 5)  # не уходит ниже нуля


def test_forget_resets_to_max_and_clears_streak():
    assert apply_answer(14, 4, remembered=False) == (100, 0)


def test_priority_stays_in_bounds():
    assert apply_answer(0, 10, remembered=True) == (0, 11)
    assert apply_answer(100, 0, remembered=False) == (100, 0)
