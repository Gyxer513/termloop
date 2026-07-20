# 🧠 TermLoop

> Термины возвращаются, пока не запомнишь.

Минимальный Telegram-бот интервального повторения профессиональных терминов —
плюс MCP-сервер, чтобы записывать термины в словарь прямо из разговора с LLM
(Claude Code, Claude Desktop или любой другой клиент
[MCP](https://modelcontextprotocol.io)).

[English documentation](index.md) · [MCP](mcp.md) · [архитектура](design.md)

## Зачем

Проблема редко в отсутствии инженерного понимания — чаще профессиональная
терминология отстаёт от концепций, которыми ты уже пользуешься на практике.
Ты знаешь, что «повторная обработка не должна менять результат»; TermLoop
следит, чтобы слово *idempotency* возвращалось, пока связь не закрепится.

Без AI-проверки и расхода токенов: ты оцениваешь себя сам двумя кнопками,
арифметика приоритетов детерминированная.

## Возможности

- Личные словари карточек «термин — определение» с необязательной темой
- Приоритетная ротация: новое и забытое возвращается чаще
  (100 → декременты 1/10/25/50 по серии «Помню»; «Не помню» возвращает 100)
- Цикл самопроверки: термин → вспоминаешь → определение → «Помню / Не помню»
- Повторение вручную (`/go [тема]`) и общее расписание напоминаний
- MCP-сервер (streamable HTTP): `add_term` / `list_terms` /
  `list_terms_topics` — запись терминов из любого LLM-чата
- Живучесть по конструкции: state machine с одноразовыми review-токенами и
  TTL, идемпотентные callback, ownership на уровне строк в каждом запросе,
  rate limit, необязательный allowlist Telegram ID
- Скучная эксплуатация: один процесс, long polling (без публичного
  endpoint), SQLite WAL, миграции Alembic, Docker Compose

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | создать аккаунт, показать справку |
| `/add Тема \| Термин \| Определение` | добавить карточку (тема необязательна) |
| `/edit 17 \| Тема \| Термин \| Определение` | изменить карточку №17 |
| `/delete 17` | удалить карточку №17 |
| `/list [тема]` | список карточек |
| `/topics` | список тем |
| `/go [тема]` | начать или продолжить повторение |
| `/notify on\|off` | напоминания |
| `/cancel` | сбросить активную попытку |

## Быстрый старт

Нужны Docker + Compose и токен бота от
[@BotFather](https://t.me/BotFather).

```bash
git clone https://github.com/Gyxer513/termloop.git
cd termloop
mkdir -p data && sudo chown 1000:1000 data   # контейнер работает от uid 1000
cp .env.example .env
# вписать BOT_TOKEN, MCP_TELEGRAM_USER_ID, MCP_AUTH_TOKEN
docker compose up -d --build
```

Конфигурация (`.env`):

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `BOT_TOKEN` | — | токен Telegram-бота (обязательно) |
| `REVIEW_TIMES` | `10:00,19:00` | общее расписание напоминаний |
| `TIMEZONE` | `Europe/Moscow` | часовой пояс расписания |
| `PENDING_TTL_MINUTES` | `30` | TTL активной попытки |
| `ALLOWED_TELEGRAM_IDS` | пусто | allowlist (пусто = пускать всех) |
| `MCP_TELEGRAM_USER_ID` | — | чей словарь пополняет MCP (обязательно для MCP) |
| `MCP_AUTH_TOKEN` | пусто | Bearer-токен MCP-эндпоинта |
| `MCP_PORT` | `8210` | порт MCP-сервера |

## MCP: термины из разговора с LLM

Сервис `termloop-mcp` отдаёт словарь на `http://<host>:8210/mcp`
(streamable HTTP, bearer-аутентификация). Карточки попадают в ту же
ротацию, что и у бота.

Claude Code:

```bash
claude mcp add --transport http termloop http://<host>:8210/mcp \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

Claude Desktop (`claude_desktop_config.json`, через локальный мост
`mcp-remote` — коннекторам на claude.ai нужен публичный HTTPS):

```json
"termloop": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "http://<host>:8210/mcp",
           "--allow-http", "--header", "Authorization:${AUTH_HEADER}"],
  "env": { "AUTH_HEADER": "Bearer <MCP_AUTH_TOKEN>" }
}
```

Дальше просто говоришь: *«запиши в термлуп: bulkhead — изоляция ресурсов,
чтобы отказ одного компонента не утянул остальные, тема Architecture»*.

## Разработка

Python 3.12+, внешние сервисы не нужны:

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest          # 34 теста: приоритеты, state machine, ownership, scheduler, миграции
ruff check .
```

Стек: [aiogram 3](https://github.com/aiogram/aiogram) ·
SQLAlchemy 2 (async) · Alembic · APScheduler ·
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) ·
SQLite (WAL).

Структура: доменная логика в `app/services/` (~280 строк, целиком покрыта
тестами), Telegram-обвязка в `app/bot/`, MCP-сервер в `app/mcp_server.py`.

## Архитектурные заметки

- Оба триггера — `/go` и scheduler — вызывают один application service
  `start_review(user, topic, source)`.
- Выбор карточки: top-10 по приоритету с детерминированными tie-break,
  случайный выбор в приложении. Никакого `ORDER BY RANDOM()`.
- State machine повторения: `IDLE → QUESTION_SHOWN → ANSWER_SHOWN → IDLE`
  под защитой случайного токена попытки; протухший или повторный callback —
  безопасный no-op.
- Авторизация построчная и живёт в самих запросах: чужая карточка
  неотличима от несуществующей.
- Stop rule — часть спеки: ни AI-проверки, ни web UI, ни тегов, ни
  аналитики, пока реальное использование их не потребует.

## Вопросы и обратная связь

Вопросы — в [Discussions (Q&A)](https://github.com/Gyxer513/termloop/discussions),
баги — в [Issues](https://github.com/Gyxer513/termloop/issues).

## Лицензия

[MIT](https://github.com/Gyxer513/termloop/blob/master/LICENSE)
