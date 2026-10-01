# OpenRouter MCP Server

A production-shaped [Model Context Protocol](https://modelcontextprotocol.io) server for
**OpenRouter**, built by **[7Block Labs](https://7blocklabs.com)**. It turns OpenRouter's API into a
first-party, agent-native surface: any MCP client (Claude, ChatGPT, Cursor, agent frameworks) can
browse the model catalog, compare pricing, pick a model by budget/context, and run completions —
metered to the caller's own key.

Built for the OpenRouter team as a working example of the official MCP server we'd ship & launch for you
(listed in Claude + ChatGPT, with OAuth + per-plan metering). Catalog tools are **keyless** (OpenRouter's
`/models` is public), so you can run it right now:

```bash
python -m venv .venv && source .venv/bin/activate && pip install -e .
python -m or_mcp.server                 # stdio (Claude Desktop / Cursor)
TRANSPORT=http PORT=8000 python -m or_mcp.server   # remote (Streamable HTTP)
# completions: export OPENROUTER_API_KEY=... (billed to that account — the metering seam)
```

Claude Code: `claude mcp add --transport http openrouter http://localhost:8000/mcp`

## Tools
| Tool | What it does | Key? |
|------|--------------|------|
| `list_models` | Browse the catalog (filter by name) | no |
| `compare_pricing` | Rank models by cost (USD/1M tokens) | no |
| `recommend_model` | Pick by budget + min context window | no |
| `chat` | Run a completion (metered to the caller) | yes |

## Why first-party > community wrappers
Several community MCP wrappers of OpenRouter already exist — unmetered, unversioned, outside your control.
A first-party server (task-shaped tools, OAuth, usage metering, directory listings) makes agents paying,
governed users. That's what **[7Block Labs](https://7blocklabs.com)** builds for data & API companies.

MIT licensed.
