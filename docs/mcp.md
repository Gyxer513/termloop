# MCP integration

TermLoop ships a second container, `termloop-mcp`, exposing the dictionary as
an [MCP](https://modelcontextprotocol.io) server over streamable HTTP at
`http://<host>:8210/mcp`. Cards added through it land in the same rotation
the bot uses — the bot will bring them back as regular review cards.

## Tools

| Tool | Purpose |
|---|---|
| `add_term(term, definition, topic?)` | add a card to the dictionary |
| `list_terms(topic?)` | list cards, optionally filtered by topic |
| `list_terms_topics()` | list topics with card counts |

Cards are written to the account configured via `MCP_TELEGRAM_USER_ID`.
The endpoint is protected by a static bearer token (`MCP_AUTH_TOKEN`);
requests without it get `401`.

## Claude Code

```bash
claude mcp add --transport http termloop http://<host>:8210/mcp \
  --header "Authorization: Bearer <MCP_AUTH_TOKEN>"
```

Registered in user scope, the server is available in every project. Then just
say: *"save to termloop: bulkhead — resource isolation so one failing
component can't take down the rest, topic Architecture."*

## Claude Desktop

Desktop connectors are established from Anthropic's cloud, which cannot reach
a LAN address — bridge through a local [`mcp-remote`](https://www.npmjs.com/package/mcp-remote)
process instead (requires Node.js). In `claude_desktop_config.json`:

```json
"termloop": {
  "command": "npx",
  "args": ["-y", "mcp-remote", "http://<host>:8210/mcp",
           "--allow-http", "--header", "Authorization:${AUTH_HEADER}"],
  "env": { "AUTH_HEADER": "Bearer <MCP_AUTH_TOKEN>" }
}
```

!!! note
    `--allow-http` is required for non-localhost HTTP URLs, and the
    `${AUTH_HEADER}` indirection works around argument-splitting issues with
    spaces on Windows. Restart Claude Desktop fully (quit from the tray) after
    editing the config.

## claude.ai / ChatGPT

Web-based connectors require a publicly reachable HTTPS URL. Expose the
endpoint through Tailscale Funnel, Cloudflare Tunnel, or a reverse proxy with
TLS — keep the bearer token in place either way.

## Health check

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://<host>:8210/mcp
# 401 — auth is on
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://<host>:8210/mcp \
  -H "Authorization: Bearer <MCP_AUTH_TOKEN>"
# anything but 401 (a bare POST without MCP headers returns 400)
```

## Concurrency

The bot and the MCP server are separate processes writing to the same SQLite
database. WAL journaling plus a 5-second busy timeout make this safe on a
single host; both containers mount the same `./data` directory.
