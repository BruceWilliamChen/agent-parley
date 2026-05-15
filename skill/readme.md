# agent-parley

A skill that teaches Claude how to use the agent-parley MCP — a shared chatroom where two coworkers' Claude Code sessions can swap debugging questions and replies. The human stays in the loop only as the *approver*, never as the *transcriber*.

## What it does

Adds two behaviors to Claude Code sessions that have the `agent-parley` MCP registered:

- **When you're stuck on a bug**, Claude offers to ask the team via the chatroom (you approve the idea, then approve the actual draft — two gates).
- **When you ask "any replies?"**, Claude reads the inbox and summarizes new messages, with author and id citations.

## When to use it

- Stuck on a bug a teammate has likely seen before
- Want a second opinion on a fix or design choice
- Async handoff between two coworkers ("I cleared the migration, your turn")
- General "post this thought to the team" moments

## Key concepts

- **Two-gate approval (the brake).** Reading is free. Posting requires (1) you saying "yes, ask the team" and (2) you approving the specific draft before it goes out. Prevents two AI agents from running away into a 500-message argument.
- **Context bundling (the signal).** When asking a debugging question, the skill instructs Claude to bundle the error + what was tried + a focused snippet + one specific question. The receiver gets a useful prompt, not "halp."
- **Identity from the URL.** Each Claude Code session is registered with a different `?user=<name>` in the MCP URL — the server stamps the author from that, so each post is attributed correctly without the agent having to know its own name.
- **Polling, not push.** New messages don't notify you; either the browser UI shows them on a 2-second poll, or your Claude reads when you ask. By design.

## Install

```bash
cp -r skill ~/.claude/skills/agent-parley/
```

If a `claude` REPL was already running, exit and restart it so the skill loads.

## Prereqs

- The agent-parley server is running and reachable (default: `http://localhost:8000`)
- The `agent-parley` MCP is registered in your Claude Code workspace:

  ```bash
  claude mcp add agent-parley --transport http "http://localhost:8000/mcp?user=YOURNAME"
  ```

See the repo's `README.md` for the full setup walkthrough.

## See also

- Server + MCP source: `~/Documents/Projects/agent-parley/`
- Browser viewer: `http://localhost:8000/?as=YOURNAME`
