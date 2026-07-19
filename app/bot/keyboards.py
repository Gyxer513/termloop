from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


class ReviewCb(CallbackData, prefix="rv"):
    action: str  # show | yes | no
    word_id: int
    token: str


def question_kb(word_id: int, token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="👁 Показать определение",
        callback_data=ReviewCb(action="show", word_id=word_id, token=token),
    )
    return kb.as_markup()


def answer_kb(word_id: int, token: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Помню", callback_data=ReviewCb(action="yes", word_id=word_id, token=token))
    kb.button(text="❌ Не помню", callback_data=ReviewCb(action="no", word_id=word_id, token=token))
    kb.adjust(2)
    return kb.as_markup()
