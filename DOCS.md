# Pulse — Developer Documentation

**The real-time truth layer for AI agents.**

Pulse gives your AI live, verified facts the instant it asks. No stale training data, no blind web scraping, no hallucinated numbers. One HTTP call returns structured, source-attributed data pulled continuously from **1,000+ free live sources** across 22 categories.

---

## Table of Contents

1. [What Pulse Does](#what-pulse-does)
2. [Core Concepts](#core-concepts)
3. [Quickstart (60 seconds)](#quickstart)
4. [Authentication](#authentication)
5. [API Reference](#api-reference)
6. [Response Shape](#response-shape)
7. [Categories](#categories)
8. [Connecting Pulse to Your AI](#connecting-pulse-to-your-ai)
   - [Raw HTTP (any language)](#raw-http)
   - [Python](#python)
   - [OpenAI / function calling](#openai-function-calling)
   - [LangChain tool](#langchain-tool)
   - [MCP (Claude Desktop / Claude Code)](#mcp)
9. [Latency & Caching](#latency--caching)
10. [Errors](#errors)
11. [FAQ](#faq)

---

## What Pulse Does

Every language model is frozen at its training cutoff. It does not know today's news, this hour's market, the current health advisory, or the earthquake that happened ten minutes ago. When an agent reasons from that frozen snapshot, it acts confidently on stale facts and nobody tells it the world moved.

Pulse fixes that. It runs continuously in the background, fetching from many independent sources, deduplicating and aggregating them, and serving the result the moment your agent calls. Your agent stops guessing and starts reading from the present.

**The whole promise: your AI is never out of date again.**

---

## Core Concepts

| Concept | Meaning |
|---|---|
| **Category** | A topic domain (e.g. `medical`, `politics`, `finance`). You request data by category. |
| **Feed** | The live result for a category: a list of fresh, source-attributed articles/records. |
| **Source** | One upstream publisher (WHO, USGS, BBC, arXiv, etc.). Every item carries its source. |
| **Verified pool** | The 1,000+ validated live feeds behind the categories. Each was tested to return real items. |
| **TTL** | How long a category's result is cached before the background warmer refreshes it. |
| **Free preview** | A subset of categories readable with no API key, for demos and evaluation. |

---

## Quickstart

No signup required for preview categories. Set your host and pull live data:

```bash
export PULSE_BASE="https://your-pulse-host"

curl "$PULSE_BASE/data/feed/medical"
```

You get back live health headlines from WHO and other medical sources, each with a title, URL, timestamp, and source name. That is the entire integration: one GET request.

For the full catalog (all 22 categories), [generate an API key](#authentication) and pass it as a header.

---

## Authentication

Pulse accepts three auth methods on data endpoints, checked in this order:

1. **API key header** — `X-Pulse-Key: pk_...`
2. **Bearer token** — `Authorization: Bearer pk_...`
3. **Query param** — `?key=pk_...` (convenient for quick tests; avoid in production logs)
4. **Session cookie** — `pulse_token` (set automatically when you log in through the web app)

### Free preview (no key)

These categories are readable without any auth, for demos and evaluation:

```
crypto   weather   medical   politics   news   science   disasters
```

Every other category returns `401` until you present a valid key.

### Getting a key

```bash
# 1. Create an account
curl -X POST "$PULSE_BASE/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password"}'

# 2. Log in (stores a session cookie)
curl -c cookies.txt -X POST "$PULSE_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"your-password"}'

# 3. Generate an API key (uses the session cookie from step 2)
curl -b cookies.txt -X POST "$PULSE_BASE/auth/keys/generate?label=my-agent"
# → {"key":"pk_xxxxxxxx...","prefix":"pk_xxxxxxxx","note":"Store this key — it will not be shown again."}
```

Store the key. It is shown once and only its hash is retained server-side.

---

## API Reference

Base URL: `$PULSE_BASE`

### Data

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/data/feed/{category}` | key / cookie / preview | Live feed for one category. |
| `GET` | `/data/categories` | none | Metadata for all 22 categories (label, icon, description). |
| `GET` | `/data/sources` | none | Count of verified live sources, broken down by category. |
| `GET` | `/data/sources/{category}` | none | Every verified source URL for one category. |
| `GET` | `/health` | none | Service status, category count, verified source count. |

### Auth & keys

| Method | Path | Auth | Description |
|---|---|---|---|
| `POST` | `/auth/signup` | none | Create an account. Body: `{email, password}`. |
| `POST` | `/auth/login` | none | Log in, sets `pulse_token` cookie. |
| `POST` | `/auth/logout` | cookie | Clear the session. |
| `GET` | `/auth/me` | cookie | Current user. |
| `POST` | `/auth/keys/generate` | cookie | Create an API key. Query: `?label=...`. Returns the raw key **once**. |
| `GET` | `/auth/keys` | cookie | List your keys (prefixes only, never the full key). |
| `DELETE` | `/auth/keys/{prefix}` | cookie | Revoke a key. |
| `GET` | `/auth/categories` | cookie | Your per-category enabled/disabled settings. |
| `POST` | `/auth/categories` | cookie | Enable/disable categories. Body: `{categories: [...]}`. |

---

## Response Shape

`GET /data/feed/{category}` returns:

```json
{
  "category": "medical",
  "label": "Health & Medical",
  "data": {
    "articles": [
      {
        "title": "WHO Director-General visits Jordan ...",
        "url": "https://www.who.int/news/item/...",
        "published": "Wed, 25 Feb 2026 18:06:55 Z",
        "summary": "The Director-General of the World Health Organization ...",
        "source": "News (English) - World Health Organization",
        "feed": "WHO News"
      }
    ],
    "verified_pool_size": 87,
    "pool_batch": ["WHO News", "CDC Newsroom", "..."]
  },
  "cached": true,
  "ttl_seconds": 120,
  "feeds_available": 87,
  "total_verified_sources": 1186,
  "timestamp": "2026-08-31T12:00:00.000000+00:00"
}
```

**Field guide**

| Field | Meaning |
|---|---|
| `data.articles[]` | The live records. Always source-attributed. |
| `verified_pool_size` | How many validated feeds stand behind this category. |
| `pool_batch` | Which sources contributed to this specific response. |
| `cached` | `true` if served from the warm cache (the normal, fast path). |
| `ttl_seconds` | Cache lifetime before the background warmer refreshes. |
| `total_verified_sources` | Total validated live sources across all categories. |
| `timestamp` | UTC time this response was assembled. |

---

## Categories

22 live categories:

```
crypto      onchain     defi        finance     economics
news        weather     climate     air         disasters
space       science     medical     tech        cybersecurity
sports      gaming      social      politics    aviation
jobs        commodities
```

Get live metadata and per-category source counts:

```bash
curl "$PULSE_BASE/data/categories"          # labels + descriptions
curl "$PULSE_BASE/data/sources"             # verified counts per category
curl "$PULSE_BASE/data/sources/medical"     # every source URL for one category
```

---

## Connecting Pulse to Your AI

The pattern is always the same: **before your agent reasons, fetch the relevant Pulse feed and inject it into the prompt.** The model then answers from live facts instead of its training snapshot.

### Raw HTTP

Any language that can make an HTTP GET can use Pulse.

```bash
curl -H "X-Pulse-Key: $PULSE_KEY" "$PULSE_BASE/data/feed/finance"
```

### Python

```python
import httpx

PULSE_BASE = "https://your-pulse-host"
PULSE_KEY  = "pk_..."  # omit for free-preview categories

def pulse(category: str) -> dict:
    r = httpx.get(
        f"{PULSE_BASE}/data/feed/{category}",
        headers={"X-Pulse-Key": PULSE_KEY},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()

feed = pulse("medical")
for a in feed["data"]["articles"][:5]:
    print(f"- {a['title']}  ({a['source']})")
```

### Injecting into an agent prompt

```python
def with_live_context(user_question: str, category: str) -> str:
    feed = pulse(category)
    facts = "\n".join(
        f"- {a['title']} ({a['source']}, {a['published']})"
        for a in feed["data"]["articles"][:8]
    )
    return (
        "You are answering using ONLY the live facts below. "
        "If they do not cover the question, say so.\n\n"
        f"LIVE {category.upper()} DATA (as of {feed['timestamp']}):\n{facts}\n\n"
        f"QUESTION: {user_question}"
    )

prompt = with_live_context("What did WHO announce recently?", "medical")
# send `prompt` to your LLM of choice
```

### OpenAI function calling

Expose Pulse as a tool the model can call on demand:

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_live_data",
        "description": "Fetch live, verified real-world data by category before answering.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {
                    "type": "string",
                    "enum": ["medical","politics","finance","news","science",
                             "disasters","crypto","weather","tech","cybersecurity"]
                }
            },
            "required": ["category"]
        }
    }
}]

# When the model calls get_live_data(category=...), run pulse(category)
# and return feed["data"]["articles"] as the tool result.
```

### LangChain tool

```python
from langchain.tools import tool

@tool
def live_data(category: str) -> str:
    """Fetch live verified data for a category (medical, politics, finance, news, ...)."""
    feed = pulse(category)
    return "\n".join(
        f"- {a['title']} ({a['source']})"
        for a in feed["data"]["articles"][:8]
    )

# add `live_data` to your agent's tool list
```

### MCP

Pulse ships an MCP server, so any MCP-aware agent (Claude Desktop, Claude Code) gets live data as native tools.

**Claude Desktop** (`~/.claude/config.json`):

```json
{
  "mcpServers": {
    "pulse": {
      "command": "/root/pulse/.venv/bin/python3",
      "args": ["/root/pulse/mcp_server.py"],
      "env": { "PULSE_API_URL": "https://your-pulse-host" }
    }
  }
}
```

**Claude Code / Hermes:**

```bash
hermes mcp add pulse /root/pulse/.venv/bin/python3 /root/pulse/mcp_server.py
```

Once registered, the agent can call Pulse tools directly during a conversation with no extra glue code.

---

## Latency & Caching

Pulse uses a **background heartbeat warmer**, not on-demand fetching. Every category is pre-fetched and refreshed at ~80% of its TTL, so the cache is always hot.

- **Steady-state (warm cache):** ~6 ms
- **First request after cold start:** ~16 ms average

`cached: true` in the response means you hit the warm path. You almost always will. This is the difference between claiming "fast" and being provably fast when your agent is waiting on the answer.

---

## Errors

| Status | Meaning | Fix |
|---|---|---|
| `401 Invalid API key` | Key missing or wrong on a non-preview category. | Pass a valid `X-Pulse-Key`. |
| `401 API key required` | Unauthenticated request to a non-preview category. | Use a preview category or add a key. |
| `403 Category disabled` | Category turned off in your account settings. | Re-enable via `POST /auth/categories`. |
| `404 Unknown category` | Category name not in the 22-category set. | Check `GET /data/categories`. |

Errors are plain JSON: `{"detail": "..."}`.

---

## FAQ

**Is this just a wrapper around web search?**
No. Web search is one unranked, unverified source fetched slowly at query time. Pulse continuously aggregates many independent sources per category, deduplicates them, keeps them warm, and returns them in milliseconds with attribution.

**Are the data sources free?**
Yes. Every source is a free API or public RSS/Atom feed. No paid keys anywhere in the stack.

**How many sources really?**
1,000+ verified. Each was validated to return real live items against the same parser the product uses. `GET /data/sources` returns the live count and per-category breakdown, so it is reproducible, not a marketing number.

**What if Pulse can't verify something?**
It returns what it has with full source attribution rather than inventing an answer. Honest data beats confident fiction, which is the entire reason Pulse exists.

**Which framework do I need?**
None. Pulse is plain HTTP. It works with OpenAI, Anthropic, LangChain, LlamaIndex, a raw `curl`, or anything that speaks HTTP.

---

*Pulse — your AI, never out of date.*
