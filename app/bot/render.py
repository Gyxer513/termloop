"""Рендер карточек. Весь пользовательский текст экранируется под HTML parse mode."""

import html

from aiogram.types import InlineKeyboardMarkup

from app.bot.keyboards import answer_kb, question_kb
from app.models import Word
from app.services.review import STATE_QUESTION, AnswerResult, ReviewCard


def esc(text: str) -> str:
    return html.escape(text, quote=False)


def render_question(word: Word) -> str:
    lines = []
    if word.topic:
        lines.append(f"📂 {esc(word.topic)}")
    lines += [f"🧠 <b>{esc(word.term)}</b>", "", "Вспомни определение, затем открой ответ."]
    return "\n".join(lines)


def render_answer(word: Word) -> str:
    lines = []
    if word.topic:
        lines.append(f"📂 {esc(word.topic)}")
    lines += [f"🧠 <b>{esc(word.term)}</b>", "", esc(word.definition), "", "Получилось вспомнить?"]
    return "\n".join(lines)


def render_result(result: AnswerResult) -> str:
    if result.remembered:
        return (
            f"✅ Помню: <b>{esc(result.word.term)}</b>\n"
            f"Приоритет {result.old_priority} → {result.new_priority}, "
            f"серия {result.streak}.\n\n/go — следующая карточка"
        )
    return (
        f"🔁 Не помню: <b>{esc(result.word.term)}</b>\n"
        f"Приоритет снова 100, серия сброшена.\n\n/go — следующая карточка"
    )


def card_message(card: ReviewCard) -> tuple[str, InlineKeyboardMarkup]:
    if card.state == STATE_QUESTION:
        return render_question(card.word), question_kb(card.word.id, card.token)
    return render_answer(card.word), answer_kb(card.word.id, card.token)
