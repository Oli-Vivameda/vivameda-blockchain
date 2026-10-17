# Astra handover — isolated live collection

1. Frozen alert rules and core.py are unchanged. This collection redesign was
   preregistered before its public-data probe; protocol is LIVE_ISOLATION_PROTOCOL.md.
2. live_rpc.py shares one cooldown and pacing store across market/live/catch-up.
   Per cycle quotas are 4/7/1, maximum 12 total. Unused live quota cannot be used
   by catch-up. HTTP 429 blocks every worker until Retry-After has elapsed.
3. Capture assigns one identity per run, retained across reconnects. Only creation
   events first observed in that run enter live work. Prior-run progress resumes
   with catch-up quota and is not reset. Neither a session nor stream continuity
   is proof of complete history.
4. live_history.py uses a new mutable cache and independent queue tables. Original
   creation authentication, complete fresh finalized signature audit, curve/mint
   ownership and complete holder reconciliation remain mandatory. Facts are
   assembled once, avoiding duplicate account/census calls around history.
5. Discovery now unions permitted public-RPC creation observations with the
   owner-export launch feed, deduplicated by mint. This addresses the original
   all-new-token watch objective; neither source guarantees universal coverage.
   Discovery hints never satisfy frozen admission checks.
6. LiveRunner reserves catch-up pricing slots and preserves due outcome checkpoint
   priority. Budget-denied candidates do not acquire a successful scheduler
   timestamp. Every launch still receives normal audit decisions.
7. Curve and creation error reasons are split without changing their predicates.
   Failed holder reconciliations retain supply/total/account-count/slot diagnostics
   in the desk's own facts. Social failure no longer hides independent curve or
   creator evidence. No identity or supply mismatch is accepted.
8. live_shadow.py and live_owner.py implement bounded log-only observation and
   owner-run hash-checked no-start staging. They cannot enable Telegram. Existing
   scanner sources, rules, study state and old collector caches are untouched.
9. Verification: offline regression and complete repository release gates must
   pass. The separate 180-second public-source probe reads no owner feed,
   protected database or credentials. Its aggregate result is reported separately;
   it is not the required owner rollout and cannot enable delivery.
10. Open gate: useful fresh histories and fully evaluated candidates must be
    observed before requesting another owner trial. The two-hour rollout and
    delivery remain blocked. Prior failed trials are retained as failures.
    Unsupported creation configurations, holder reconciliation, social metadata,
    free-RPC capacity and coverage may still prevent readiness.

Portable commands after checking the release hashes:
```
python3 -B early_lane/live_owner.py --expected-bundle REVIEWED_BUNDLE stage
python3 -B early_lane/live_owner.py --expected-bundle REVIEWED_BUNDLE shadow -- --state-dir OWNER_STATE --input OWNER_FEED --duration 600
```
The receipt is live_screening_receipt.json. Preserve original owner activation,
journal and the existing 14-day review date; never reset them for another attempt.
