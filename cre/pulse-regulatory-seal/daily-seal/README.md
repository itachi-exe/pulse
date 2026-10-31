# Pulse daily seal, a Chainlink CRE workflow

Every night at 23:30 UTC this workflow reads the day's seal from the Pulse Regulatory & Legal feed. Each node in the Chainlink DON fetches it on its own, and the result only counts when the nodes agree on the exact same digest. One node, or one bad fetch, cannot change what the day's record says.

## What it does

1. **Cron trigger** at `0 30 23 * * *` (23:30 UTC, daily).
2. **HTTP fetch** of `https://getpulsedata.online/data/feed/regulatory` and reads `data.snapshot` (digest, item count, time, verify path).
3. **Identical consensus** (`consensusIdenticalAggregation`): the nodes must return the same record.
4. **Returns the agreed seal**: day, sha256 digest, item count and the path to verify it.

The verify path (`/data/regulatory/snapshot/<day>`) returns that day's items, the same digest and its on-chain anchor status, so anyone can check the agreed seal against the record Pulse anchors (`PULSE-REG:v1:<day>:<digest>`, see the main [README](../../../README.md)).

## Run it

Needs the [CRE CLI](https://docs.chain.link/cre) and [bun](https://bun.sh). The workflow writes nothing on-chain, so any dummy key works for the simulator.

```bash
cd cre/pulse-regulatory-seal
echo "CRE_ETH_PRIVATE_KEY=0000000000000000000000000000000000000000000000000000000000000001" > .env
(cd daily-seal && bun install)
cre workflow simulate daily-seal -T staging-settings -e .env --non-interactive --trigger-index 0
```

Real output from a run on 2026-10-31:

```text
[USER LOG] Pulse seal run | triggered_at=2026-10-31T07:12:20.849Z
[USER LOG] Fetching | https://getpulsedata.online/data/feed/regulatory
[USER LOG] Seal confirmed | day=2026-10-31 digest=b87f88d147e3c473... items=80
```

```json
{
  "pulse_seal": {
    "day": "2026-10-31",
    "digest": "b87f88d147e3c473948dd9bcb57616a655b4122c961520ed5e4a47b3c6cb2253",
    "items": 80,
    "feed": "regulatory",
    "verify_path": "/data/regulatory/snapshot/2026-10-31",
    "fetched_at": "2026-10-31T07:06:37.373085+00:00"
  },
  "workflow": "pulse-daily-regulatory-seal",
  "triggered_at": "2026-10-31T07:12:20.849Z"
}
```

## Deploy

```bash
cre workflow deploy daily-seal -T production-settings -e .env
```

Deploy needs Chainlink to enable deployment access for the organization (requested).

## Files

| File | What it is |
|---|---|
| `daily-seal/main.ts` | The workflow: cron trigger, HTTP fetch, consensus |
| `daily-seal/config/config.production.json` | Schedule, Pulse API base URL, feed key |
| `daily-seal/workflow.yaml` | Staging and production targets |
| `project.yaml` | RPC settings for the CRE CLI |
