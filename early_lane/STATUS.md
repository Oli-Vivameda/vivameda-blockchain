# Early lane status — 17 October 2026, 10:22 Cyprus

RUNNING LOG-ONLY; DATA/PRICING OBSERVED; TWO-HOUR VALIDATION IN PROGRESS.

Owner applied bundle 41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d. Upgrade receipt: journal preserved, no scanner change, no service auto-start; live pricing preflight priced 16 of 30 sampled mints. The old HTTP-dependent rollout was stopped with zero valid polls and is not a successful observation.

The repaired exporter succeeded: 644 retained launch rows, zero scanner market snapshots, query_only true and scanner_modified false. Prices now come from the separate permitted public RPC path. Starting the exporter service before its timer resolved the inactive timer on this resumed installation. No source or timer definition was changed for that startup ordering.

Owner then started vivameda-early-lane-rollout-rpc2.service. Supplied logs show 10 valid polls, pricing_issue null, and 129 fresh market marks among 627 tokens in the latest cycle. Selected/suppressed decisions remain 0; Telegram false throughout. These are startup observations, not final hourly counts, a full-screening pass, universal coverage or a completed two-hour rollout. Most watched tokens still lack a fresh mark in that latest cycle. Missing/unsupported evidence remains UNKNOWN; no filter relaxation.

First supplied fresh-data heartbeat: 2026-10-17 07:20:58 UTC (10:20:58 Cyprus). Exact persisted activation must be confirmed from the journal/report; expected review date 31 October if activation is this run. Failed missing-input waits do not count. The new run should finish around 12:21 Cyprus; inspect actual receipt timestamps, duration, valid/priced polls and gaps before accepting it.

No Telegram channel or existing sender confirmed; no execution/signing/keys/paid calls. Scanner, learner, monitors and frozen rules unchanged. Meme desk remains paused. Source release gate: 936 tests across 26 suites, including 109 early-lane tests. Current observation adds no source/threshold changes.

After the run, from the root server terminal:

```bash
cat /var/lib/vivameda-early-lane/log_only_receipt.json
```

Keep runtime rows/logs private. Publish aggregates and limitations. See OWNER_COMMANDS, ROLLOUT and ASTRA_HANDOVER.

## Sender source prepared — 17 October 2026

The separate sender/ package implements the existing root Unix-socket contract,
durable idempotency and Telegram receipts, persisted Retry-After, exact configured
channel enforcement and scanner-chat exclusion. 46 new offline tests; source only.
NOT installed, started or enabled. No Telegram message sent, credential contents
read by engineering, delivery.json change or lane executable-bundle change.
The current log-only run and its pending result remain as reported above.
See [sender handover](sender/ASTRA_HANDOVER.md) and the
[owner install-only/test commands](sender/OWNER_COMMANDS.md). The new numeric channel
and separately authorized configuration are still missing. Uncertain network sends
are held for owner review, never automatically resent. Repository gate: 982 tests
across 27 suites, including 109 lane tests and 46 sender tests.

Owner installation attempt stopped before writes at the credential ownership check.
Metadata confirms the existing scanner owns its 0600 credential. Corrected sender
bundle accepts root or vivameda-scout owner-only files, preserves that file, and
retains root-only delivery config checks. 46 sender tests / 982 repository tests.
Sender installation and real channel test remain pending; nothing was started.
