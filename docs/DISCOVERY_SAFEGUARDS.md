# Discovery safeguards

Dated deployment: 16 October 2026. [Source](../scout/early_scout.py), [tests](../scout/test_discovery_guard.py), [release evidence](releases/2026-10-16-discovery.md).

Each feed saves validated rows before another request. Malformed rows are excluded individually while valid rows continue; persistent partial ingestion remains visible. Empty or stale responses cannot manufacture fresh coverage.

Ordinary errors have a per-feed retry delay. HTTP 401/403/429 suspend further requests to that host for five minutes. Existing market/scoring work continues after the bounded acquisition cycle.

## Catch-up and measurement

Loss of creation-page overlap starts a backward scan with ten-row overlap and actual returned page sizes. Bounds: one extra page per pass, at least 30 seconds between extras, offset at most 10000, target lookback at most six hours, and at most one hour per scan. Empty, invalid or non-progress pages leave recorded gaps. Later success does not erase an unrecovered gap.

First activation establishes a forward anchor and does not certify prior coverage. Recovered coins retain actual local first-seen times. Measurements include new token counts, rejected rows, maximum ingestion delay and first-seen age buckets: within 30 minutes, 30 minutes to six hours, over six hours.

## System warnings

At least three minutes without fresh valid ingestion or with persistent malformed rows produces a system-level warning. Unrecovered gaps and catch-up lasting five minutes are also reported. Reminders are at most hourly, with at least ten minutes between notification attempts, including recovery. Throttling survives restarts.

Coin-specific watchlist movement and pool-status routes retain their separate mutes. The warning runs inside the scanner, so it cannot report when that process is stopped. Existing service monitoring remains necessary. Telegram outages can prevent delivery. Failed health-record persistence leaves local errors and suppresses sends to avoid a restart flood.

## Evidence and limits

Retained postflight logs showed both feeds saving data. Forty-one offline tests cover failure isolation, malformed rows, cooldowns, catch-up, timestamps and notifications. The original release also passed 13 transport and 10 stack checks.

The [contract](../scout/discovery_function_contract.json) records AST hashes for 60 original functions preserved from the reviewed pre-release source, including selection, scoring, screening and study functions. It is checked against the one canonical source.

Catch-up effectiveness, actual outage-alert latency, complete coverage and profitable trades remain unproven. Provider pagination is not a stable snapshot. Runtime health and future results require forward observation.
