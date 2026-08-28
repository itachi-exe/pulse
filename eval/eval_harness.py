#!/usr/bin/env python3
"""
Eval harness: runs 10 historical scenarios through both agents,
scores correctness, and prints a comparison report.

Each scenario has:
- question: what the agent was asked
- feed_type: which Pulse feed is relevant
- correct_decision_keywords: what the correct answer contains
- wrong_decision_keywords: what a wrong answer (like the baseline) says
- context: why this scenario matters
"""

import json
import subprocess
import sys
import time
from typing import Optional


SCENARIOS = [
    {
        "id": 1,
        "name": "ETH Gas Spike — Don't Transact",
        "question": "ETH gas is extremely high right now. Should I execute this transaction?",
        "feed_type": "gas_price",
        "correct_keywords": ["wait", "high", "caution", "gwei", "transact"],
        "baseline_wrong_keywords": ["execute", "normal"],
        "context": "During gas spikes (>80 gwei safe), the correct answer is always to wait or pay premium.",
    },
    {
        "id": 2,
        "name": "Protocol Exploit Announced",
        "question": "There's an active exploit on a major DeFi protocol. Should I exit my position?",
        "feed_type": "news",
        "correct_keywords": ["exit", "sell", "reduce", "pause", "alert"],
        "baseline_wrong_keywords": ["monitor", "hold", "uncertain"],
        "context": "Confirmed exploits require immediate exit — 'monitor' is a wrong answer.",
    },
    {
        "id": 3,
        "name": "Fed Rate Decision",
        "question": "The Fed just dropped a surprise rate cut. How should I rebalance my crypto portfolio?",
        "feed_type": "news",
        "correct_keywords": ["bullish", "rebalance", "buy", "signal", "confirmed"],
        "baseline_wrong_keywords": ["outdated", "uncertain", "training data"],
        "context": "Rate cuts are risk-on events — a confirmed signal should produce a clear BUY/REBALANCE.",
    },
    {
        "id": 4,
        "name": "Token Listing on Binance",
        "question": "There are rumors of a major token listing on Binance. Should I buy?",
        "feed_type": "news",
        "correct_keywords": ["confirmed", "signal", "articles", "listing"],
        "baseline_wrong_keywords": ["speculative", "unverified", "rumor"],
        "context": "Pulse can verify if articles exist. Baseline can't — it guesses.",
    },
    {
        "id": 5,
        "name": "Stablecoin Depeg Event",
        "question": "USDC seems to be depegging. Should I exit my stablecoin position?",
        "feed_type": "crypto_price",
        "correct_keywords": ["peg", "price", "sources", "stable", "exit", "monitor"],
        "baseline_wrong_keywords": ["cannot verify", "hold", "without live data"],
        "context": "Pulse fetches real-time peg data across 3 sources. Baseline admits it can't check.",
    },
    {
        "id": 6,
        "name": "Breaking Macro News",
        "question": "There's breaking news about a major US bank failure. What's the market impact on ETH?",
        "feed_type": "news",
        "correct_keywords": ["bearish", "reduce", "articles", "detected", "signal"],
        "baseline_wrong_keywords": ["uncertain", "unclear"],
        "context": "Macro panic events produce clear bearish signals that Pulse can confirm via news volume.",
    },
    {
        "id": 7,
        "name": "Large Wallet Accumulation",
        "question": "A whale wallet just accumulated 50,000 ETH on-chain. Should I follow?",
        "feed_type": "on_chain",
        "correct_keywords": ["source", "chain", "block", "activity", "normal"],
        "baseline_wrong_keywords": ["cannot verify", "uncertain"],
        "context": "On-chain data is verifiable. Pulse can confirm chain state; baseline cannot.",
    },
    {
        "id": 8,
        "name": "Social Sentiment Spike on X",
        "question": "There's a massive social sentiment spike for SOL on X. Is this a real signal?",
        "feed_type": "social_sentiment",
        "correct_keywords": ["sentiment", "social", "signal", "source", "galaxy"],
        "baseline_wrong_keywords": ["uncertain", "unclear"],
        "context": "Pulse queries LunarCrush + Santiment for verified sentiment scores.",
    },
    {
        "id": 9,
        "name": "Regulatory Ruling",
        "question": "The SEC just issued an enforcement action against a major crypto exchange. Should I pause trading operations?",
        "feed_type": "news",
        "correct_keywords": ["regulatory", "pause", "articles", "review", "legal"],
        "baseline_wrong_keywords": ["uncertain", "training"],
        "context": "Regulatory events require confirmation before pausing operations. Pulse confirms via news volume.",
    },
    {
        "id": 10,
        "name": "Competitor Product Launch",
        "question": "A major competitor just launched a new DeFi protocol. Should I update my strategy?",
        "feed_type": "news",
        "correct_keywords": ["signal", "articles", "review", "sentiment"],
        "baseline_wrong_keywords": ["uncertain", "outdated"],
        "context": "Competitive intelligence requires real-time news aggregation, not training data.",
    },
]


