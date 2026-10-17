# Astra handover — early-lane sender — 17 October 2026

BUILT AND OFFLINE TESTED. NOT INSTALLED, STARTED OR ENABLED BY ENGINEERING.
No Telegram message sent. No delivery.json or credential contents read by engineering.
No scanner, frozen rule, lane executable-bundle or running-service changes.

The lane source baseline is main 37190d5693fa3d62aff1fe2b1e4e3fa2e540cddf,
which includes the owner's RPC repair and log-only startup evidence after b0b4d375.
New source lives only in early_lane/sender/. Documentation/navigation and root
MANIFEST.json also change. The existing 41b453fb lane installation remains intact.

## Files and hashes

Independent sender BUNDLE.json SHA-256: `5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b`.

| Executable/test file | SHA-256 |
|---|---|
| `sender.py` | `2a6c816f6fb2a06bd25840a0738ea79b9276b0570bef333ed4161e673a0c8f8b` |
| `install.py` | `df98008fc6a55791889102c345d60de465874d0e12bcdadeb10dcc9ed437845c` |
| `owner.py` | `4f49e1ed7cd166527c2df008e4231fdf15bc2e2ecb040c973e6949209d2a3274` |
| `tests/test_sender.py` | `7a7439a5210f5117fe162449a7aaaf1344ae81fd13b54e23fcb63aa358335a4a` |

README.md, OWNER_COMMANDS.md and this handover are pinned by root MANIFEST.json,
not the executable bundle. Owner commands check bootstrap and bundle before imports.
No duplicate scanner or credential source is distributed.

## State and commands

Engineering source: /var/lib/vivameda-engineering/repo/early_lane/sender/.
Owner-only installed source: /opt/vivameda-early-lane-sender/5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b/.
Unit: vivameda-early-lane-sender.service, root process with existing lane group.
Socket: /run/vivameda-early-lane-sender/sender.sock, root:lane 0660, parent 0750.
State: /var/lib/vivameda-early-lane-sender/ (root 0700), sender.sqlite plus WAL/SHM
and sender.lock. State is private; it includes outgoing message text and receipts.
Do not publish or erase it. No raw token is stored in it.
Existing configuration: /etc/vivameda-early-lane/delivery.json, never written here.
Existing runtime credential: /opt/vivameda-crypto-early-scout/credentials.json,
owned by root or vivameda-scout with owner-only permissions; read only at runtime
and never copied or logged. Root-owned delivery configuration remains required.

Exact install-without-start and owner-only single-test commands:
[OWNER_COMMANDS.md](OWNER_COMMANDS.md). Run in the owner's existing root terminal.
No continuous-service start/enable instructions are part of this task.

## Results, limits and open issues

46 offline sender tests passed locally and on server Python 3.12. Coverage includes
Unix peer checks and complete wire round-trip, receipt persistence across restart,
changed retry text, Retry-After/global cooldown persistence, wrong/scanner-chat refusal,
owner-test isolation, uncertain/crash holds and secret redaction in logs/receipts/state.
Fake HTTP only; no Telegram calls from tests. The repository release gate and syntax
check are recorded in the dated sender release evidence.

Telegram cannot provide an atomic idempotency guarantee for sendMessage. The sender
commits inflight before HTTP; crashes/timeouts/uncertain responses are held rather
than automatically repeated. This can require manual delivery reconciliation and
is an explicit availability limit. Definite rate limits stay queued. Retries need
a caller; the sender never drains autonomously. Shared-bot throttles can affect both
feeds; scanner operation is untouched. No bot polling or webhook changes are made.

Owner still needs to provide the NEW numeric -100... channel ID, arrange its value
in delivery.json separately, run the install-only command and then the one-shot test.
Owner metadata now confirms credential owner vivameda-scout and permissions 0600;
contents/runtime format and real bot channel permissions are not verified. Current configuration is unconfirmed/TBD; the test refuses
until a channel exists in that file. A scanner chat represented by an alias instead
of a number fails closed; do not bypass this by changing scanner configuration.
No live end-to-end delivery or service-sandbox runtime result is claimed.

Existing two-hour log-only rollout continues independently. Last owner evidence:
10 valid polls, 129 fresh marks/627 watched, zero selected/suppressed, Telegram false.
This is startup evidence, not a completed rollout or a full-screening pass. Inspect
its actual receipt around 12:21 Cyprus. Review stays activation+14 days (expected
31 October if the journal confirms 17 October activation); final maturity +15 days
+120 seconds. Sender construction does not restart that clock. Meme desk stays paused.

Next: collect the actual log-only aggregate report and channel ID; owner-install/test
only. Later separately authorize delivery configuration/activation after checking
coverage and readiness. No rule changes, trading, signing, paid calls or new accounts.

## Credential ownership correction — 17 October 2026

Owner's metadata-only stat showed a regular file owned by vivameda-scout (UID 996),
mode 0600. The first installer stopped before any writes because it required root.
Corrected installer/runtime accept root or the existing scanner UID, with owner-only
access and no symlinks. Delivery config, state and socket still require root ownership.
CAP_DAC_READ_SEARCH permits the sandboxed root process to read that private file;
no write-bypass capability is granted and scanner data stays inaccessible. Seven new
offline regressions cover owner acceptance/refusal, unchanged root-config protection,
metadata-only installer checks and the bounded read capability. No credential file
or running service was changed. Rerun only the corrected install command.

The isolated child bootstrap explicitly adds only its private hash-verified snapshot
to the import path before running reviewed modules. A new offline subprocess test
checks local helper loading and argument forwarding without touching production files.
