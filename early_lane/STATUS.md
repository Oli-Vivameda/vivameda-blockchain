# Early lane status — 17 October 2026: evidence repair candidate

SOURCE TESTED; OWNER UPGRADE AND NEW LIVE LOG-ONLY VALIDATION PENDING.
Telegram delivery remains disabled. No continuous lane or sender started by engineering.

The owner's completed RPC rollout observed 898 valid polls and 889 priced polls
in 7201.43 seconds, with no poll errors and zero alerts/suppressed candidates.
First-seen candidates totalled 2,893; 89,571 repeated filter evaluations had nine
mandatory fields UNKNOWN. These are transport observations, not a screening pass.
The original live_rollout_pass:true tested prices/feed only and was insufficient.
No real example alerts exist from that run; synthetic examples are not substitutes.

Candidate fixes version-1 Solana transaction fetches, uses 1,000-signature pages,
collects fresh authorities/full holder census before history completion, and uses
authenticated cached creation for independent social/curve/developer checks.
Caches expire; every frozen gate remains fail-closed. History remains complete-only
for buyer growth/share and first-two-block membership. Account results are reused
for at most 40 seconds under the existing 60-second freshness limit.
New heartbeat/receipt counters expose collection failures and distinguish transport
from full screening. Explicit owner-opted-in shared/private chat is supported by
the client without changing delivery.json. Every lane alert includes DEX Screener.

128 lane offline tests passed locally and on server Python 3.12. A live independent
account probe returned authorities PASS, top_holder PASS, complete census true in
two RPC calls. Current public RPC also returned a successful version-1 envelope;
that sampled transaction contained no direct Pump instructions, so it is not a
successful Pump trade-decoder validation. A larger trade-history probe hit RPC
rate limiting; backoff was respected, no provider/endpoint cycling or paid fallback.
A successful version-1 economic buy is covered by an offline authenticated fixture.
No complete live screening path or new two-hour run is claimed yet.

Protected lane state/inbox remain unreadable to engineering; no permissions changed.
The root-only migration accepts installed RPC bundle 41b453fb, verifies exact old
units and both bundles, locks the stopped lane, validates the append-only journal,
and preserves its existing activation/cohorts. It starts nothing. The original
study clock is not reset. Exact persisted review timestamp requires owner report;
if activation was the supplied 17 October run, day-14 review is 31 October 2026,
with a later maturity follow-up for the last day's selections.

Open issues: free-RPC history throughput and complete live eligibility, incomplete
launch-source coverage, new shadow receipt and real eligible examples. Shared 🌻
destination one-shot succeeded earlier; continuous confirmation still disabled.
Scanner, learner, monitors, frozen study, rules and meme desk remain unchanged.
See EVIDENCE_OWNER_COMMANDS.md and EVIDENCE_REPAIR_20261017.md.

Repository release verification: Python 3.12; 1,027 tests /28 suites passed, 405 files verified. Scanner and learner remain active with unchanged source hashes. This verifies source, not deployment or live screening.
