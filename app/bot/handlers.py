import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app.bot import texts
from app.bot.keyboards import ReviewCb, answer_kb
from app.bot.render import card_message, esc, render_answer, render_result
from app.config import Config
from app.services.review import (
    clear_pending,
    show_definition,
    start_review,
    submit_answer,
)
from app.services.users import get_or_create_user, get_user, set_notifications
from app.services.words import add_word, delete_word, edit_word, list_topics, list_words
from app.validation import validate_card_fields

logger = logging.getLogger(__name__)
router = Router()

MAX_MESSAGE_LEN = 4000


def _parse_parts(raw: str) -> list[str]:
    return [part.strip() for part in raw.split("|")]


def _extract_card_fields(parts: list[str]) -> tuple[str | None, str, str] | None:
    """[term, def] или [topic, term, def] → (topic, term, definition)."""
    if len(parts) == 2:
        return None, parts[0], parts[1]
    if len(parts) == 3:
        topic = parts[0] or None
        return topic, parts[1], parts[2]
    return None


@router.message(Command("start", "help"))
async def cmd_start(message: Message, session) -> None:
    is_new = await get_user(session, message.from_user.id) is None
    await get_or_create_user(session, message.from_user.id)
    if is_new:
        await message.answer(texts.GREETING)
    await message.answer(texts.HELP)


@router.message(Command("add"))
async def cmd_add(message: Message, command: CommandObject, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    if not command.args:
        await message.answer(texts.USAGE_ADD)
        return
    fields = _extract_card_fields(_parse_parts(command.args))
    if fields is None:
        await message.answer(texts.USAGE_ADD)
        return
    topic, term, definition = fields
    error = validate_card_fields(term, definition, topic)
    if error:
        await message.answer(error)
        return
    word = await add_word(session, user, term, definition, topic)
    await message.answer(f"Добавлено: №{word.number} — <b>{esc(word.term)}</b>")


@router.message(Command("edit"))
async def cmd_edit(message: Message, command: CommandObject, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    parts = _parse_parts(command.args or "")
    if len(parts) not in (3, 4) or not parts[0].isdigit():
        await message.answer(texts.USAGE_EDIT)
        return
    number = int(parts[0])
    if not (1 <= number <= 10**9):
        await message.answer(texts.USAGE_EDIT)
        return
    fields = _extract_card_fields(parts[1:])
    if fields is None:
        await message.answer(texts.USAGE_EDIT)
        return
    topic, term, definition = fields
    error = validate_card_fields(term, definition, topic)
    if error:
        await message.answer(error)
        return
    word = await edit_word(session, user, number, term, definition, topic)
    if word is None:
        await message.answer(texts.CARD_NOT_FOUND.format(number=number))
        return
    await message.answer(f"Обновлено: №{word.number} — <b>{esc(word.term)}</b>")


@router.message(Command("delete"))
async def cmd_delete(message: Message, command: CommandObject, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    arg = (command.args or "").strip()
    if not arg.isdigit():
        await message.answer(texts.USAGE_DELETE)
        return
    number = int(arg)
    if await delete_word(session, user, number):
        await message.answer(f"Карточка №{number} удалена.")
    else:
        await message.answer(texts.CARD_NOT_FOUND.format(number=number))


@router.message(Command("list"))
async def cmd_list(message: Message, command: CommandObject, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    topic = (command.args or "").strip() or None
    words = await list_words(session, user, topic)
    if not words:
        text = texts.NO_CARDS_TOPIC.format(topic=esc(topic)) if topic else texts.NO_CARDS
        await message.answer(text)
        return
    lines = []
    for w in words:
        prefix = f"[{esc(w.topic)}] " if w.topic else ""
        definition = w.definition if len(w.definition) <= 80 else w.definition[:77] + "…"
        lines.append(
            f"<b>№{w.number}</b> {prefix}{esc(w.term)} — {esc(definition)} (prio {w.priority})"
        )
    # Telegram ограничивает сообщение 4096 символами — режем на части.
    chunk: list[str] = []
    size = 0
    for line in lines:
        if size + len(line) + 1 > MAX_MESSAGE_LEN and chunk:
            await message.answer("\n".join(chunk))
            chunk, size = [], 0
        chunk.append(line)
        size += len(line) + 1
    if chunk:
        await message.answer("\n".join(chunk))


@router.message(Command("topics"))
async def cmd_topics(message: Message, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    topics = await list_topics(session, user)
    if not topics:
        await message.answer("Тем пока нет. Тема указывается при добавлении карточки.")
        return
    lines = [f"📂 {esc(topic)} — {count}" for topic, count in topics]
    await message.answer("\n".join(lines))


@router.message(Command("go"))
async def cmd_go(message: Message, command: CommandObject, session, config: Config) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    topic = (command.args or "").strip() or None
    card = await start_review(session, user, topic, source="manual", ttl=config.pending_ttl)
    if card is None:
        text = texts.NO_CARDS_TOPIC.format(topic=esc(topic)) if topic else texts.NO_CARDS
        await message.answer(text)
        return
    text, markup = card_message(card)
    await message.answer(text, reply_markup=markup)


@router.message(Command("notify"))
async def cmd_notify(message: Message, command: CommandObject, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    arg = (command.args or "").strip().lower()
    if arg not in ("on", "off"):
        await message.answer(texts.USAGE_NOTIFY)
        return
    set_notifications(user, arg == "on")
    await message.answer(texts.NOTIFY_ON if arg == "on" else texts.NOTIFY_OFF)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, session) -> None:
    user = await get_or_create_user(session, message.from_user.id)
    if user.pending_word_id is None:
        await message.answer(texts.NOTHING_TO_CANCEL)
        return
    clear_pending(user)
    await message.answer(texts.CANCELLED)


@router.callback_query(ReviewCb.filter(F.action == "show"))
async def cb_show(
    callback: CallbackQuery, callback_data: ReviewCb, session, config: Config
) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    word = await show_definition(
        session, user, callback_data.word_id, callback_data.token, ttl=config.pending_ttl
    )
    if word is None:
        await callback.answer(texts.CARD_STALE)
        return
    try:
        await callback.message.edit_text(
            render_answer(word), reply_markup=answer_kb(word.id, callback_data.token)
        )
    except TelegramBadRequest:
        pass  # двойной тап: сообщение уже в этом состоянии
    await callback.answer()


@router.callback_query(ReviewCb.filter(F.action.in_({"yes", "no"})))
async def cb_answer(
    callback: CallbackQuery, callback_data: ReviewCb, session, config: Config
) -> None:
    user = await get_or_create_user(session, callback.from_user.id)
    result = await submit_answer(
        session,
        user,
        callback_data.word_id,
        callback_data.token,
        remembered=callback_data.action == "yes",
        ttl=config.pending_ttl,
    )
    if result is None:
        await callback.answer(texts.CARD_STALE)
        return
    try:
        await callback.message.edit_text(render_result(result))
    except TelegramBadRequest:
        pass
    await callback.answer("Записано")
