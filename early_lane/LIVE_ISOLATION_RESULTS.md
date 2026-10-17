# Live collection isolation — preliminary feasibility result

Status: BLOCKED. No owner install/start or further rollout is requested.

The preregistered engineering-owned public-RPC source probe ran for 180.04 seconds.
It read no owner export, protected scanner database, frozen outcomes or credentials,
changed no running service, and sent zero Telegram messages. Its state is separate
from the owner's journal. This is a source feasibility observation, not a rollout,
alert-quality study or real trading result.

| Measure | Observed |
| --- | ---: |
| Newly discovered mints | 26 |
| Unique mints observed in the frozen market-cap band | 2 |
| Fully evaluated unique mints | 0 |
| Completed fresh histories | 0 |
| Selected alerts | 0 |
| Live worker RPC calls | 63 |
| Catch-up worker RPC calls | 0 |
| Market RPC calls | 34 |
| Finalized failed signatures skipped | 4,460 |
| Captured stream transactions reused | 237 |
| Canonical transaction repairs | 56 |
| Unresolved live signatures at finish | 1,270 |

Isolation worked: catch-up consumed no live capacity. The new collection path still
failed to assemble a single complete screening. All 23 new regression tests and
1,155 repository tests passed before this probe; tests do not establish live readiness.

Read-only classification of already-cached public transactions found that 38 of
the 56 canonical repairs contained no Pump invocation. Fourteen could be normalized
as safe trade-log fast paths, while 42 were outside that fast path. Fifty pending
signatures had an event-time-not-fresh gap recorded by capture. These counts overlap
and are diagnostics, not an alert population or outcome sample.

The remaining bottleneck includes references to mints that the Pump-only log
subscription cannot supply, plus absent/late observations. A complete signature
audit still requires those gaps to be resolved. No such signature was discarded
or treated as a completed history to obtain a PASS.

The probe exhausted live history budget before reaching holder/curve checks.
There were no cached transaction decode errors in this sample. It therefore does
not resolve the owner's earlier curve-identity or holder-supply failures; the
specific new diagnostics remain available for a future justified observation.

Next gate: improve authenticated transaction coverage or demonstrate a different
permitted source design within the existing no-key/no-paid constraints. Repeating
this exact owner trial is not justified. Keep delivery disabled, preserve the
original activation and frozen rules, and do not claim universal token coverage.
