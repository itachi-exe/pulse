#!/usr/bin/env python3
"""
Anchor a day's sealed regulatory snapshot on-chain.

Writes one transaction from the Pulse anchor wallet to itself, with the
calldata  PULSE-REG:v1:<day>:<digest>  so anyone can read the day's seal
straight off a block explorer, without trusting Pulse.

Usage:  anchor.py            anchor today (UTC)
        anchor.py 2026-10-28 anchor a given day
Runs once per day from cron. Already-anchored days are skipped.
"""
import json, os, sqlite3, sys, time, urllib.request
from datetime import datetime, timezone
from eth_account import Account

HERE = os.path.dirname(os.path.abspath(__file__))

def load_env():
    p = os.path.join(HERE, ".env")
    if os.path.exists(p):
        for line in open(p):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def rpc(url, method, params):
    req = urllib.request.Request(url, json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                 {"Content-Type": "application/json", "User-Agent": "pulse-anchor/1.0"})
    out = json.load(urllib.request.urlopen(req, timeout=20))
    if "error" in out:
        raise RuntimeError(out["error"])
    return out["result"]

def main():
    load_env()
    key = os.environ["PULSE_ANCHOR_KEY"]
    url = os.environ.get("PULSE_ANCHOR_RPC", "https://evmrpc-testnet.0g.ai")
    explorer = os.environ.get("PULSE_ANCHOR_EXPLORER", "https://chainscan-galileo.0g.ai/tx/")
    chain_name = os.environ.get("PULSE_ANCHOR_CHAIN_NAME", "0G Galileo testnet")
    db_path = os.environ.get("DB_PATH", os.path.join(HERE, "pulse.db"))
    day = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Make sure there is a fresh snapshot for today before sealing it.
    if day == datetime.now(timezone.utc).strftime("%Y-%m-%d"):
        try:
            urllib.request.urlopen("http://127.0.0.1:7072/data/feed/regulatory", timeout=120).read()
        except Exception as e:
            print("warn: refresh failed:", e)

    db = sqlite3.connect(db_path)
    db.execute("""CREATE TABLE IF NOT EXISTS reg_anchors (
        day TEXT PRIMARY KEY, fetched_at TEXT NOT NULL, digest TEXT NOT NULL,
        chain_id INTEGER, chain_name TEXT, rpc TEXT, explorer TEXT,
        address TEXT, tx TEXT NOT NULL, block INTEGER, anchored_at TEXT)""")
    if db.execute("SELECT tx FROM reg_anchors WHERE day=?", (day,)).fetchone():
        print(f"{day} already anchored"); return
    snap = db.execute("SELECT fetched_at, digest FROM reg_snapshots WHERE day=? ORDER BY fetched_at DESC LIMIT 1", (day,)).fetchone()
    if not snap:
        print(f"no snapshot for {day}"); sys.exit(1)
    fetched_at, digest = snap

    acct = Account.from_key(key)
    data = f"PULSE-REG:v1:{day}:{digest}".encode()
    chain_id = int(rpc(url, "eth_chainId", []), 16)
    nonce = int(rpc(url, "eth_getTransactionCount", [acct.address, "pending"]), 16)
    gas_price = int(rpc(url, "eth_gasPrice", []), 16)
    tx = {"to": acct.address, "value": 0, "data": "0x" + data.hex(), "nonce": nonce, "chainId": chain_id, "gasPrice": gas_price}
    tx["gas"] = int(int(rpc(url, "eth_estimateGas", [{"from": acct.address, "to": acct.address, "data": tx["data"]}]), 16) * 1.2)
    signed = acct.sign_transaction(tx)
    raw = getattr(signed, "raw_transaction", None) or signed.rawTransaction
    tx_hash = rpc(url, "eth_sendRawTransaction", ["0x" + raw.hex().removeprefix("0x")])

    receipt = None
    for _ in range(60):
        receipt = rpc(url, "eth_getTransactionReceipt", [tx_hash])
        if receipt: break
        time.sleep(2)
    if not receipt or int(receipt["status"], 16) != 1:
        print("anchor tx failed or not mined:", tx_hash); sys.exit(1)

    db.execute("INSERT INTO reg_anchors VALUES (?,?,?,?,?,?,?,?,?,?,?)",
               (day, fetched_at, digest, chain_id, chain_name, url, explorer, acct.address,
                tx_hash, int(receipt["blockNumber"], 16), datetime.now(timezone.utc).isoformat()))
    db.commit()
    print(f"anchored {day} digest {digest[:16]} -> {explorer}{tx_hash}")

if __name__ == "__main__":
    main()
