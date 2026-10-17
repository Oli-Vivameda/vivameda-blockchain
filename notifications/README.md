# Notification suppression policy

1. Scope: portable source transformations for auxiliary notification routes. This
   component does not send messages, load credentials, read live databases or
   install a service. The reviewed owner installer is separate.
2. Preserve the owner's permitted core alert feeds. Suppress auxiliary pool,
   spot-movement, price-watchlist, speculative-watchlist and prediction-research
   delivery routes without changing scanner scoring or scientific protocols.
3. Caller contract: patch(kind, source, expected_sha256). Require the caller's
   exact reviewed source hash. Unknown hashes, functions or shapes fail closed.
   Compile each candidate and verify other top-level code/functions are unchanged.
4. Pool: retain observations; pending notifications become suppressed_owner with
   no message receipt. Already expired notifications remain expired.
5. Movement: continue sampling and evaluating price history. Mark setup and
   movement notifications suppressed without send attempts or delivery timestamps.
6. Speculative watchlist: retain research evidence and record suppression before
   attempting delivery. Prediction research: retain its collection cycle while
   returning explicit zero-sent notification status. Startup messages are muted.
7. Price watchlist: suppress only its notification helper. If the helper contains
   capture/file/SQL writes, refuse it for separate review rather than deleting
   capture work. Other functions remain unchanged. No successful receipt is faked.
8. Tests: offline synthetic source/queue tests in tests/test_policy.py. Production
   source parity, retained observation behavior and installer rollback are tested
   separately against reviewed source snapshots in private owner engineering.
9. Deployment limits: source publication is not deployment. Applying reviewed
   candidates requires the owner installer, backups, current source hashes and
   normal-cycle verification. Do not disable research collectors to silence them.
10. Runtime safety: allowed core feeds, early-lane delivery activation, frozen
    predictions, learning journals and study clocks are outside these edits.
