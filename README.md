# Pulse

**We give AI live data, instantly. Your agent is always up to date.**

> No stale training data. No web searches. No hallucinations. Just live facts, the moment your agent needs them.

---

## The Problem

Every AI agent deployed today reasons from the past. Language models are frozen at their training cutoff — they don't know what ETH is trading at right now, what gas looks like, what happened on-chain an hour ago. When an agent makes a decision, it is working from yesterday's world and nobody told it things changed.

Web search is a band-aid. It's slow, unstructured, one unverified source, no confidence score, no aggregation. Your agent deserves better infrastructure than a Google search.

**Pulse is that infrastructure.**

---

## What Pulse Does

Pulse runs continuously in the background — fetching live data from multiple independent sources every ~10 seconds, aggregating them, resolving conflicts, and returning a verified structured answer the moment your agent calls.

One API call. Any framework. Instant.

```python
from pulse import PulseClient

client = PulseClient("http://your-pulse-server/api")
ctx = client.context("What is the ETH price right now?")

print(ctx["answer"])     # "$2,443 · confidence: 0.91 · source: coingecko"
print(ctx["confidence"]) # 0.91
print(ctx["defer"])      # False — safe to act on
```

If Pulse can't verify the data, it returns `defer: true` — honest uncertainty instead of a confident wrong answer.

---

## Architecture

```
[CoinGecko]  [Etherscan]  [CoinPaprika]   ← independent async fetchers (Rust)
      \             |             /
       \            |            /
        [Aggregation — median consensus, conflict detection]
                    |
               [Redis cache]               ← 10s TTL, sub-ms reads
                    |
           [Pulse API — Axum/Rust]         ← HTTP + WebSocket
                    |
         [Python SDK / MCP Server]         ← one-line integration
                    |
          [Your AI agents]                 ← any framework
```

---

## MCP Server (Claude agents)

Pulse ships with a native MCP server. Any Claude-based agent gets live data as a built-in tool — no custom integration code.

```json
{
  "mcpServers": {
    "pulse": {
      "command": "/path/to/pulse/.venv/bin/python3",
      "args": ["/path/to/pulse/mcp_server.py"]
    }
  }
}
```

Tools exposed: `pulse_price`, `pulse_gas`, `pulse_health`, `pulse_feeds`, `pulse_feed`.

---

## Live Feeds

| Feed | Sources | Refresh |
|---|---|---|
| `eth_price` | CoinGecko, Etherscan | ~10s |
| `btc_price` | CoinGecko, CoinPaprika | ~10s |
| `sol_price` | CoinGecko | ~10s |
| Gas estimates | Etherscan | ~12s |

---

## Evaluation Results

Same question, baseline agent vs Pulse-powered agent, 10 live scenarios:

| Metric | Baseline | Pulse |
|---|---|---|
| Correct decisions | 1/10 (10%) | 5/10 (50%) |
| Source count | 1 unverified | 2-3 aggregated |
| Confidence scoring | None | 0.0–1.0 |
| Conflict detection | None | Yes |

Baseline on a gas spike: *"EXECUTE — gas appears normal."* Pulse on the same scenario: *"DEFER — gas data returned zero, verify manually."* Honest uncertainty beats confident wrongness every time.

---

## Tech Stack

| Layer | Choice |
|---|---|
| API + fetchers | Rust (Axum, Tokio, Reqwest) |
| Cache | Redis |
| Agent SDK | Python |
| MCP integration | Python (mcp 2.x) |
| Deployment | Production server, always-on |

---

## Quick Start

```bash
git clone https://github.com/itachi-exe/pulse
cd pulse

# With Docker
docker-compose up

# Query the API
curl http://localhost:7070/feed/eth_price
curl http://localhost:7070/feed/btc_price

# Python SDK
pip install -e ./sdk/python
python3 -c "from pulse import PulseClient; c = PulseClient('http://localhost:7071/api'); print(c.context('ETH price?'))"
```

---

## The One-Liner

> Every AI agent deployed today is flying blind. Pulse is the instrument panel.

---

## Submission: HackerEarth Frontier Engineering Challenge 2026

**Track:** AI Infrastructure / Agent Tooling
**Deadline:** Aug 31, 2026 18:00 UTC
**Live demo:** https://pulse.itachi.dev
**Contact:** itachi_r3birth@proton.me
