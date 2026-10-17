# Rollout observations — 17 October 2026

## Owner-confirmed running observation — 17 October 2026, 10:22 Cyprus

Owner applied the checked RPC repair (41b453fb), preserving the journal; preflight obtained 16/30 prices. Repaired exporter succeeded with 644 retained launch rows. After starting the exporter service before its timer, the new vivameda-early-lane-rollout-rpc2.service produced 10 valid polls, pricing_issue null and 129 fresh market marks among 627 watched tokens in the last supplied cycle. Selected/suppressed decisions 0; Telegram false. This confirms startup data/pricing, not full screening, complete coverage, 10x performance or the completed 7200-second result. The exact persisted activation and final receipt still need inspection. First supplied heartbeat is 07:20:58 UTC; expected finish around 12:21 Cyprus. Review is activation+14 days, expected 31 October if confirmed. No scanner/rules changes or Telegram destination/sender confirmation. Earlier sections describe their dated preparation/failure, superseded by this owner receipt.


The initial source was installed by the owner. The subsequent log-only run failed:
Pump.fun HTTP 403 prevented the exporter writing any input; 0 valid polls and no
Telegram. Owner stopped both early-lane rollout and export timer. This is NOT a
successful two-hour run or measured zero-alert performance. A scanner-only
query_only export returned 597 launch rows and 0 fresh price snapshots.

A separate RPC-pricing repair is prepared and offline-tested, NOT applied. See
SOURCE_REPAIR.md and OWNER_COMMANDS.md. Its root preflight must obtain authenticated
live marks before unit changes; full screening and a new 7200-second log-only run
are still required. Frozen rules, journal, scanner and studies remain unchanged.
The review clock has not started. Three examples remain synthetic only.
