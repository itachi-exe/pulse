#!/usr/bin/env python3
"""
Pulse-powered agent: answers using verified, aggregated, multi-source real-time data.
Same questions as the baseline — but with Pulse providing truth before the LLM responds.
"""

import sys
import json
import time
import httpx
import os
from typing import Optional


PULSE_URL = os.environ.get("PULSE_URL", "http://localhost:7070")


def pulse_get(feed_type: str, query: str = None) -> Optional[dict]:
    """Fetch a verified Pulse feed."""
    params = {"q": query} if query else {}
    try:
        resp = httpx.get(
            f"{PULSE_URL}/feed/{feed_type}",
            params=params,
            timeout=15.0,
        )
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        print(f"[pulse] error: {e}", file=sys.stderr)
    return None


def pulse_answer(question: str) -> dict:
    """
    Pulse-powered approach:
    1. Classify the question to pick the right feed
    2. Fetch verified, aggregated data from 3+ sources
    3. Decision is grounded in confirmed multi-source truth
    """
    t0 = time.time()
    q = question.lower()

    # Route to the right feed type
    if "gas" in q:
        feed = pulse_get("gas_price")
        decision = gas_decision(feed, question)
    elif any(sym in q for sym in ["eth", "btc", "bitcoin", "ethereum", "sol", "bnb", "token", "price"]):
        symbol = extract_symbol(q)
        feed = pulse_get("crypto_price", query=symbol)
        decision = price_decision(feed, question)
    elif any(w in q for w in ["exploit", "hack", "attack", "vulnerability", "block"]):
        feed = pulse_get("on_chain", query=question)
        decision = onchain_decision(feed, question)
    elif any(w in q for w in ["depeg", "stablecoin", "usdc", "usdt", "dai"]):
        feed = pulse_get("crypto_price", query="usdc")
        decision = stablecoin_decision(feed, question)
    elif any(w in q for w in ["listing", "binance", "exchange"]):
        symbol = extract_symbol(q)
        feed = pulse_get("news", query=question)
        decision = news_decision(feed, question)
    elif any(w in q for w in ["fed", "rate", "fomc", "inflation", "cpi", "regulatory"]):
        feed = pulse_get("news", query=question)
        decision = regulatory_decision(feed, question)
    elif any(w in q for w in ["sentiment", "social", "twitter", "x.com"]):
        symbol = extract_symbol(q)
        feed = pulse_get("sentiment", query=symbol)
        decision = sentiment_decision(feed, question)
    else:
        feed = pulse_get("crypto_price", query=question)
        decision = generic_decision(feed, question)

    latency_ms = int((time.time() - t0) * 1000)

    return {
        "agent": "pulse",
        "question": question,
        "feed": feed,
        "decision": decision,
        "source_count": feed.get("source_count", 0) if feed else 0,
        "confidence": feed.get("confidence") if feed else None,
        "agreement_score": feed.get("agreement_score") if feed else None,
        "verification": "multi-source aggregated" if feed else "feed unavailable",
        "latency_ms": latency_ms,
    }


# ── Decision logic ────────────────────────────────────────────────────────────

def gas_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — Pulse feed unavailable, cannot verify gas safely"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    safe_gwei = val.get("safe_gwei", val.get("slow_gwei", 0))
    fast_gwei = val.get("fast_gwei", 0)
    base = val.get("base_fee_gwei", 0)
    sources = feed.get("source_count", 1)

    tag = f"[{sources} sources, {conf:.0%} confidence]"

    if safe_gwei > 80 or fast_gwei > 150:
        return f"WAIT — gas critically high ({safe_gwei:.0f} gwei safe, {fast_gwei:.0f} fast). Do not transact now. {tag}"
    elif safe_gwei > 40:
        return f"CAUTION — gas elevated ({safe_gwei:.0f} gwei safe). Transact only if time-sensitive. {tag}"
    elif safe_gwei > 0:
        return f"EXECUTE — gas normal ({safe_gwei:.0f} gwei safe). Good window to transact. {tag}"
    else:
        return f"UNKNOWN — gas data returned zero, verify manually. {tag}"


def price_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — price feed unavailable"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    agreement = feed.get("agreement_score", 0)

    price = val.get("price_usd", 0)
    change = val.get("change_24h_pct", 0)
    spread = val.get("_spread_pct", 0)

    tag = f"[{sources} sources, {conf:.0%} confidence, {agreement:.0%} agreement]"

    if spread > 5:
        return f"ALERT — sources disagree on price by {spread:.1f}%. Possible manipulation or data issue. Manual check required. {tag}"
    elif change < -10:
        return f"SELL/EXIT — significant drop ({change:.1f}% in 24h) confirmed across {sources} sources at ${price:.2f}. {tag}"
    elif change < -5:
        return f"REDUCE — notable decline ({change:.1f}% 24h) at ${price:.2f}. Consider reducing exposure. {tag}"
    elif change > 10:
        return f"BUY signal — strong upward move ({change:.1f}% 24h) confirmed at ${price:.2f}. {tag}"
    elif change > 5:
        return f"BULLISH — positive momentum ({change:.1f}% 24h) at ${price:.2f}. {tag}"
    else:
        return f"HOLD — price stable at ${price:.2f} ({change:+.1f}% 24h), no strong signal. {tag}"


