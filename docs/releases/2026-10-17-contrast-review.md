# Owner-selected token contrast — source receipt — 17 October 2026

Two owner examples received privately. Generic source, methods and synthetic tests
are published; identities, live alert/case details and public-provider raw captures
remain private. The examples are outcome-selected, not a validation cohort.

14 synthetic exporter tests pass. Full Python 3.12 gate: 1008 tests across 28 suites,
397 verified file hashes. The exporter checks only opaque pl_predictions membership
first, excludes every member, refuses an absent exclusion table, and uses a SQLite
read-column authorizer plus mode=ro/query_only. It never opens frozen outcomes,
prediction bodies/probabilities or model features. It exports bounded reconstructed
context only for nonmembers, without interpolation or claimed fills/profit.

Exporter SHA-256: c01cd5681996fb5d95632255b98ff6fc0bed518c5b3134786304ec97ccc67d0f.
See [protocol/limits and private owner invocation](../../learning/contrast_review/README.md).
Original protected alert context and exclusion status still require the owner-run
read-only export. No comparison learning, fitted weights or automatic rules changed.
No production database/journal, source permission or running service was changed.

A separate sender owner receipt confirmed one direct 🌻 Telegram test accepted,
with sender and lane still stopped/disabled for continuous delivery. Identifiers
stay private. Private-chat client compatibility and final log-only result remain
outstanding before automatic activation; this research does not change those gates.
