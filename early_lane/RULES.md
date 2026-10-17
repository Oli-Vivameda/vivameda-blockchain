# Early lane v1 — frozen 14-day rules

Freeze this file in Git BEFORE any experimental alert, including log-only selection.
No signing, wallet connection, keys, signup, trades, paid calls or direct bot API.
New early_lane/ source/state only; do not modify scanner, monitors, studies or services.

## Sources, coverage and frozen omissions

Use an owner-run hash-checked mode=ro/query_only export of the scanner's launch feed
and retained market snapshots, plus read-only public Solana RPC. Never import the
scanner process, alter its database permissions, or read prediction/journal tables.
The existing launch discovery excludes NSFW results and can be late/gapped. Watch
EVERY exported new Pump token until 1800 seconds after actual creation, logging late
arrival and feed gaps; do not claim universal launch coverage that this source does
not establish. Continue outcome monitoring for selected/suppressed cohorts to 24h.
Public RPC throttling, missing history and unsupported layouts are recorded, never
silently filled. No paid endpoint fallback, account creation, IP rotation or keys.

PumpPortal is NOT enabled: its documented trade streams are metered and require a
funded wallet/API key; its terms restrict distribution absent authorization. No
optional third-party feed is used. SOURCE_TERMS.md records the primary sources.

Rug-name/ticker reuse rule is explicitly OMITTED for this frozen version: there is
no verified complete 24-hour rug registry from permitted sources. A price collapse
is not proof of a scam. Do not invent a registry or add this rule mid-experiment.

## Eligibility — every enabled rule must PASS, UNKNOWN never passes

All facts must refer to the same exact mint/chain and actual decision time, with
original observation timestamps, evidence hashes and no future data. Market/holder/
authority facts max age 60 s. Complete successful trade history from verified mint
creation through the current head is needed for buyer counts and first-block union.
No transfers/airdrops/failed transactions counted as buys. Unsupported relevant swaps,
transaction gaps, incomplete holder census or unverifiable developer => UNKNOWN.

1. Age >=0 and <=1800 s; market cap USD inclusive $8,000–$25,000.
2. Authenticated bonding curve still incomplete, OR authenticated graduation event
   at/before now and <=300 s old. Never infer graduation time from first-seen alone.
3. Developer's CURRENT aggregate wallet holdings <5% of current mint supply.
4. Union of developer AND every successful buyer in the first TWO PRODUCED Solana
   blocks (creation block plus next produced block, not assumed slot+1) holds <15%.
   Deduplicate overlapping wallets; include all token accounts owned by each wallet.
5. Largest single non-curve HOLDER, aggregated by owner, <=8% of supply. Exclude only
   authenticated bonding-curve/AMM vault ownership, not arbitrary exchange labels.
   Require full token-account census and supply reconciliation; top-20 is insufficient.
6. Cumulative unique successful buyers since creation >=25, AND >=50% growth versus
   that cumulative count exactly 300 s earlier. Need a full five-minute lookback and
   positive baseline: zero/missing baseline is UNKNOWN, never infinite growth. Thus
   this rule cannot qualify a token younger than five minutes in v1.
7. Successful buys / (buys+sells) in (now-300,now] >=60%; no trades => UNKNOWN.
8. Mint AND freeze authority revoked, or independently authenticated standard Pump
   configuration. V1 only passes observed revoked authorities on supported classic
   Token/standard metadata-only Token-2022 mint layouts; unsupported exceptions stay
   UNKNOWN. No self-asserted 'standard' flag may pass.
9. At least one metadata-origin X, Telegram or website HTTPS link resolves with an
   observed successful HTTP status/validated redirect. Preserve URL/time; missing,
   private IP, local URL, login/error/blocked response or timeout is not PASS. Validate
   each redirect, public DNS/IP, bounded response; do not send credentials.
10. One experimental alert selection per mint EVER, including restarts and modes.
11. At most SIX selections in ANY rolling 3600 s. Each decision microbatch ranks
    fully eligible candidates by unique-buyer growth descending, then unique count,
    then mint. Select strongest among currently available quota; remaining eligible
    mints are recorded once as CAP_SUPPRESSED. No future information or hour-long
    delay to pick the globally strongest unseen token. Later stronger arrivals cannot
    retract earlier alerts. Suppressed cohort is fixed at first eligible decision,
    never promoted later; it is tracked separately. Failed filters are not the cap-
    suppressed cohort. Record sequential/pass-each gate counts and suppression reasons.

Rules/thresholds/source omissions are immutable from this commit through the first
verified observational activation plus 14*86400 seconds. Activation is the first
successful fresh live-input polling cycle in the observational state (including
approved log-only rollout), not a unit process
start, fixture, missing-input wait or unconfirmed queued job. Persist its timestamp.
No automatic changes after review. Changed rules require a separately frozen version.

## Outcomes — append only, actual observations only

Anchor each ALERT or CAP_SUPPRESSED cohort at its decision timestamp and observed
market cap. Horizons are +5,+15,+30,+60,+360,+1440 minutes. Choose nearest actual
observation within +/-120 s, earlier timestamp on ties; finalize only once target
+120 s is due. No interpolation, retroactive provider ATH or late backfill after
finalization. Missing remains missing; never substitute zero or 'no winner'.

Track observed peak cap and time-to-peak within (anchor,anchor+24h], plus the anchor;
first observed crossings of >=2x,3x,5x,10x. A dead flag is an observed cap strictly
<30% of anchor OR positive evidence of liquidity gone; missing liquidity is UNKNOWN.
Price collapse/dead is not proof of fraud. All observations, decisions, milestones,
checkpoints, flags, delivery attempts and summaries append to the lane's own hash-
chained SQLite journal. Deduplicate event IDs; never overwrite previous evidence.
Sampling gaps mean 'first observed', not first on-chain; peaks can be missed.

## Summaries and go/no-go

At 08:00 Asia/Nicosia (DST-aware) summarize yesterday's decision cohorts: count,
observed threshold counts and dead count, observed median time-to-peak, plus the
cap-suppressed 10x rate with explicit denominator/coverage. Yesterday's late alerts
are not all 24-hour mature at 08:00: label provisional/incomplete, never failed.
Footer: small sample; observed peak multiples, not realized profit.

At activation+14 days produce the frozen-cohort review: all selected/suppressed
counts, observed 2x/3x/5x/10x rates, dead rate, median time-to-peak and completeness.
Last-day cohorts need a further 24h+120 s to mature; day-14 report is provisional,
with a final locked-cohort follow-up after maturation. Show 10x/ALL selections as a
conservative observed rate and 10x/mature-covered selections separately. Ten percent
is the owner's DESCRIPTIVE benchmark; do not assert evidence of it with immature,
incomplete or tiny samples. No automatic funding, trading or filter change. Per-
filter winner/loser separation is post-hoc EXPLORATORY; selection bias/correlation
preclude causal claims. Retain failed-filter audit for exploratory comparison only
where actual comparable outcomes were separately observed; otherwise not estimable.

Channel TBD. No Telegram until a new channel and an existing authenticated sender
are confirmed. Experimental footer is mandatory on every eventual alert:
EXPERIMENTAL early alert. Not safety-screened like scanner alerts. Most early tokens fail.
