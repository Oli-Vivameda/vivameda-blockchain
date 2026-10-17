# Current rollout record — 17 October 2026

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
