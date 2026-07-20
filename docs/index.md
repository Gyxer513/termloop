# TermLoop

> Terms keep coming back until you remember them.

A minimal Telegram bot for spaced repetition of professional terminology —
plus an MCP server, so you can save terms into your dictionary right from a
conversation with an LLM. See [MCP integration](mcp.md) and
[design notes](design.md); документация [по-русски](README.ru.md).

## Why

The problem is rarely a lack of engineering understanding — it's that
professional vocabulary lags behind the concepts you already use in practice.
You know that "reprocessing must not change the result"; TermLoop makes sure
the word *idempotency* comes back to you until the link sticks.

No AI grading, no token spend: you judge yourself with two buttons,
the priority math is deterministic.

## Review loop

1. The bot shows a term.
2. You try to recall the definition.
3. You reveal the stored definition.
4. You judge yourself: **Remember** or **Forgot**.
5. Priority and recall streak are recalculated deterministically:
   new cards start at 100, consecutive "Remember" answers decrement priority
   by 1 / 10 / 25 / 50, "Forgot" resets it to 100.
6. The next card is a random pick from your top-10 highest-priority cards.

Reviews start manually (`/go [topic]`) or on a shared notification schedule —
both paths call the same application service.

## Bot commands

| Command | Action |
|---|---|
| `/start` | create account, show help |
| `/add Topic \| Term \| Definition` | add a card (topic is optional) |
| `/edit 17 \| Topic \| Term \| Definition` | edit card #17 |
| `/delete 17` | delete card #17 |
| `/list [topic]` | list your cards |
| `/topics` | list topics |
| `/go [topic]` | start or resume a review |
| `/notify on\|off` | toggle reminders |
| `/cancel` | reset the active attempt |

## Quick start

Requirements: Docker + Compose, a bot token from
[@BotFather](https://t.me/BotFather).

```bash
git clone https://github.com/Gyxer513/termloop.git
cd termloop
mkdir -p data && sudo chown 1000:1000 data   # container runs as uid 1000
cp .env.example .env
# set BOT_TOKEN, MCP_TELEGRAM_USER_ID, MCP_AUTH_TOKEN in .env
docker compose up -d --build
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `BOT_TOKEN` | — | Telegram bot token (required) |
| `REVIEW_TIMES` | `10:00,19:00` | shared reminder schedule |
| `TIMEZONE` | `Europe/Moscow` | schedule timezone |
| `PENDING_TTL_MINUTES` | `30` | active attempt expiry |
| `ALLOWED_TELEGRAM_IDS` | empty | optional allowlist (empty = everyone) |
| `MCP_TELEGRAM_USER_ID` | — | whose dictionary MCP tools write to (required for MCP) |
| `MCP_AUTH_TOKEN` | empty | static bearer token for the MCP endpoint |
| `MCP_PORT` | `8210` | MCP server port |

## Operations

- All state lives in one SQLite file (WAL) under `./data` — a bind mount that
  fits any host-level backup or VM snapshot strategy.
- Long polling: no public endpoint, nothing to reverse-proxy.
- Alembic migrations run automatically on container start.
- Designed for basic durability and disaster recovery without high
  availability: one process, `restart: unless-stopped`, daily snapshots.
