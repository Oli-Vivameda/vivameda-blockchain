# Signature-audited stream integration — preregistration

This extends STREAM_PROTOCOL.md for a bounded log-only screening build. RULES.md,
its preregistration, exported-launch population and original activation stay fixed.
No Telegram, service activation, scanner changes, keys or paid calls are permitted.

The stream itself never grants history_complete. A separate collector enumerates
ALL finalized mint signatures, including failed entries, through a fresh RPC audit.
Initial enumeration must reach mint creation; incremental enumeration must reach
the previous finalized cursor without a gap. Validate ordering, statuses and IDs.
A successful signature must have either a complete, conflict-free Pump buy/sell
notification at its exact slot, or its canonical finalized full transaction body.
Use the signature's blockTime for lookbacks, with <=30s parity against event time,
matching the existing transaction parser. Conflicts, absent/malformed/truncated
notifications, creations, other Pump methods, AMM and migrations require full
transactions; never infer their absence from a program-mention subscription.

Authenticate creation using the existing instruction/account/signer/event parser.
No synthetic instruction or relaxed creator checks. Missing/unsupported events or
original creators block history. Finalized transaction identity, slot, status and
blockTime must match the requested signature evidence. A durable per-signature
repair cache shares full bodies across relevant mints. Demand-driven repairs run
only for audited candidates, not every unsupported event across the whole chain.
Provider cooldowns and the existing one HTTP call/second limit remain in force.

Every signature in the audited interval must be accounted for. Before returning,
check known conflicts against previously reused notifications and replace them
with canonical full-transaction evidence. Completed stale work advances its cursor
but cannot produce fresh history; require a fresh catch-up scan. Signature audit
completeness, not TCP continuity or a global generation counter, covers omissions.
Only this collector may return complete history to the unchanged evidence checks.
AMM/graduated candidates retain full-RPC fallback and can remain UNKNOWN if too slow.

Integrated shadow uses its own stream cache and a separate stream RPC cache in the
lane state directory, while retaining the existing append-only lane journal and
clock. The installer only stages reviewed files; it never edits units, delivery
configuration or permissions, and never starts anything. Existing export units
can keep running their prior reviewed bundle. Shadow explicitly uses log_only=True
and has no sender or flush call. Test code never sends messages.

Validation: adversarial offline signature/repair/creation/freshness tests; synthetic
complete-path all-gates test; bounded public-chain capability observation, without
protected data access. Then an owner-run short integrated shadow on the approved
export. Require full candidate evaluation before a two-hour rollout. Zero selected
alerts can be valid; zero fully evaluated candidates is not readiness. Record actual
failures. No outcome learning, rule changes or delivery activation in this task.
