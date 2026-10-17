# Meme desk v1 exit replay — preregistration

Version 1, 17 October 2026. Commit this document before any replay computation.
No case outcomes, protected results or model probabilities were inspected to design
this protocol. Only source code/schema and bounded service status were inspected.
The owner-run read-only exporter is the sole scanner-data access mechanism.

## Population and information boundary

Exclude EVERY mint in pl_predictions using membership only (mint column). Never
read pl_results, prediction values, probabilities, v2_outcomes or the frozen journal.
Use the earliest retained v2_cases source=ALERT row per development mint, ordered
by decision_ts then id. Never select a later better-screened alert. Exclude SHADOW
and LEDGER_ALERT. Require a screening review at/before that alert, at most 300 s
old, identity-bound to mint/solana/pair, with observed_at and nonempty evidence_refs
for each mandatory PASS. Freeze the scanner's actual mandatory set:
token_controls, liquidity_control, trading_mechanics. Any explicit REJECT in ANY
check blocks eligibility. Background UNKNOWNs remain explicit; do not relabel PASS.
This is not the learning journal's separate seven-PASS ENTER_REVIEW policy and does
not change either existing policy. Current scanner source hash at inspection:
6790a2c192bbdecfcd17abbe6f41f774675f059e5fab52edb0b6b2ab99b4dbf1.

Require an observed price snapshot at/after alert+3600 s and within 180 s of that
checkpoint. Cases failing screening or 60-minute coverage are counted as exclusions,
not silently dropped from denominator descriptions. Regime is the retained Learning
V2 case regime: CONTINUATION, COMPRESSION, RECLAIM, otherwise OTHER. Score bands
8–9 and 10+ are reported; below-8/missing are reported separately, not silently
excluded. Features/regimes may be retrospective reconstructions; no causality claim.

## Entry, costs, exits and missingness

Entry is the first snapshot at/after alert+60 s, no more than 180 s late. Size is
$10 swap notional, PLUS $0.10 fee and $0.05 network at entry: initial outlay $10.15.
Use authenticated constant-product reserves contemporaneous with that snapshot:
X = human token reserve, Y = quote reserve valued in USD. Bought tokens are
X*10/(Y+10). This incorporates price impact once, not as a second deduction.
For sale quantity q, gross dollars are Y*q/(X+q), then subtract 1% swap fee and
$0.05 network PER executed sale leg. Half-target plus final exit therefore incurs
three network charges including entry. Fees are modeled externally, not inside
both the AMM formula and a separate deduction. Ignore hypothetical self-impact on
later observed historical reserves: this is a small-trade replay approximation.

Plan A: sell HALF of bought tokens at +40%; stop ALL unsold tokens at -25%; time
exit all unsold at 45 minutes. Plan B: half at +25%, stop -20%, time 30 min.
Plan C: half at +100%, stop -35%, time 120 min. Stop/target levels reference the
entry SNAPSHOT price, not the impacted execution price. Stops remain at the original
entry level after the half sale: no breakeven/trailing substitution. Holding times
start at actual entry snapshot time. A stop before the target sells all inventory.

At each observed snapshot on/before the deadline, apply stop then the as-yet-unhit
half target. Fill at that actual snapshot price via its authenticated reserves,
NEVER at the threshold. Record signed observed-price overshoot vs target/stop and
actual fill lateness. A time exit uses the FIRST snapshot strictly AFTER deadline,
no more than 180 s late; once past deadline, time exit takes priority. No interpolation.
Any gap >180 s while inventory is open makes the case unresolved, including an
entry/required exit with missing/invalid reserves, missing price, duplicate conflicting
snapshots, different pair, non-constant-product pool or unauthenticated evidence.
If a target/stop resolves C earlier, 120-minute coverage is unnecessary; otherwise
C lacking its required time exit is unresolved despite the cohort's 60-minute gate.
Partial proceeds from an unresolved remainder do not become a completed win.

Reserves must match mint/chain/pair, authenticated pool/vault relationships, original
observation time and provenance references. Reserve and any USD conversion observation
must be at/before the price snapshot, at most 180 s old. For live tickets the limit
is 30 s. Use only supported constant-product pools and positive finite reserves;
require reserve-implied USD token price within 3% of observed snapshot price.
A boolean flag or displayed liquidity alone is not authentication. Historic rows
without proof remain unresolved; current reserves cannot backfill history.

## Aggregates and interpretation

For each plan report eligible case count, resolved/unresolved count and reasons,
win rate among resolved (net PnL>0), average positive/negative dollar PnL, largest
single loss, total and mean net PnL and mean PnL/$10 notional after all costs.
Report the same after removing the five highest-PnL resolved cases; if <=5 resolved,
report N/A. Report every regime, score band and fixed chronological half. Sort the
eligible cohort by alert time then mint; first floor(N/2) is early, remainder late.
Do not re-split separately after unresolved cases are removed. Report per-stratum
unresolved counts; empty cells are N/A, never zero-performance claims.

Public REPLAY_RESULTS.md contains AGGREGATES ONLY, no mints, private cases, model
probabilities, examples from protected cohorts or raw price/reserve paths. Private
replay rows, traces and input exports stay on server. Zero eligible cases, missing
reserves and negative results are valid outcomes. Snapshot replay is not a real fill,
execution quote, independent population sample or validated recommendation. These
three fixed comparisons are descriptive; no optimized winner or statistical
significance claim. Freeze new protocols separately before changing assumptions.