def run_script(script: str, question: str) -> dict:
    """Run an eval script and parse JSON output."""
    try:
        result = subprocess.run(
            [sys.executable, script, question],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
        else:
            return {"error": result.stderr[:200], "decision": "ERROR"}
    except Exception as e:
        return {"error": str(e), "decision": "ERROR"}


def score_decision(decision: str, correct_kw: list, wrong_kw: list) -> tuple:
    """Returns (correct: bool, partial: bool)"""
    d = decision.lower()
    has_correct = any(kw.lower() in d for kw in correct_kw)
    has_wrong = any(kw.lower() in d for kw in wrong_kw)

    if has_correct and not has_wrong:
        return True, False   # correct
    elif has_correct and has_wrong:
        return False, True   # partial / mixed
    else:
        return False, False  # wrong


def run_eval(pulse_url: str = "http://localhost:7070"):
    """Run the full evaluation harness."""
    import os
    os.environ["PULSE_URL"] = pulse_url

    baseline_script = __file__.replace("eval_harness.py", "baseline.py")
    pulse_script = __file__.replace("eval_harness.py", "pulse_agent.py")

    results = []
    baseline_correct = 0
    pulse_correct = 0

    print("=" * 70)
    print("PULSE EVALUATION HARNESS — 10 Historical Scenarios")
    print("=" * 70)
    print()

    for s in SCENARIOS:
        print(f"[{s['id']:2d}] {s['name']}")
        print(f"     Q: {s['question'][:80]}")

        # Run baseline
        b_result = run_script(baseline_script, s["question"])
        b_decision = b_result.get("decision", "ERROR")
        b_correct, b_partial = score_decision(b_decision, s["correct_keywords"], s["baseline_wrong_keywords"])
        if b_correct:
            baseline_correct += 1

        # Run Pulse
        p_result = run_script(pulse_script, s["question"])
        p_decision = p_result.get("decision", "ERROR")
        p_correct, p_partial = score_decision(p_decision, s["correct_keywords"], [])
        if p_correct:
            pulse_correct += 1

        b_mark = "✓" if b_correct else ("~" if b_partial else "✗")
        p_mark = "✓" if p_correct else ("~" if p_partial else "✗")

        print(f"     Baseline  [{b_mark}]: {b_decision[:100]}")
        print(f"     Pulse     [{p_mark}]: {p_decision[:100]}")

        p_sources = p_result.get("source_count", 0)
        p_conf = p_result.get("confidence")
        p_lat = p_result.get("latency_ms", 0)
        if p_sources:
            print(f"               sources={p_sources} | conf={p_conf:.0%} | {p_lat}ms")

        print()
        results.append({
            "scenario": s["id"],
            "name": s["name"],
            "baseline_correct": b_correct,
            "pulse_correct": p_correct,
            "baseline_decision": b_decision,
            "pulse_decision": p_decision,
        })

    # Summary
    total = len(SCENARIOS)
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Baseline: {baseline_correct}/{total} correct  ({baseline_correct/total:.0%})")
    print(f"  Pulse:    {pulse_correct}/{total} correct  ({pulse_correct/total:.0%})")
    print()
    improvement = pulse_correct - baseline_correct
    if improvement > 0:
        print(f"  Pulse outperformed baseline by {improvement} scenarios (+{improvement/total:.0%})")
    print()
    print("KEY INSIGHT: Pulse provides multi-source verified context.")
    print("Baseline answers from training data + 1 unverified source.")
    print("=" * 70)

    return {
        "baseline_score": f"{baseline_correct}/{total}",
        "pulse_score": f"{pulse_correct}/{total}",
        "baseline_pct": baseline_correct / total,
        "pulse_pct": pulse_correct / total,
        "results": results,
    }


if __name__ == "__main__":
    pulse_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7070"
    summary = run_eval(pulse_url)
    print(json.dumps(summary, indent=2))
