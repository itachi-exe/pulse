#!/usr/bin/env python3
"""
Try to tamper with a sealed Pulse day and watch the check catch it.
Standard library only, nothing is written anywhere.

    python tests/tamper_demo.py 2026-10-28

It downloads a sealed day, edits one headline in memory and runs the same
checks as verify.py twice:
  1. a plain edit, which the item hashes catch and name;
  2. a cover-up that also rewrites the item hash and the day digest, so the
     local data looks clean, which the on-chain anchor still catches.
"""
import hashlib, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from verify import PULSE, get, item_hash  # noqa: E402


def digest_of(items):
    return hashlib.sha256("".join(sorted(it["sha256"] for it in items)).encode()).hexdigest()


def main():
    day = sys.argv[1] if len(sys.argv) > 1 else "2026-10-28"
    snap = get(f"{PULSE}/data/regulatory/snapshot/{day}")
    oc = snap.get("onchain")
    if not oc:
        sys.exit(f"{day} is not anchored yet, pick an anchored day")
    rpc = {16602: "https://evmrpc-testnet.0g.ai", 8453: "https://mainnet.base.org"}[oc["chain_id"]]
    tx = get(rpc, {"jsonrpc": "2.0", "id": 1, "method": "eth_getTransactionByHash", "params": [oc["tx"]]})["result"]
    on_chain = bytes.fromhex(tx["input"][2:]).decode()

    items = [dict(it) for it in snap["items"]]
    target = next((it for it in items if it["feed"].startswith("SEC")), items[0])
    old = target["title"]
    target["title"] = old + " (withdrawn)"

    print(f"day:        {day}, {len(items)} sealed items")
    print(f"edit:       '{old}'")
    print(f"        ->  '{target['title']}'")
    print()
    bad = [it["title"] for it in items if item_hash(it) != it["sha256"]]
    print("1. plain edit")
    print(f"   item hashes:  {len(bad)} broken -> {bad[0] if bad else 'none'}")
    print(f"   verified:     {not bad}")
    print()
    target["sha256"] = item_hash(target)
    fake = digest_of(items)
    bad = [it["title"] for it in items if item_hash(it) != it["sha256"]]
    chain_ok = on_chain == f"PULSE-REG:v1:{day}:{fake}"
    print("2. cover-up: item hash and day digest rewritten")
    print(f"   item hashes:  {'all ok, looks clean' if not bad else 'broken'}")
    print(f"   new digest:   {fake[:16]}…")
    print(f"   on chain:     {on_chain.split(':')[-1][:16]}…  ({'match' if chain_ok else 'MISMATCH'})")
    print(f"   verified:     {chain_ok and not bad}")


if __name__ == "__main__":
    main()
