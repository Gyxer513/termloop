# 🧠 TermLoop

> Terms keep coming back until you remember them.

A minimal Telegram bot for spaced repetition of professional terminology —
plus an MCP server, so you can save terms into your dictionary right from a
conversation with an LLM (Claude Code, Claude Desktop, or anything else that
speaks [MCP](https://modelcontextprotocol.io)).

**Docs:** [gyxer513.github.io/termloop](https://gyxer513.github.io/termloop/) · [Документация на русском](docs/README.ru.md)

## Why

The problem is rarely a lack of engineering understanding — it's that
professional vocabulary lags behind the concepts you already use in practice.
You know that "reprocessing must not change the result"; TermLoop makes sure
the word *idempotency* comes back to you until the link sticks.

No AI grading, no token spend: you judge yourself with two buttons,
the priority math is deterministic.

## Features

- Personal card dictionaries (term — definition, optional topic)
- Priority rotation: new and forgotten cards come back more often
  (100 → decrements of 1/10/25/50 per recall streak; "forgot" resets to 100)
- Self-assessment flow: show term → recall → reveal definition → Remember /
  Forgot
- Manual reviews (`/go [topic]`) and a shared notification schedule
- MCP server (streamable HTTP) with `add_term` / `list_terms` /
  `list_terms_topics` — write terms from any LLM chat
- Sturdy by design: state machine with single-use review tokens and TTL,
  idempotent callbacks, row-level ownership in every query, rate limiting,
  optional Telegram ID allowlist
- Boring ops: single process, long polling (no public endpoint), SQLite WAL,
  Alembic migrations, Docker Compose

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

Configuration (`.env`):

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

## MCP: save terms from an LLM conversation

The `termloop-mcp` service exposes the dictionary at `http://<host>:8210/mcp`
(streamable HTTP, bearer auth). Cards land in the same rotation the bot uses.

Claude Code:

```bash
claude mcp add --transport http termloop http://<host>:8210/mcp \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

Claude Desktop (`claude_desktop_config.json`, via a local `mcp-remote`
bridge — connectors on claude.ai itself require a public HTTPS URL):

```json
"termloop": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "http://<host>:8210/mcp",
           "--allow-http", "--header", "Authorization:${AUTH_HEADER}"],
  "env": { "AUTH_HEADER": "Bearer <MCP_AUTH_TOKEN>" }
}
```

Then just say: *"save to termloop: bulkhead — resource isolation so one
failing component can't take down the rest, topic Architecture."*

## Development

Python 3.12+, no external services needed:

```bash
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest          # 34 tests: priority policy, state machine, ownership, scheduler, migrations
ruff check .
```

Stack: [aiogram 3](https://github.com/aiogram/aiogram) ·
SQLAlchemy 2 (async) · Alembic · APScheduler ·
[MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) ·
SQLite (WAL).

Layout: domain logic lives in `app/services/` (~280 lines, fully covered by
tests), Telegram wiring in `app/bot/`, the MCP server in `app/mcp_server.py`.

## Design notes

- Both triggers — `/go` and the scheduler — call the same
  `start_review(user, topic, source)` application service.
- Card selection: top-10 by priority with deterministic tie-breaks, random
  pick in the application. No `ORDER BY RANDOM()`.
- Review state machine: `IDLE → QUESTION_SHOWN → ANSWER_SHOWN → IDLE`,
  guarded by a per-attempt random token; stale or replayed callbacks are
  safe no-ops.
- Authorization is row-level and lives in the queries themselves: a foreign
  card is indistinguishable from a missing one.
- The stop rule is part of the spec: no AI grading, no web UI, no tag system,
  no analytics until real usage demands them.

## Questions & feedback

Ask in [Discussions (Q&A)](https://github.com/Gyxer513/termloop/discussions) —
bugs go to [Issues](https://github.com/Gyxer513/termloop/issues).

## License

[MIT](LICENSE)
