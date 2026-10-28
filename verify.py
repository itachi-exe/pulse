#!/usr/bin/env python3
"""
Verify a Pulse regulatory snapshot yourself. Standard library only.

    python verify.py               # today (UTC)
    python verify.py 2026-10-28

It downloads the day's items from Pulse, recomputes every sha256 locally,
rebuilds the day's digest, then reads the anchor transaction straight from
the chain's public RPC and checks the digest written there. Pulse's own
"verified" field is ignored: every check happens on your machine.
"""
import hashlib, json, sys, urllib.request
from datetime import datetime, timezone

PULSE = "https://getpulsedata.online"

def get(url, body=None):
    req = urllib.request.Request(url, json.dumps(body).encode() if body else None,
                                 {"Content-Type": "application/json", "User-Agent": "pulse-verify/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=30))

def item_hash(a):
    canon = json.dumps({k: a.get(k, "") for k in ("feed", "title", "url", "published")},
                       sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()

def main():
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap = get(f"{PULSE}/data/regulatory/snapshot/{day}")
    items = snap["items"]

    bad = [it["title"] for it in items if item_hash(it) != it["sha256"]]
    digest = hashlib.sha256("".join(sorted(it["sha256"] for it in items)).encode()).hexdigest()
    print(f"{day}: {len(items)} items")
    print(f"  item hashes recomputed   {'ok' if not bad else f'{len(bad)} MISMATCH'}")
    print(f"  day digest rebuilt       {'ok' if digest == snap['digest'] else 'MISMATCH'}  {digest[:16]}…")

    oc = snap.get("onchain")
    if not oc:
        print("  on-chain anchor          not anchored yet (anchors are written at 23:55 UTC)")
        sys.exit(0 if not bad and digest == snap["digest"] else 1)

    # Public RPC for the chain named in the anchor. Not Pulse.
    rpc = {16602: "https://evmrpc-testnet.0g.ai", 8453: "https://mainnet.base.org"}[oc["chain_id"]]
    tx = get(rpc, {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionByHash", "params": [oc["tx"]]})["result"]
    written = bytes.fromhex(tx["input"][2:]).decode()
    chain_ok = written == f"PULSE-REG:v1:{day}:{digest}"
    print(f"  on-chain anchor          {'ok' if chain_ok else 'MISMATCH'}  block {int(tx['blockNumber'], 16)}")
    print(f"  written on chain:        {written}")
    print(f"  explorer:                {oc['explorer']}")
    ok = not bad and digest == snap["digest"] and chain_ok
    print("VERIFIED" if ok else "NOT VERIFIED")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
