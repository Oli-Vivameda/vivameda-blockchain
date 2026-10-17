# Stream shadow source: build handover

1. Purpose: a standalone public Solana PubSub capture component for early lane.
   It is a source candidate, not a production history replacement or an alert feed.
2. Files: stream_wire.py (bounded TLS/RFC6455 transport), stream_events.py (Pump
   emitted-event normalizer), stream_capture.py (private mutable cache, audit,
   RPC recovery boundary), tests/test_stream.py and STREAM_PROTOCOL.md.
3. Sources: one fixed public Solana websocket; confirmed Pump program-mention logs
   plus finalized roots. No credentials, signup, wallet, transaction submission,
   paid feed, endpoint rotation or scanner import. Standard-library implementation.
4. Evidence contract: validate subscription IDs, successful transaction status,
   program invocation stack, pinned methods/events, economic amounts, event count
   and timestamps. Creation/signer facts remain provisional pending full transaction
   authentication. Exact originals are not inferred from names or mutable fee fields.
5. Coverage: malformed/unknown or unlocatable records and transport loss cause global
   gaps. When every affected mint can be established from a complete transaction's
   emitted events, scope the error to ALL those mints. Never count unsupported/zero
   economic events. Restart opens a new coverage generation. A stop closes coverage.
6. Recovery: require the unchanged Collector.history complete RPC contract, original
   creation consistency, full decoded rows, fresh snapshot after the gap, and exact
   overlap parity including signature/event/participant/amounts. Recovery proves only
   that snapshot. Later gaps invalidate it. Nothing promotes unverified stream data.
7. State: caller-chosen private directory, stream_cache.sqlite3 (mutable bounded
   thirty-minute cache plus margin), stream_audit.sqlite3 (append-only hash chain),
   stream_process.lock and stream_receipt.json. This never opens or writes lane.sqlite3,
   scanner databases, frozen prediction data, journals or credential files. Raw rows
   and live receipts must stay private and must not be added to this repository.
8. Tests: isolated offline tests cover transport framing/masks/fragmentation/timeouts,
   bounds and HTTP Retry-After; spoofed/missing/truncated events; duplicates/conflicts;
   durable gaps/restarts; cache expiry; incomplete/stale/conflicting RPC recovery;
   mint-local scope; and refusal to produce frozen history PASS from provisional data.
   Test directories remain isolated in scripts/verify_release.py; Python 3.12 required.
9. Runtime: source only. No existing service unit, installer bundle, scanner, ledger,
   frozen rule, original activation or delivery configuration is changed. Current
   owner.py bundles do not contain this new source. CLI capture is explicitly bounded
   to 1–600 seconds and always shadow-only. It never imports a Telegram sender.
10. Open gates: authenticate original creations; establish full trade-history coverage
    and ordering through current head; support AMM or retain strict RPC fallback;
    compare against complete RPC snapshots on exported eligible mints; integrate only
    after provenance/freshness/gap checks pass. Continuous/filtered notifications and
    small parity samples do not prove universal coverage. Existing rules/populations
    remain unchanged; no history_complete or screening admission shortcut is enabled.

Every normalized stream event/report/recovery carries admissible_for_screening=false.
The component is intentionally unable to turn stream-only observations into alerts.
See STREAM_PROTOCOL.md for the precommitted validation boundary and source limits.

Public source release verification: Python3.12,1,081 tests across28 isolated suites passed;411 files verified. This includes54 new stream tests. The engineering lane has18 additional pending queue-repair tests outside this public source candidate.

RPC recovery currently retains the cost of complete legacy history backfill. Automatic transaction-level refill and the runtime screening adapter are not implemented. End-to-end full-history equivalence, live recovery and eligible-alert generation remain unverified; stream capture performance does not establish them.
