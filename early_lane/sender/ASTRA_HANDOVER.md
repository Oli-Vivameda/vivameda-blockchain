# Astra handover — early-lane sender — 17 October 2026

BUILT AND OFFLINE TESTED. NOT INSTALLED, STARTED OR ENABLED BY ENGINEERING.
No Telegram message sent. No delivery.json or credential contents read by engineering.
No scanner, frozen rule, lane executable-bundle or running-service changes.

The lane source baseline is main 37190d5693fa3d62aff1fe2b1e4e3fa2e540cddf,
which includes the owner's RPC repair and log-only startup evidence after b0b4d375.
New source lives only in early_lane/sender/. Documentation/navigation and root
MANIFEST.json also change. The existing 41b453fb lane installation remains intact.

## Files and hashes

Independent sender BUNDLE.json SHA-256: `f5b6bd39c8e12fe323c0242d5a81d437e59ee190b4c67c09ba3f4e17b3fd1dcc`.

| Executable/test file | SHA-256 |
|---|---|
| `sender.py` | `f7f1db7ddc844309ff3781a2435c4d98bc79cd385638ccc131cc41ba9334af67` |
| `install.py` | `d59641a96dca6cf10ab29c45407618f7685b4e88175f5a24e9f43c344987cb9a` |
| `owner.py` | `e209057c437d9ca24d9220a2de13ac4e1ef18c3ded434850b63cd10d2b58f268` |
| `tests/test_sender.py` | `7648c72150bbf570b89e21d36f8f5dc6b5b8fe116b79d5ad8a24d51f1a9dd29e` |

README.md, OWNER_COMMANDS.md and this handover are pinned by root MANIFEST.json,
not the executable bundle. Owner commands check bootstrap and bundle before imports.
No duplicate scanner or credential source is distributed.

## State and commands

Engineering source: /var/lib/vivameda-engineering/repo/early_lane/sender/.
Owner-only installed source: /opt/vivameda-early-lane-sender/f5b6bd39c8e12fe323c0242d5a81d437e59ee190b4c67c09ba3f4e17b3fd1dcc/.
Unit: vivameda-early-lane-sender.service, root process with existing lane group.
Socket: /run/vivameda-early-lane-sender/sender.sock, root:lane 0660, parent 0750.
State: /var/lib/vivameda-early-lane-sender/ (root 0700), sender.sqlite plus WAL/SHM
and sender.lock. State is private; it includes outgoing message text and receipts.
Do not publish or erase it. No raw token is stored in it.
Existing configuration: /etc/vivameda-early-lane/delivery.json, never written here.
Existing runtime credential: /opt/vivameda-crypto-early-scout/credentials.json,
root-owned, read only at runtime and never copied or logged.

Exact install-without-start and owner-only single-test commands:
[OWNER_COMMANDS.md](OWNER_COMMANDS.md). Run in the owner's existing root terminal.
No continuous-service start/enable instructions are part of this task.

## Results, limits and open issues

39 offline sender tests passed locally and on server Python 3.12. Coverage includes
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
Root credential metadata/runtime format and real bot channel permissions are not
verified by engineering. Current configuration is unconfirmed/TBD; the test refuses
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
