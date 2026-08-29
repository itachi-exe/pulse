#!/usr/bin/env python3
"""
Pulse MCP Server — mcp 2.x
Exposes live crypto prices, gas estimates, and confidence scoring
as native tools for any Claude-based agent.

Usage (stdio — Claude Desktop / Claude Code):
  /root/pulse/.venv/bin/python3 /root/pulse/mcp_server.py

Claude Desktop config (~/.claude/config.json):
  {
    "mcpServers": {
      "pulse": {
        "command": "/root/pulse/.venv/bin/python3",
        "args": ["/root/pulse/mcp_server.py"]
      }
    }
  }

Claude Code (hermes config):
  hermes mcp add pulse /root/pulse/.venv/bin/python3 /root/pulse/mcp_server.py
"""

import asyncio
import os
import httpx
from mcp.server.mcpserver import MCPServer

# ── Config ───────────────────────────────────────────────────────────────────
PULSE_API = os.getenv("PULSE_API_URL", "http://localhost:7070")
TIMEOUT   = 8.0

mcp = MCPServer("pulse", version="0.1.0")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt(data: dict) -> str:
    v    = data.get("value", {})
    src  = (data.get("sources") or [{}])[0].get("source", "unknown")
    conf = round(data.get("confidence", 0) * 100)
    agr  = round(data.get("agreement_score", 0) * 100)
    lat  = data.get("latency_ms", 0)
    ts   = data.get("refreshed_at", "?")

    lines = []
    if v.get("price_usd"):
        lines.append(f"Price: ${v['price_usd']:,.4f} USD")
    if v.get("symbol"):
        lines.append(f"Symbol: {v['symbol']}")
    if v.get("change_24h_pct"):
        arrow = "↑" if v["change_24h_pct"] > 0 else "↓"
        lines.append(f"24h Change: {arrow} {abs(v['change_24h_pct']):.2f}%")
    if v.get("fast_gwei"):
        lines.append(f"Gas Fast:  {v['fast_gwei']} gwei")
        lines.append(f"Gas Safe:  {v['safe_gwei']} gwei")
        lines.append(f"Base Fee:  {v['base_fee_gwei']} gwei")

    lines += [
        f"Confidence: {conf}%  (source agreement: {agr}%)",
        f"Source: {src}",
        f"Latency: {lat}ms",
        f"Refreshed: {ts}",
    ]
    if conf < 40:
        lines.append("⚠ DEFER — confidence below 40%. Do not act on this data.")

    return "\n".join(lines)

async def _get(path: str) -> tuple[int, dict]:
    async with httpx.AsyncClient(base_url=PULSE_API, timeout=TIMEOUT) as c:
        try:
            r = await c.get(path)
            return r.status_code, dict(r.json())
        except httpx.ConnectError:
            return 503, {"error": f"Pulse API unreachable at {PULSE_API}"}
        except httpx.TimeoutException:
            return 504, {"error": "Pulse API timed out"}
        except Exception as e:
            return 500, {"error": str(e)}

# ── Tools ─────────────────────────────────────────────────────────────────────

@mcp.tool(description=(
    "Get the live price of a cryptocurrency. "
    "Returns real-time USD price, 24h change, confidence score, and data source. "
    "Supported symbols: ETH, BTC, SOL, MATIC, and others available on CoinGecko. "
    "Always use this instead of recalling stale training-data prices."
))
async def pulse_price(symbol: str) -> str:
    """
    Args:
        symbol: Ticker symbol e.g. ETH, BTC, SOL
    """
    feed = f"{symbol.strip().lower()}_price"
    status, data = await _get(f"/feed/{feed}")
    if status == 404:
        return f"No feed found for '{symbol}'. Try ETH, BTC, or SOL."
    if status != 200:
        return f"Error fetching price: {data.get('error', 'unknown')}"
    return _fmt(data)


@mcp.tool(description=(
    "Get the current Ethereum gas price estimate. "
    "Returns safe, fast, and base fee in gwei. "
    "Use before estimating on-chain transaction costs."
))
async def pulse_gas() -> str:
    status, data = await _get("/feed/eth_price")
    if status != 200:
        return f"Gas data unavailable: {data.get('error', 'unknown')}"
    v = data.get("value", {})
    if not v.get("fast_gwei"):
        return "Gas data not yet available — Etherscan may be rate-limited. Retry in 30s."
    return (
        f"Gas Fast:  {v['fast_gwei']} gwei\n"
        f"Gas Safe:  {v['safe_gwei']} gwei\n"
        f"Base Fee:  {v['base_fee_gwei']} gwei\n"
        f"Confidence: {round(data.get('confidence', 0) * 100)}%\n"
        f"Source: etherscan\n"
        f"Refreshed: {data.get('refreshed_at', '?')}"
    )


@mcp.tool(description="Check whether the Pulse API is online and healthy.")
async def pulse_health() -> str:
    status, data = await _get("/health")
    if status != 200:
        return f"Pulse API is DOWN (HTTP {status})"
    return (
        f"Pulse API: {data.get('status', '?').upper()}\n"
        f"Version: {data.get('version', '?')}\n"
        f"Endpoint: {PULSE_API}"
    )


@mcp.tool(description=(
    "List all currently cached data feeds in Pulse. "
    "Returns feed IDs and last refresh timestamps. "
    "Use this to discover what feeds are available before calling pulse_feed."
))
async def pulse_feeds() -> str:
    status, data = await _get("/feeds")
    if status != 200:
        return f"Could not list feeds: {data.get('error', 'unknown')}"
    feeds = data.get("cached_feeds", [])
    if not feeds:
        return "No feeds cached yet. Trigger one by calling pulse_price first."
    lines = [f"Cached feeds ({data.get('count', 0)}):"]
    for f in feeds:
        lines.append(f"  • {f.get('feed_id', '?')}  —  refreshed {f.get('refreshed_at', '?')}")
    return "\n".join(lines)


@mcp.tool(description=(
    "Fetch any specific Pulse feed by its feed_type identifier. "
    "Common values: eth_price, btc_price, sol_price. "
    "Call pulse_feeds first to see what is available."
))
async def pulse_feed(feed_type: str) -> str:
    """
    Args:
        feed_type: Feed identifier e.g. eth_price, btc_price, sol_price
    """
    status, data = await _get(f"/feed/{feed_type.strip()}")
    if status == 404:
        return f"Feed '{feed_type}' not found. Call pulse_feeds to see available feeds."
    if status != 200:
        return f"Error: {data.get('error', 'unknown')}"
    return _fmt(data)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(mcp.run_stdio_async())
