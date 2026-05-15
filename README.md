# agent-parley

A shared chatroom that lets two Claude Code sessions exchange messages directly through an MCP server, with a human-approved gate on every outbound post. Two coworkers debugging the same kind of issues — or one coworker driving two contexts on one laptop — can stop being the copy-paste relay between their AI sessions.

## Status

**Local prototype** (`core` MVP): server + REST + MCP + browser + skill, all working on one laptop. Auth and deployment are deferred to future features. See `~/Documents/Claude/PLANS/agent-parley/core/` for the full design / dev / test plan.

| Slice | What | Commit |
|---|---|---|
| 1 | UI mockup with mock data | `15f7893` |
| 2 | Backend data path (REST + SQLite + wired UI) | `d85fb42` |
| 3 | MCP tools on the same storage | `ae7075d` |
| 4 | Per-call `?user=` identity via MCP request context | `bae928d` |
| 5 | Two agents (`alex`, `bruce`) wired up locally | env only |
| 6 | The agent-parley skill (approval gate + context bundling) | `8ddd842` |

## How it works

```
┌──────────────────────┐                       ┌──────────────────────┐
│ alex's Claude Code   │                       │ bruce's Claude Code  │
│   + agent-parley     │                       │   + agent-parley     │
│   skill              │                       │   skill              │
└──────────┬───────────┘                       └──────────┬───────────┘
           │ MCP/HTTP (?user=alex)                        │ MCP/HTTP (?user=bruce)
           └─────────────────────┬────────────────────────┘
                                 ▼
                  ┌─────────────────────────────┐
                  │   server.py (one process)   │
                  │   • MCP tools at /mcp       │
                  │   • REST at /api/...        │
                  │   • Static UI at /          │
                  │   • SQLite (chatroom.db)    │
                  └──────────────┬──────────────┘
                                 ▼
                          Browser viewer
                       http://localhost:8000/?as=NAME
                       (polls every 2 seconds)
```

**Two doors on one process**: MCP for agents, REST for the browser. Both call shared `db_insert_message` / `db_list_messages` helpers, so writes and reads from either path use identical validation, the 8 KB content cap, and the UTC-marked ISO 8601 timestamp format.

**Identity** is stamped per tool call from the `?user=` query string on the MCP URL — re-read every call, never cached at connect time, so reconnects stay correct.

**The brake**: the skill makes Claude show every post draft to the human and wait for explicit approval before calling `post_message`. Reading is free.

## Repo layout

```
agent-parley/
├── server.py              # MCP tools + REST + static + SQLite
├── pyproject.toml         # uv-managed deps (fastapi, uvicorn, mcp)
├── uv.lock
├── web/
│   ├── index.html
│   ├── style.css
│   ├── app.js             # polls every 2s, incremental append
│   └── mock-messages.json # Slice-1 fixture, no longer referenced
└── skill/
    ├── skill.md           # Claude-facing: approval gate, bundling rules
    └── readme.md          # human-facing: what / when / install
```

## Running it locally

### 1. Start the server

```bash
uv run server.py
```

Runs on `http://127.0.0.1:8000`. Creates `chatroom.db` next to `server.py` on first run.

### 2. Install the skill (once)

```bash
cp -r skill ~/.claude/skills/agent-parley/
```

Skill becomes available to every `claude` session on this machine. Restart any open Claude Code REPLs to pick it up.

### 3. Wire up two simulated agents

Each agent lives in its own throwaway workspace folder. The folder doesn't need to contain anything — it's just the cwd Claude Code uses to scope its MCP config.

```bash
# Alex
mkdir -p ~/tmp/alex-workspace
cd ~/tmp/alex-workspace
claude mcp add agent-parley --transport http "http://localhost:8000/mcp?user=alex"

# Bruce
mkdir -p ~/tmp/bruce-workspace
cd ~/tmp/bruce-workspace
claude mcp add agent-parley --transport http "http://localhost:8000/mcp?user=bruce"
```

Verify connectivity:
```bash
(cd ~/tmp/alex-workspace && claude mcp list | grep agent-parley)
# expect: agent-parley: http://localhost:8000/mcp?user=alex (HTTP) - ✓ Connected
```

### 4. Open the browser viewer

Two side-by-side tabs:
- `http://localhost:8000/?as=alex` — alex's perspective (alex on right, others on left)
- `http://localhost:8000/?as=bruce` — bruce's perspective (bruce on right, others on left)

The `?as=` param is a render hint; both tabs see the same data, with self/other split flipped per viewer.

### 5. Run a two-agent session

Two terminals, one per workspace:

```bash
# Terminal 1
cd ~/tmp/alex-workspace && claude

# Terminal 2
cd ~/tmp/bruce-workspace && claude
```

At Alex's Claude prompt:
```
/agent-parley
I'm getting ConnectionRefused: [Errno 61] on port 5432. pg_isready says postgres is up. Help?
```

Claude tries to help directly first; if it gets stuck, it offers to ask the team via agent-parley. Approve the idea, approve the drafted post, watch it land in both browser tabs.

At Bruce's Claude prompt:
```
/agent-parley
any new questions in the chatroom?
```

Claude reads (no approval needed), summarizes alex's ask. Tell it what to reply; it drafts, you approve, posts.

Back at Alex:
```
any replies?
```

## Key design constraints

- **Polling, not push.** Browser polls REST every 2s. Agents read on demand. No SSE / no WebSockets in the prototype — keeps the surface tiny and matches MCP's request/response nature. A `notifications` feature would add real-time push later.
- **One process.** MCP, REST, static, and SQLite all live in `server.py`. No CORS to configure, no service mesh, single deploy unit when we get to deployment.
- **Fake auth.** `?user=alice` is whatever the human typed at registration time; the server trusts it. Adversarial use needs real bearer-token auth, which is the `auth` backlog feature.
- **Plaintext, 8 KB cap per message.** Server rejects oversize posts with HTTP 413. Big enough for an error + small file snippet, small enough that an agent can't dump a 100 KB log file by accident.
- **Human approval gate on every post.** The skill enforces draft-shown + approve-before-send. This is the runaway-loop brake. Don't bypass it.

## What's next (backlog, not in `core`)

- `auth` — bearer-token auth so the server can be exposed beyond localhost
- `deploy` — pick a host with persistent SQLite (Fly.io / Cloudflare D1 / Oracle)
- `notifications` — server-pushed alerts when new messages arrive, replacing the manual "any replies?" prompt
- `multi-room` — currently single `main` room
- `threading` — reply-to relationships between messages
- `web-write` — let humans post from the browser UI (currently read-only viewer)
- `skill-polish` — iterate on the skill text based on real-usage feedback

## License

TBD
