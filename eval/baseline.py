#!/usr/bin/env python3
"""
Baseline agent: answers using only training data + a single web search.
No aggregation, no source verification, no conflict resolution.
This is the dumb version — a single unverified data point driving decisions.
"""

import sys
import json
import urllib.request
import urllib.parse
import time
import os

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


def web_search_single(query: str) -> str:
    """Single unverified web search — no aggregation."""
    # Use DuckDuckGo instant answer API (keyless)
    url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "baseline-agent/0.1"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        abstract = data.get("AbstractText", "")
        answer = data.get("Answer", "")
        related = " ".join(r.get("Text", "") for r in data.get("RelatedTopics", [])[:2])
        return (abstract or answer or related or "No information found.")[:500]
    except Exception as e:
        return f"Search failed: {e}"


def baseline_answer(question: str) -> dict:
    """
    Baseline approach:
    1. Run one web search
    2. Trust it blindly
    3. Let the LLM answer from that single source
    """
    t0 = time.time()

    # Single unverified data source
    raw_data = web_search_single(question)

    # Simulate LLM reasoning (without actual API key for demo)
    # In production this would call OpenAI/Anthropic with the context
    decision = derive_decision_heuristic(question, raw_data)

    latency_ms = int((time.time() - t0) * 1000)

    return {
        "agent": "baseline",
        "question": question,
        "raw_context": raw_data,
        "decision": decision,
        "source_count": 1,
        "confidence": None,  # baseline has no confidence scoring
        "verification": "none",
        "latency_ms": latency_ms,
    }


def derive_decision_heuristic(question: str, context: str) -> str:
    """
    Heuristic decision derived from one unverified source.
    This is intentionally naive — it's the baseline we're beating.
    """
    q = question.lower()
    c = context.lower()

    if "gas" in q and "transact" in q:
        # Gas question — no real data, just guess
        return "EXECUTE — gas appears normal based on training data"
    elif "eth" in q or "bitcoin" in q or "btc" in q:
        if any(w in c for w in ["up", "bull", "rise", "gain"]):
            return "BUY signal detected"
        elif any(w in c for w in ["down", "bear", "drop", "crash"]):
            return "SELL signal detected"
        else:
            return "HOLD — price direction unclear from single source"
    elif "exploit" in q or "hack" in q or "attack" in q:
        return "MONITOR — unable to verify severity from single source"
    elif "depeg" in q or "stablecoin" in q:
        return "HOLD — peg status cannot be verified without live data"
    elif "listing" in q or "binance" in q:
        return "SPECULATIVE BUY — based on unverified listing rumor"
    elif "fed" in q or "rate" in q or "fomc" in q:
        return "REBALANCE — based on training data expectations (may be outdated)"
    else:
        return f"UNCERTAIN — context: {context[:100]}..."


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python baseline.py '<question>'")
        sys.exit(1)

    question = sys.argv[1]
    result = baseline_answer(question)
    print(json.dumps(result, indent=2))