def onchain_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — on-chain feed unavailable"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    tag = f"[{sources} sources, {conf:.0%} confidence]"

    # Check for anomalous transaction counts or fees
    txs_24h = val.get("transactions_24h", 0)
    avg_fee = val.get("avg_fee_eth", 0)

    if avg_fee > 0.01:  # >0.01 ETH avg fee = extreme congestion, possible exploit
        return f"ALERT — abnormally high avg fees ({avg_fee:.4f} ETH). Network stress detected. Pause operations. {tag}"
    elif txs_24h > 1_500_000:
        return f"HIGH ACTIVITY — {txs_24h:,} txs/24h detected, network congested. Monitor closely. {tag}"
    else:
        return f"NORMAL — on-chain metrics within expected range. {tag}"


def stablecoin_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — stablecoin feed unavailable, cannot verify peg"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    price = val.get("price_usd", 1.0)
    tag = f"[{sources} sources, {conf:.0%} confidence]"

    deviation = abs(price - 1.0)
    if deviation > 0.05:
        return f"EMERGENCY EXIT — stablecoin depegged to ${price:.4f} ({deviation*100:.1f}% off peg). Exit immediately. {tag}"
    elif deviation > 0.01:
        return f"WARNING — peg stress detected at ${price:.4f}. Reduce exposure. {tag}"
    else:
        return f"STABLE — peg holding at ${price:.4f}. No action needed. {tag}"


def news_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — news feed unavailable"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    count = val.get("article_count", 0)
    sentiment = val.get("sentiment_score", 0)
    headlines = val.get("top_headlines", [])
    tag = f"[{sources} sources, {conf:.0%} confidence]"

    if "listing" in question.lower():
        if count > 5:
            return f"CONFIRMED SIGNAL — {count} articles about this listing. Strong market event. {tag}\nTop headline: {headlines[0] if headlines else 'N/A'}"
        elif count > 0:
            return f"WEAK SIGNAL — only {count} articles found. Unconfirmed or early. Proceed with caution. {tag}"
        else:
            return f"NO CONFIRMATION — no news coverage found for this listing. High risk of false signal. {tag}"

    if sentiment > 0.3:
        return f"BULLISH NEWS SENTIMENT ({sentiment:.2f}) — {count} articles. {tag}\nTop: {headlines[0] if headlines else 'N/A'}"
    elif sentiment < -0.3:
        return f"BEARISH NEWS SENTIMENT ({sentiment:.2f}) — {count} articles. Reduce exposure. {tag}"
    else:
        return f"NEUTRAL SENTIMENT ({sentiment:.2f}) — no strong directional signal. {tag}"


def regulatory_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — news feed unavailable, cannot assess regulatory impact"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    count = val.get("article_count", 0)
    headlines = val.get("top_headlines", [])
    tag = f"[{sources} sources, {conf:.0%} confidence]"

    if count > 10:
        return f"MAJOR REGULATORY EVENT — {count} articles covering this. PAUSE operations until legal assessment complete. {tag}\nTop: {headlines[0] if headlines else 'N/A'}"
    elif count > 3:
        return f"REGULATORY NEWS DETECTED — {count} articles. Review implications before proceeding. {tag}"
    else:
        return f"LOW REGULATORY SIGNAL — only {count} articles. Monitor but no immediate action required. {tag}"


def sentiment_decision(feed: Optional[dict], question: str) -> str:
    if not feed or not feed.get("value"):
        return "DEFER — sentiment feed unavailable"

    val = feed["value"]
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    galaxy = val.get("galaxy_score", 0)
    sentiment = val.get("sentiment", 0)
    vol = val.get("social_volume_24h", 0)
    tag = f"[{sources} sources, {conf:.0%} confidence]"

    if galaxy > 75 and sentiment > 0.6:
        return f"STRONG BULLISH SOCIAL SIGNAL — galaxy score {galaxy:.0f}, sentiment {sentiment:.2f}, {vol:,} social mentions. {tag}"
    elif galaxy < 30 or sentiment < 0.3:
        return f"BEARISH SOCIAL SIGNAL — galaxy {galaxy:.0f}, sentiment {sentiment:.2f}. Risk elevated. {tag}"
    else:
        return f"NEUTRAL SOCIAL — galaxy {galaxy:.0f}, sentiment {sentiment:.2f}, {vol:,} mentions. No strong signal. {tag}"


def generic_decision(feed: Optional[dict], question: str) -> str:
    if not feed:
        return "DEFER — feed unavailable"
    conf = feed.get("confidence", 0)
    sources = feed.get("source_count", 1)
    return f"DATA RETRIEVED — {sources} sources, {conf:.0%} confidence. Review value field for details."


# ── Helpers ───────────────────────────────────────────────────────────────────

def extract_symbol(query: str) -> str:
    q = query.upper()
    for sym in ["BTC", "ETH", "SOL", "BNB", "MATIC", "ARB", "OP", "AVAX", "LINK", "USDC", "USDT", "DAI"]:
        if sym in q:
            return sym.lower()
    return "ethereum"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python pulse_agent.py '<question>'")
        sys.exit(1)

    question = sys.argv[1]
    result = pulse_answer(question)
    print(json.dumps(result, indent=2, default=str))
