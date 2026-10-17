# Astra handover: stream backlog collection repair

1. Problem: an unavailable early canonical transaction stopped processing later
   finalized failures and reusable stream observations. Existing round-robin work
   also spent scarce RPC capacity on pre-stream launch history.
2. Change: drain authenticated local evidence across each pending page and retained
   queue before network repair. Preserve every unresolved successful signature.
   Batch cache commits; interrupted work remains idempotently recoverable.
3. Scheduling: on four polls out of five, prioritize existing feed candidates with
   captured creation events, for pricing and enrichment. Every fifth poll uses fair
   round-robin across all feed candidates. Due outcome checkpoints remain first.
4. Creation events supply scheduling hints only. They grant no creator, holder,
   history or admission PASS. No new launch population or data source is introduced.
5. Frozen rules, mandatory completeness/freshness checks, RPC call limits and
   Retry-After remain unchanged. Unsupported creation identities and unreconciled
   supply still block screening. No interpolation or inferred PASS.
6. No journal reset, activation change, credential access or scanner modification.
   Existing staging remains owner-run and no-start. Continuous delivery is disabled.
7. Seven new regression tests cover later cached/failure processing behind a
   missing head, durable replay, conflicting or wrong-slot cache entries, missing
   history refusal, non-authenticating scheduling hints and fifth-poll fairness.
8. Validation: full offline release gate required before staging. Synthetic
   regression success is not evidence of live capacity or an alert-quality result.
9. Next gate: owner-run bounded shadow; require completed fresh histories and
   fully evaluated candidates before the two-hour rollout. Report stream queue,
   scheduling group and captured-birth population in cycle logs. No automatic
   promotion or Telegram enablement.
10. Open limits: retained scanner launch feed coverage remains incomplete;
    pre-stream history can still exceed free public RPC capacity. Unsupported
    creation configurations, social availability and account snapshot mismatch
    remain separate blockers. All missing evidence continues to fail closed.

Portable commands, after checking the reviewed BUNDLE and entrypoint hashes:
```
python3 -B early_lane/stream_owner.py --expected-bundle REVIEWED_BUNDLE stage
python3 -B early_lane/stream_owner.py --expected-bundle REVIEWED_BUNDLE shadow -- --state-dir OWNER_STATE --input OWNER_FEED --duration 600
```
Use the new staged bundle for the shadow, preserve the existing state, and inspect
stream_screening_receipt.json. Do not start a continuous service.
