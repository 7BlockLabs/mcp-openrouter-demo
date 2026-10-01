"""
OpenRouter MCP Server — a 7Block Labs build for OpenRouter.

A production-shaped Model Context Protocol server over OpenRouter's API. It lets any MCP client
(Claude, ChatGPT, Cursor, agent frameworks) browse the model catalog, compare pricing, pick a model
by budget/context, and run completions — turning OpenRouter into a first-party, agent-native surface
instead of leaving it to community wrappers.

Catalog/pricing tools are KEYLESS (OpenRouter's /models is public). Completions use the caller's own
OPENROUTER_API_KEY, so usage is metered to their account — the seam where per-plan billing attaches.

Run (stdio):   python -m or_mcp.server
Run (remote):  TRANSPORT=http PORT=8000 python -m or_mcp.server
"""
from __future__ import annotations

import os
import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

API = "https://openrouter.ai/api/v1"
UA = "openrouter-mcp/1.0 (+https://github.com/7BlockLabs/mcp-openrouter-demo)"
READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=True)

mcp = MCPServer(
    "OpenRouter",
    instructions=(
        "OpenRouter model routing over MCP. Use list_models to browse, compare_pricing to rank by "
        "cost, recommend_model to pick by budget/context window, and chat to run a completion "
        "(needs the user's OPENROUTER_API_KEY). Prices are USD per 1M tokens."
    ),
)


async def _get(path: str, params: dict | None = None, key: str | None = None) -> dict:
    headers = {"User-Agent": UA}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    async with httpx.AsyncClient(timeout=20, headers=headers) as c:
        r = await c.get(f"{API}{path}", params=params or {})
        r.raise_for_status()
        return r.json()


def _price_per_m(model: dict) -> dict:
    p = model.get("pricing", {}) or {}
    def perm(v):
        try: return round(float(v) * 1_000_000, 4)
        except Exception: return None
    return {"prompt": perm(p.get("prompt")), "completion": perm(p.get("completion"))}


@mcp.tool(title="List available models",
          description="List OpenRouter's model catalog. Optional substring filter on id/name "
          "(e.g. 'claude', 'gpt', 'llama'). Keyless.", annotations=READ_ONLY)
async def list_models(filter: str | None = None, limit: int = 40) -> dict:
    data = (await _get("/models")).get("data", [])
    if filter:
        f = filter.lower()
        data = [m for m in data if f in m.get("id", "").lower() or f in (m.get("name") or "").lower()]
    out = [{"id": m["id"], "name": m.get("name"),
            "context": m.get("context_length"), "price_per_1m": _price_per_m(m)} for m in data[:limit]]
    return {"count": len(out), "models": out}


@mcp.tool(title="Compare model pricing",
          description="Rank models by cost (cheapest first) on prompt or completion tokens, "
          "USD per 1M tokens. Optional filter. Keyless.", annotations=READ_ONLY)
async def compare_pricing(on: str = "completion", filter: str | None = None, top: int = 15) -> dict:
    data = (await _get("/models")).get("data", [])
    if filter:
        f = filter.lower()
        data = [m for m in data if f in m.get("id", "").lower() or f in (m.get("name") or "").lower()]
    rows = []
    for m in data:
        pm = _price_per_m(m); v = pm.get(on)
        if v is not None:
            rows.append({"id": m["id"], "price_per_1m": v, "context": m.get("context_length")})
    rows.sort(key=lambda r: r["price_per_1m"])
    return {"ranked_by": on, "cheapest": rows[:top]}


@mcp.tool(title="Recommend a model",
          description="Pick models fitting a budget (max USD/1M completion tokens) and minimum "
          "context window. Keyless.", annotations=READ_ONLY)
async def recommend_model(max_price_per_1m: float = 5.0, min_context: int = 32000) -> dict:
    data = (await _get("/models")).get("data", [])
    hits = []
    for m in data:
        pm = _price_per_m(m); c = m.get("context_length") or 0
        comp = pm.get("completion")
        if comp is not None and comp <= max_price_per_1m and c >= min_context:
            hits.append({"id": m["id"], "price_per_1m": comp, "context": c})
    hits.sort(key=lambda r: r["price_per_1m"])
    return {"budget": max_price_per_1m, "min_context": min_context, "matches": hits[:15]}


@mcp.tool(title="Run a chat completion",
          description="Run a completion through OpenRouter. Needs the user's OPENROUTER_API_KEY in "
          "env — usage is billed to their account (the metering seam).")
async def chat(model: str, prompt: str, system: str | None = None) -> dict:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return {"error": "set OPENROUTER_API_KEY to run completions (catalog tools are keyless)"}
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    async with httpx.AsyncClient(timeout=60, headers={"Authorization": f"Bearer {key}", "User-Agent": UA}) as c:
        r = await c.post(f"{API}/chat/completions", json={"model": model, "messages": msgs})
        r.raise_for_status()
        d = r.json()
    return {"model": model, "reply": d["choices"][0]["message"]["content"], "usage": d.get("usage")}


def main() -> None:
    if os.environ.get("TRANSPORT") == "http":
        import uvicorn
        uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
    else:
        mcp.run()


if __name__ == "__main__":
    main()
