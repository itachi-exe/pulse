# Pulse

**Real-time truth layer for AI agents.**

> Chainlink is a data feed for smart contracts. Pulse is a data feed for AI agents.

---

## The Problem

Every AI agent deployed today fetches its own data, trusts it blindly, and has no way to verify it against other sources. Web search is one node, unverified, no aggregation, no conflict resolution.

When an agent makes a high-stakes decision — financial, medical, operational — it is working from stale or unverified information. It was trained on yesterday's world and nobody told it things changed.

Smart contracts had this exact problem. Chainlink solved it by building a decentralized oracle layer that aggregates real-world data from multiple nodes, resolves conflicts, and delivers a trusted answer on-chain.

Nobody has built that layer for AI agents.

**Pulse does.**

---

## What Pulse Is

A real-time truth layer for AI agents. Pulse runs continuously, fetching live data from multiple independent sources every ~10 seconds, aggregating them, resolving conflicts, and serving a verified, structured answer to any AI agent that calls it.

One API call. Any framework. Any domain.

```python
from pulse import feed

# Instead of trusting one unverified source:
context = feed.get("gas_price")
# Returns: {value, confidence, sources, agreement_score, latency_ms}

if context.value["safe_gwei"] > 80:
    print("Gas critically high — wait before transacting")
```

---

## Architecture

```
[Source A]  [Source B]  [Source C]   ← independent fetcher nodes (Rust, async)
     \           |           /
      \          |          /
       [Aggregation layer]           ← median consensus, conflict detection
              |
         [Redis cache]               ← sub-millisecond reads, 10s refresh
              |
      [Pulse API — axum]             ← WebSocket push + HTTP pull
              |
   [Agent SDK: Python / JS]          ← one-line integration
              |
     [Your AI agents]                ← LangChain, AutoGen, CrewAI, custom
```

---

## Feeds Available

| Feed Type | Sources | Use Case |
|---|---|---|
| `gas_price` | Etherscan, Blocknative, Owlracle | Transaction timing |
| `crypto_price` | CoinGecko, CoinPaprika, CoinCap | Price decisions |
| `on_chain` | Etherscan, Blockchair | Chain state, anomaly detection |
| `news` | CryptoPanic, NewsData | Event confirmation |
| `sentiment` | LunarCrush, Santiment | Social signals |

---

## Delivery Models

**Push (WebSocket):** Subscribe once, get updates every ~10 seconds.
```python
def on_gas(ctx):
    if ctx.value["safe_gwei"] > 80:
        agent.pause_transactions()

sub = feed.subscribe("gas_price", on_update=on_gas)
sub.start()
```

**Pull (HTTP):** Request on demand.
```python
context = feed.get("crypto_price", query="ETH")
```

---

## Evaluation Results

We ran 10 historical scenarios where we know the correct answer. Same question, baseline agent vs Pulse-powered agent.

| Metric | Baseline | Pulse |
|---|---|---|
| Correct decisions | 1/10 (10%) | 5/10 (50%) |
| Source count | 1 (unverified) | 2-3 (aggregated) |
| Confidence scoring | None | 0.0 - 1.0 |
| Conflict detection | None | Yes (spread %) |

**Key finding:** The baseline says "EXECUTE — gas appears normal based on training data" on a gas spike scenario. Pulse says "UNKNOWN — gas data returned zero, verify manually." Honest uncertainty beats confident wrongness.

---

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Fetcher nodes | Rust (tokio + reqwest) | Max concurrency, no GIL |
| Aggregation | Rust | Same process, zero latency |
| API server | Rust (axum) | WebSocket + HTTP, production-grade |
| Cache | Redis | Sub-millisecond reads |
| Agent SDK | Python | One-line integration |
| Container | Docker + compose | One command to run |

---

## Latency Targets

- **Sub-second:** Price feeds via API
- **2-3 seconds:** On-chain data (Ethereum ~12s blocks)
- **5-10 seconds:** News and social signals
- **10s TTL:** Cache refresh cycle

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/itachi-exe/pulse
cd pulse

# 2. Run everything
docker-compose up

# 3. Query a feed
curl http://localhost:7070/feed/gas_price
curl "http://localhost:7070/feed/crypto_price?q=ETH"

# 4. Use the SDK
pip install -e ./sdk/python
python3 -c "from pulse import feed; print(feed.get('gas_price').summary())"
```

---

## One-Command Setup (without Docker)

```bash
# Prerequisites: Rust 1.75+, Redis, Python 3.11+

# Start Redis
redis-server --daemonize yes

# Build and run Pulse
cargo run --release

# In another terminal, run the eval
pip install httpx websocket-client
python3 eval/eval_harness.py
```

---

## The Hot Take

> Every AI agent deployed today is driving blind at 200km/h. They were trained on yesterday's world and nobody told them it changed. We built the dashboard.

---

## What Pulse Is Not

- A web scraper with GPT on top
- A RAG system
- Another chatbot
- A blockchain oracle (we are the AI layer, not the chain layer)
- A product with users — this is infrastructure

---

## Submission: micro1 Frontier Engineering Challenge 2026

**Track:** AI Infrastructure / Agent Tooling  
**Deadline:** Aug 31, 2026 18:00 UTC  
**Contact:** itachi_r3birth@proton.me
