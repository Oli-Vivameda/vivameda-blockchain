# Astra handover — early-lane evidence repair, 17 October 2026

1. Goal: repair nine UNKNOWN screening fields after the owner's actual two-hour
   rollout. Changes confined to early_lane/ and release bookkeeping. Source only;
   runtime deployment and screening validation remain pending.
2. Evidence: owner's receipt 898 valid /889 priced polls, duration 7201.43s,
   2,893 first-seen candidates, 89,571 evaluations, zero selected/suppressed/sent.
   Every non-age/non-market-cap field UNKNOWN. Original pass was transport only.
   Protected scanner and lane state were not opened by engineering.
3. Causes: live RPC rejects version-1 transactions under the prior version-0
   ceiling. The monolithic collector gated authorities/census/social behind full
   history; its 100-signature pages amplified backlog. This establishes code and
   public-source failures, not the exact frequency of each failure in owner state.
4. Implementation: sources.py requests maximum version1 and pages1000; pump.py
   explicitly accepts legacy/0/1 and rejects unknown versions. New evidence.py
   independently authenticates account/census facts, supply/context reconciliation,
   original creator and fresh resolved socials while history catches up. No stale
   input PASS survives refresh. Full history still required by the frozen gates.
   service.py exposes stage failures/full evaluations and separates rollout gates.
   alerts.py adds DEX Screener. transport.py supports the owner's explicit shared
   chat opt-in while requiring normal confirmation and the root sender guard.
5. Tests: 128 offline lane tests passed on local/server Python3.12 (19 additional
   tests), including v1 economic buy, future-version refusal, resumable history,
   supply mismatch/stale census, partial facts without history PASS, stale refresh,
   creator mismatch, activated-journal preservation, transport-only receipt refusal,
   shared destination configuration and DEX link. No tests send Telegram.
6. Live probes: public RPC provided full Token-2022 census and successful version1
   envelope. Repaired independent account collection produced authorities PASS and
   top_holder PASS with reconciled complete census in two requests. No direct Pump
   trade was present in that v1 sample. A further history probe hit throttling;
   no retry/endpoint cycling while cooldown active. Private probe rows stay server
   side, outside publication. Full live screening remains unverified.
7. Integrity: bundle 0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91; owner.py d97bb8e4474418b8ba5d02bdf41f1e97e575d91e9290fdca78b79db9d79d5c47.
   BUNDLE.json lists every executable/test file hash. RULES.md remains
   ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463;
   preregistration commit 959cdebdea5107f48bcc03b16c3968b34dc24fbe unchanged.
   Runtime still old bundle41b453fb. Existing sender40c80bc0 stays stopped/disabled.
8. Owner commands: EVIDENCE_OWNER_COMMANDS.md. Root-only evidence-upgrade accepts
   only reviewed41b453fb, verifies immutable old release/units, checks own services
   stopped and holds process.lock, preserves entire journal head/activation/cohorts,
   leaves delivery config/credentials/scanner untouched. Own export timer then
   bounded shadow run only. No continuous lane/sender start or delivery enable.
9. Paths: source /var/lib/vivameda-engineering/repo/early_lane/; release
   /opt/vivameda-early-lane/0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91; state
   /var/lib/vivameda-early-lane (lane.sqlite3, rpc_cache.sqlite3, tracked.json,
   lane.log, log_only_receipt.json); approved inbox
   /var/lib/vivameda-early-lane-inbox/feed.json; config
   /etc/vivameda-early-lane/delivery.json; sender state
   /var/lib/vivameda-early-lane-sender. No secret values copied, read or published.
10. Next gate: owner upgrade/new two-hour receipt, full known screening evidence,
    eligibility/examples if any, then separately reviewed destination confirmation
    and delivery activation. Free-RPC coverage/latency may still block eligibility;
    do not relax rules or claim zero pass means zero good tokens. Preserve original
    activation+14-day review (expected31October; confirm journal), final cohort
    maturity follow-up, no automatic learning or spending. Robinhood work and
    meme desk remain paused. See STATUS.md for limits.

Official version documentation checked 17 October 2026:
https://solana.com/developers/cookbook/transactions/versions (legacy/0/1; max1)
and https://solana.com/docs/rpc/http/gettransaction. Existing public-RPC rate limits
and lack of production-availability guarantee still apply. No new feed or paid tier.

Repository release verification: Python 3.12; 1,027 tests /28 suites passed, 405 files verified. Scanner and learner remain active with unchanged source hashes. This verifies source, not deployment or live screening.
