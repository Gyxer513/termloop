# 🧠 Gyxer TermLoop

> Термины возвращаются, пока не запомнишь.

Telegram-бот для повторения профессиональных терминов: личные карточки
«термин — определение», приоритетная ротация, самопроверка кнопками
«Помню / Не помню», напоминания по общему расписанию.

Спека: Nextcloud-заметка «🧠 Gyxer TermLoop — MVP» (№116833).

## Стек

Python 3.12 · aiogram 3 · SQLAlchemy 2 (async) · Alembic · APScheduler ·
SQLite (WAL) · Docker Compose. Long polling, публичного endpoint нет.

## Команды бота

| Команда | Действие |
|---|---|
| `/start` | справка |
| `/add Тема \| Термин \| Определение` | добавить карточку (тема необязательна) |
| `/edit 17 \| Тема \| Термин \| Определение` | изменить карточку №17 |
| `/delete 17` | удалить карточку №17 |
| `/list [тема]` | список карточек |
| `/topics` | список тем |
| `/go [тема]` | начать/продолжить повторение |
| `/notify on\|off` | напоминания |
| `/cancel` | сбросить активную попытку |

## Локальная разработка (Windows/Linux)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; на Linux: source .venv/bin/activate
pip install -r requirements-dev.txt

# тесты и линт
pytest
ruff check .

# запуск (нужен BOT_TOKEN в окружении или .env, загрузка .env — вручную)
alembic upgrade head
python -m app.main
```

## Деплой на homelab (VM финтрекера, через Gitea)

Один раз:

```bash
# 1. В Gitea создать пустой репозиторий termloop, затем локально:
git remote add origin ssh://git@<gitea-host>/<owner>/termloop.git
git push -u origin master

# 2. На VM:
git clone ssh://git@<gitea-host>/<owner>/termloop.git
cd termloop
mkdir -p data && sudo chown 1000:1000 data   # контейнер работает от uid 1000
cp .env.example .env
# вписать BOT_TOKEN от @BotFather (и при желании ALLOWED_TELEGRAM_IDS)
docker compose up -d --build
docker compose logs -f
```

Обновление:

```bash
git pull && docker compose up -d --build
```

## Эксплуатация

- Всё состояние — в `./data/termloop.db` (bind mount, попадает в snapshot VM).
- Модель DR: ежедневный snapshot VM, RPO до 24 часов, HA не требуется.
- Проверка восстановления: развернуть snapshot, `docker compose up -d`,
  убедиться что `/list` показывает карточки.
- Расписание напоминаний общее для всех: `REVIEW_TIMES` + `TIMEZONE` в `.env`.
- Незавершённая попытка протухает через `PENDING_TTL_MINUTES` (30 по умолчанию).

## Stop rule

MVP закончен, когда пользователь может вести словарь, повторять карточки
вручную и по расписанию, а состояние переживает рестарт. Дальше — ничего
(AI-проверка, web UI, теги, аналитика), пока реальное использование не
покажет конкретную потребность.
