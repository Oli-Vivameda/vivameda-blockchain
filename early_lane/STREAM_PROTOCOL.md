# Live stream source protocol — shadow build

The frozen RULES.md and original activation remain unchanged. This component uses
only the existing permitted public Solana RPC, via its TLS websocket. It never
imports the scanner, reads scanner/learning tables, receives credentials or sends
Telegram. No service installation/start is part of this build.

Capture Pump program-mention logs at confirmed commitment and finalized root
notifications on one fixed connection. Validate subscription IDs, framing bounds,
program invocation nesting, successful transaction status, pinned instruction and
event layouts, positive economic amounts, method/event coverage and observation
timestamps. Parse official emitted data directly; never synthesize instructions
or signer evidence to make the existing transaction decoder accept log-only data.
Creation records are provisional until original full transaction authentication.

A separate bounded mutable stream cache retains about thirty minutes plus a
sixty-second margin. It contains public-chain observation rows privately and is
not the decision journal. Keep an append-only hash-chained audit of connection
starts, gaps, stops and RPC recovery proofs. Duplicates cannot duplicate economic
trades. Conflicting notifications, truncation, unknown relevant methods, malformed
frames, disconnects and restarts must create coverage gaps/generations. Unsupported economic records whose complete
transaction mint set is decoded create gaps for every mint in that transaction.
An unlocatable/missing event, stack error or disconnect creates a global gap.
A mint-scoped gap cannot be cleared by unrelated-token traffic or an older proof. Persist
provider Retry-After/cooldowns across restarts; no endpoint/IP rotation. Disk
reserve and cache/message/record bounds must fail closed. Stop a bounded capture
cleanly; a stopped connection is not current coverage.

Gap recovery uses the unchanged complete RPC Collector.history contract. Require
original authenticated creation and complete successful transaction rows, snapshot
not before the connection/gap and <=60 seconds old, and exact overlap parity by
signature, event hash, participant, direction, timestamp and amounts. A mismatch
cannot clear a gap. A full RPC snapshot proves only its own timestamp; it never
blesses subsequent log-only observations. The owner lane cache is not opened by
the engineering probe. Recovery metadata/hashes are append-only in the stream audit.

ADMISSION IS DISABLED: every stream report/event/recovery explicitly carries
admissible_for_screening=false. This component never sets history_complete, never
writes lane.sqlite3, never resets the study clock, and never changes ticket/alert
population. The existing lane runner is unchanged. Pump AMM/other venues are not
normalized by this shadow parser; graduated tokens still require the existing
full RPC evidence. Capturing broader public launch events does not expand the
frozen exported-launch eligibility population.

Before replacing the runtime history source: verify original creators with full
transactions, prove whole-history continuity and checkpoint ordering/recovery,
add supported AMM parity or retain strict RPC fallback, check trade timestamps,
and compare live frozen-gate results on eligible exported mints. TCP continuity
and a few matching samples alone are insufficient proof. Root/live capture is
not a screening pass. No more blind two-hour runs or delivery activation.

Validation preregistered for this component: adversarial offline transport and
source tests, then bounded public log-only capture (<=600 seconds); report actual
notifications, normalized events, gaps and refusal reasons. No returns, win rates,
training labels, or token recommendations are computed in this capture task.
