# Early-lane Telegram sender — built, not installed or started

Separate Python 3.12 standard-library transport for the unchanged
`early_lane/transport.py` contract. No autonomous jobs or delivery activation.
[Owner commands](OWNER_COMMANDS.md) install definitions only and provide a separate,
explicit one-message channel test. [Astra handover](ASTRA_HANDOVER.md) records hashes,
verification, state and remaining owner actions.

The root service listens on `/run/vivameda-early-lane-sender/sender.sock`, owned
root:vivameda-early-lane, mode 0660 in a root-owned 0750 directory. Linux SO_PEERCRED
admits only root and the dedicated lane UID. The existing client authenticates the
server as root. Requests use newline JSON, protocol `vivameda-early-lane-send-v1`,
HTML text, an event key and a channel. Replies contain status 200 and a whitelisted
Telegram receipt, status 429 with retry_after, or a fixed safe refusal reason.
Messages and raw HTTP errors are never logged.

Every send re-reads the existing owner-only
`/opt/vivameda-crypto-early-scout/credentials.json` at runtime only. The credential must be a regular owner-only file owned by root or the existing
vivameda-scout account. Its existing ownership and permissions are preserved. The
file is never copied, changed or opened during installation/testing. Fields are the scanner's
existing `bot_token` and `chat_id`. Only the numeric channel in root-owned
`/etc/vivameda-early-lane/delivery.json` can receive messages; the scanner chat is
always forbidden. An unknown/non-numeric scanner chat fails closed. Normal socket
requests also require new_channel_confirmed=true, a positive numeric confirmed_at,
and the exact socket above. No component here writes delivery.json. The root service bounds its capabilities to
CAP_DAC_READ_SEARCH so it can read a scanner-owned 0600 credential without changing
its owner or permissions; scanner data remains explicitly inaccessible.

Root-only `/var/lib/vivameda-early-lane-sender/sender.sqlite` persists immutable first
payloads, states, retries and real message_id/chat_id/date receipts with WAL and
synchronous=FULL. A process lock prevents concurrent service/owner-test use. Duplicate
event keys return the same saved receipt, including across restarts. Changed late
text on a client retry cannot create a second event or replace its first payload.
Queued sends acquire a late-age prefix when appropriate. Telegram 429 cooldowns use
the greater of API retry_after and HTTP Retry-After, including HTTP dates; cooldowns
persist for the whole sender. The lane outbox drives retries; no background worker
sends after the lane has stopped requesting delivery. Shared bot limits may also
reflect scanner traffic; no scanner coordination or changes are made.

Telegram sendMessage has no idempotency parameter. A crash between network acceptance
and receipt commit, a timeout, a malformed success or a 5xx response is uncertain.
Such events are durably HELD as ambiguous and **never automatically sent again**.
This favours avoiding duplicates over claiming impossible exactly-once delivery.
The unchanged lane client will keep retrying; the sender keeps refusing that held
key. Owner review of the private database and channel is needed; there is no blind
reset/retry command. Do not delete state or generate a new key to bypass a hold.
Definite 400/401/403 API rejections queue a safe delayed retry; redirects and automatic
chat migration are forbidden. Real successes are the only source of receipts.

The one-shot owner test uses a fixed message and a fixed channel-specific event key.
It requires root and a destination already present in delivery.json, and checks the
scanner-chat exclusion. It can test while new_channel_confirmed remains false; this
exception is unavailable through the Unix protocol. It neither starts a service nor
changes configuration. Repeat invocations return the original receipt. No actual
Telegram test has been run by engineering.

Offline tests use synthetic credentials, temporary state and fake HTTP adapters:

```bash
python3.12 -B -m unittest discover -s early_lane/sender/tests -v
```

Existing scanner, lane runtime bundle, frozen rules, studies and running services
are unchanged. Installing the sender does not establish full screening, completed
rollout validation, channel confirmation or profitable outcomes.

Telegram API references checked 17 October 2026:
https://core.telegram.org/bots/api#sendmessage and
https://core.telegram.org/bots/api#responseparameters.
