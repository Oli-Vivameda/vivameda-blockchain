> Current status: owner applied the RPC repair and began the new log-only run.
> Startup data/prices were observed; the completed two-hour result is pending.
> Sender source is built and tested, but is not installed or started. See
> [sender handover](sender/ASTRA_HANDOVER.md) and [install-only commands](sender/OWNER_COMMANDS.md).

# Early lane v1

Experimental read-only Pump.fun observer, separate from the scanner. The owner
applied the RPC pricing repair and started a new two-hour log-only run. Supplied
startup logs show fresh input/prices and no selected alerts. Final validation is
pending. Telegram channel remains TBD. The separate sender is built with 46 offline
tests; it is not installed, started or enabled. No trading code, wallet connection,
signup or paid fallback. Meme desk remains paused.

Read [frozen rules](RULES.md), [source/terms check](SOURCE_TERMS.md),
[rollout evidence](ROLLOUT.md), [exact owner commands](OWNER_COMMANDS.md), and
[Astra handover](ASTRA_HANDOVER.md). Three [synthetic examples](EXAMPLES.md) show
formatting only; they are not observed opportunities.

## Components

- `exporter.py`: owner-run mode=ro/query_only SQLite export, column/table allowlist,
  bounded queries; optional explicit refresh of the scanner's same public launch
  endpoint. No source import, database writes or permission changes.
- `pricing.py`: authenticated on-chain SOL curve/PumpSwap marks and fresh verified
  Pyth SOL/USD through public RPC; no website price endpoint or Hermes API.
- `upgrade.py`: checked repair for the stopped initial installation, preserving
  state and requiring live pricing preflight before any unit replacement.
- `sources.py`, `pump.py`, pinned official `*_layout.json`: public RPC history,
  authenticated Pump creation/curve, successful economic trades, first two produced
  blocks, complete holder census reconciled to supply, owner-level concentration,
  mint controls and safe public HTTPS social resolution. Missing, unsupported or
  throttled evidence stays UNKNOWN. Only revoked-authority configurations pass v1.
- `core.py`: fixed predicates, causal growth ranking, rolling six/hour, immutable
  ALERT versus CAP_SUPPRESSED cohorts, one selection/mint ever, hash-chained journal.
- `outcomes.py`: observed checkpoints, peaks/crossings/dead flags, provisional daily
  summaries at 08:00 Asia/Nicosia and activation-relative 14-day/final reviews.
- `service.py`: isolated log-only runner, fair round-robin RPC budget, tracked-mint
  requests prioritized around checkpoint deadlines, volume and coverage receipts.
- `alerts.py`, `transport.py`: disabled-by-default confirmed-new-channel queue with
  retry/late-age marking, optional root-authenticated Unix sender protocol. No direct
  bot API or credential reader in the lane process. The separate [sender](sender/README.md)
  implements this contract with a root Unix socket, durable idempotency/receipts and
  Retry-After. It reads the existing bot credential at runtime only; it never copies
  it or writes delivery configuration. Installation and a test remain owner actions.
- `owner.py`, `verify.py`, `BUNDLE.json`, `install.py`: hash-pinned snapshot execution
  and owner-only installer for NEW lane/export units. Installer enables/starts none.

## Verification

```
python3.12 -B -m unittest discover -s early_lane/tests -v
python3.12 -B -m unittest discover -s early_lane/sender/tests -v
```

Tests never make network calls or send Telegram. Synthetic Runner tests explicitly
use `fixtures=True`, cannot activate the observational clock, and use temporary
state. Real RPC connectivity was probed separately (health/handshake only).

## State and operations

Installed source `/opt/vivameda-early-lane/<bundle-sha256>/` is root owned. Dedicated
user `vivameda-early-lane` owns `/var/lib/vivameda-early-lane/`: append-only
`lane.sqlite3` plus WAL/SHM, mutable `rpc_cache.sqlite3`, bounded `lane.log`,
`tracked.json`, `process.lock`, and `log_only_receipt.json`. Root owns
`/var/lib/vivameda-early-lane-inbox/feed.json` and feed cooldown, readable only to the
lane group; the lane cannot read the protected scanner database. Root-owned
`/etc/vivameda-early-lane/delivery.json` starts unconfirmed. No service reuses the
scanner's chat or changes another unit. Do not remove/reset the journal on promotion:
it holds the one-ever constraint, outcome anchors and activation date.

Disk reserve is 3 GiB. Low disk exits 75 without restart. RPC uses one public endpoint,
maximum 12 calls per poll and one call/sec with persisted Retry-After cooldowns;
response sizes and request timeouts are bounded. The root export timer runs every
20s, with a 55s job timeout. A long pagination/slow feed can fail freshness rather
than fabricate coverage. Logs rotate; append-only journal does not silently prune.

## Limits to resolve before live use

Universal launch coverage is **not established**: the permitted existing feed
excludes NSFW and may be late/gapped; bounded pagination can fail to reach the 30m
boundary. Log discovery delay and coverage instead of claiming every new launch.
The production scanner also does not cover every token after 30m. Free RPC may
block full `getProgramAccounts` census/history, especially at launch volume. This
can leave every candidate UNKNOWN; budget pressure never relaxes a filter.

Market cap is provider-reported at fresh response capture, not an executable quote.
Same-feed per-token refresh continues for tracked cohorts after 30m; 12 requests per
export prioritize checkpoints then stale observations. Dense cohorts or downtime
can miss peaks/checkpoints. Missing liquidity is unknown, never a false zero; the
current provider export does not independently prove a liquidity-drain event, so
dead detection normally relies on the price-collapse limb. Unsupported USDC-quoted,
mayhem or new program layouts fail closed. Successful social HTTP resolution proves
reachability, not authenticity. No verified 24h rug registry exists here: ticker/name
reuse check is explicitly omitted for this frozen version.

Ranking chooses strongest **available now**, not future arrivals later in an hour.
Suppressed cohorts are anchored once and never promoted. Yesterday's 08:00 summary
is provisional; late alerts are immature. Peaks are sampled lower bounds, never
realized profit. All-pass cohort comparisons are exploratory and cannot establish
causal filter value or justify funding; failed-filter outcomes are not collected.

At activation +14 days report the frozen cohort, with final maturation at +15 days
+120s. Activation has not happened, so there is no booked review date yet. If
activation occurs on 17 October 2026, day 14 is 31 October and final follow-up is
1 November +120s at the corresponding UTC time (Cyprus DST can change local hour).
