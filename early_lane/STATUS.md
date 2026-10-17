# Early lane status — source repair, 17 October 2026

INITIAL BUNDLE INSTALLED; EXPERIMENT STOPPED; REPAIR PREPARED, NOT APPLIED.

The owner installed d3811acb, then launched log-only. The public Pump.fun endpoint
returned HTTP 403/Cloudflare, so the exporter never wrote a feed. Owner output
showed 0 valid polls. Owner stopped only early-lane jobs; engineering read-only
systemd checks confirm the timer and rollout inactive. Scanner/learner remain active.
A scanner-only diagnostic export returned 597 recent launches, 0 market snapshots.

The prepared repair uses that approved discovery export and independently reads
Pump curve/PumpSwap vault marks with a fully verified, fresh on-chain SOL/USD Pyth
feed through public Solana RPC. No website price refresh, keys, accounts or paid
calls. Frozen RULES and screening thresholds unchanged. 109 local tests pass; see
the dated release for final server/full-suite checks. Owner upgrade preflight must
obtain live prices before any unit change, otherwise aborts. No real screening or
successful two-hour rollout has been established; no alert/outcome result exists.

Remaining limits: NSFW-excluded discovery, public-RPC completeness/throughput,
unsupported USDC/mayhem/boost pools, metadata reachability, full-history freshness,
new Telegram channel TBD and compatible authenticated sender absent. Journal is
preserved; missing prices cannot start the observation clock or pass the rollout.
See SOURCE_REPAIR, OWNER_COMMANDS and ASTRA_HANDOVER.
