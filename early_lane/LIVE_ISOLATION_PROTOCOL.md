# Live collection isolation protocol — 17 October 2026

Recorded before the new public-data feasibility probe. This changes collection,
not the frozen alert predicates, thresholds, six-per-hour policy or study clock.

- Discover the union of retained owner-export launch rows and creation events
  observed on the already-approved public Solana RPC websocket. A creation event
  is a discovery hint only. Original finalized creation transaction, signer,
  curve identity, full signature audit and fresh holder census remain required.
- Every capture run has a new session identifier. Only creation events first
  observed in that session enter the live worker. Retained creation events and
  pre-session exports enter a separate catch-up queue. Reconnection does not
  reclassify pre-session tokens as new.
- Use a new mutable collection cache, leaving prior collector caches intact.
  Live and catch-up scan tables are separate. All share one transport cooldown
  and one-per-second pacing. Per poll: market calls at most 4, live calls at
  most 7, catch-up calls at most 1; total at most 12. No capacity borrowing from
  live to catch-up, endpoint cycling or paid fallback.
- Construct history-derived and account-derived facts once per enrichment.
  Cache original creation authentication separately from scan progress.
  Missing, incomplete or stale history remains UNKNOWN, never inferred from
  stream continuity. Market price alone cannot authenticate a trade history.
- Keep all unresolved signatures; report active live/catch-up queue sizes,
  oldest ages, completed fresh histories, denied budget calls and coverage.
  All exported/discovered launches still receive an audit, even when unpriced.
- Keep creation validation, holder reconciliation, authorities, social resolution
  and unsupported-config checks strict. Split compound curve error reasons and
  retain aggregate supply/census diagnostics. No mismatch is converted to PASS.
- Offline gates: budget isolation/cooldown, independent live/catch-up progress,
  current-session classification, duplicate and gap behavior, missing evidence,
  no signing/Telegram, immutable rules/journal and staging protections.
- Run a bounded 180-second engineering-owned public-data probe after tests.
  It uses an independent state path, no owner feed or protected database and no
  credentials. Report all observed failures, fresh-history and fully-evaluated
  counts. It is a source feasibility check, not a rollout or alert-quality test.
- Proceed to an owner-run shadow only if useful complete screening is observed.
  A failed probe is a valid result: no automatic delivery, new trial loop or
  two-hour pass. Preserve owner activation and review date.
- Existing retained scanner discovery is incomplete; the public websocket is
  also not a universal-coverage proof. Coverage and unsupported evidence remain
  explicit. No results/probabilities from frozen studies may be read.
