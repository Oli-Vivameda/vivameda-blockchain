# Astra handover — signature-audited stream shadow

1. Scope: finish demand-driven per-transaction repair and connect it to frozen
   screening in a bounded shadow command. No trading, Telegram, scanner changes,
   delivery configuration edits or continuous service activation.
2. Protocol: STREAM_INTEGRATION_PROTOCOL.md extends the original capture protocol.
   Engineering preregistration commit: 2e9b0fb (before the public-chain probe).
   RULES.md remains ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463;
   original rules commit 959cdebdea5107f48bcc03b16c3968b34dc24fbe is unchanged.
3. Source: public Solana RPC only. Captured logs are provisional. Complete finalized
   mint-signature audits bind event sets and establish coverage. Demand-driven
   canonical transaction repairs handle missing/conflicting events, creation,
   migrations and AMM. Unknown statuses/layouts/creators remain blocked.
4. Implementation: stream_history.py, stream_shadow.py, stream_owner.py,
   stream_stage.py, tests/test_stream_history.py; additions to stream_events.py,
   stream_capture.py and the optional Runner(stream=True) constructor. The default
   service behavior is unchanged. No public feed subscriptions or paid tiers added.
5. Validation: 33 new offline tests cover canonical identity/status/slot/time,
   durable retries and reuse, failures, signature pagination/cursors, stale scans,
   creator authentication, late conflicts, staging and state preservation. The
   synthetic complete path passes all frozen checks while reusing 30 streamed
   transactions and fetching the original creation once. This is not live proof.
6. Live gate: bounded engineering source probes use public-chain data in isolated
   private state. They do not access the protected owner export or owner journal,
   expand eligibility, send alerts, validate returns or establish universal coverage.
   An owner-run integrated shadow on the approved export remains required.
7. State: existing lane.sqlite3 and activation are retained. New mutable caches are
   stream_rpc_cache.sqlite3 and stream/stream_cache.sqlite3 in the existing lane
   state directory. stream/stream_audit.sqlite3 remains append-only and hash-chained.
   stream_screening_receipt.json is the integrated summary. Raw rows stay private.
8. Installation: stream_owner.py verifies all reviewed bytes before imports. Its
   stage command copies a new release under the existing runtime base. It changes
   no systemd units, configuration or access permissions and starts/enables nothing.
   The existing exporter can keep using its prior reviewed source. The bounded
   shadow command explicitly passes log_only=True and has no sender/flush path.
9. Limits: exported scanner coverage is incomplete; no universal new-token capture
   claim. Finalization adds delay. Missing historical stream rows still cost full
   RPC downloads. AMM and unusual creations can remain UNKNOWN. Public RPC capacity,
   reconciled holder census, social resolution and alert readiness need live proof.
   Offline parity and raw event counts are not profitability or safety validation.
10. Next: stage the reviewed bundle, run one short integrated owner shadow, inspect
    fully evaluated candidates and reason counts. Fix concrete blockers before any
    two-hour rollout. Start delivery only after screening readiness is demonstrated.
    Do not loosen filters, reset the clock or enable a continuous lane automatically.

Source-only publication contains no live case rows, protected-state aggregates or
credentials. Existing pending queue-repair publication is a separate workstream.
The capture-only STREAM_HANDOVER.md describes the previous component boundary;
this document supersedes its unimplemented-adapter statements for this new source.
