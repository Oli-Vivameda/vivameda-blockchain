# Early-lane Telegram sender — existing scanner channel, 🌻

Owner chose the scanner's existing Telegram channel on 17 October 2026, replacing
the earlier separate-channel requirement. Every message from this sender starts
with 🌻. No new channel, bot, token or manual channel-ID lookup is needed.

Old sender bundle is owner-confirmed installed, stopped and disabled. The shared-
channel update is prepared but not applied. [One owner command](OWNER_COMMANDS.md)
hash-verifies the stopped upgrade, preserves state, prepares lane-only routing and
sends one fixed direct test. It leaves continuous delivery unconfirmed and does
not start/enable either service. [Astra handover](ASTRA_HANDOVER.md) has hashes,
state paths, verification and remaining work. Scanner code/services stay untouched.

The root service implements the unchanged early_lane/transport.py newline JSON
protocol. Socket /run/vivameda-early-lane-sender/sender.sock is root:lane 0660 in a
root-owned 0750 directory. SO_PEERCRED admits root and the dedicated lane UID;
the client authenticates root. Only the exact numeric chat in root-owned delivery.json
is allowed. The scanner chat additionally needs the owner's explicit
reuse_scanner_channel=true setting. Normal requests still need the existing wire
fields new_channel_confirmed=true, a positive confirmed_at and the exact socket.
The legacy field name is retained; it remains false during the one-shot test.

At runtime only, the sender reads the scanner's existing credential at
/opt/vivameda-crypto-early-scout/credentials.json. It requires a regular file with
owner-only access, owned by root or vivameda-scout. No token is copied, printed,
logged or stored. The installer checks metadata only. The service bounds capabilities
to CAP_DAC_READ_SEARCH for reading the existing scanner-owned 0600 file and makes
scanner data inaccessible. The owner-only shared test copies chat_id alone to lane
configuration atomically, preserving ownership/mode, setting the explicit opt-in and
keeping new_channel_confirmed=false, confirmed_at=null. Socket requests never write
configuration. A different preconfigured destination or enabled confirmation refuses
the preparation rather than overwriting it.

Root-only sender.sqlite under /var/lib/vivameda-early-lane-sender/ uses WAL/FULL to
persist first payloads, event keys, statuses, cooldowns and whitelisted real Telegram
chat_id/message_id/date receipts. A process lock serializes service and owner tests.
Duplicate keys reuse the first event and receipt across restarts. Retry-After uses
the greater of Telegram parameters and HTTP headers, including HTTP dates; global
cooldowns persist. Queued messages gain late-age marking. The lane caller drives
retries; the sender has no autonomous drain. Shared bot limits can affect both feeds;
scanner operation is not coordinated or changed. No polling/webhook changes.

Telegram sendMessage cannot atomically commit with SQLite. Inflight crashes,
timeouts, malformed successes and uncertain 5xx responses are held for owner review,
never automatically resent. This avoids duplicates but may leave a message unconfirmed.
Do not delete state or change keys to bypass a hold. Definite rejections/rate limits
remain safely queued. Redirects and automatic chat migration are forbidden. Raw HTTP
errors, response descriptions, token URLs and message bodies never enter logs.

The root-only direct test uses a fixed message/key, unavailable through the socket.
Repeating the owner command returns the saved receipt. Status 429 gives retry_after;
status 409 means review the held event. No real Telegram call was made by engineering.
58 offline tests use temporary files, synthetic credentials and fake HTTP only:

```bash
python3.12 -B -m unittest discover -s early_lane/sender/tests -v
```

Frozen rules and the lane runtime bundle are unchanged. A completed log-only report,
real channel test and later owner-authorized activation remain separate gates. Tests
prove neither full screening, universal discovery nor profitable outcomes. References
checked 17 October 2026: https://core.telegram.org/bots/api#sendmessage and
https://core.telegram.org/bots/api#responseparameters.

## Private scanner chat correction

Owner's runtime diagnostic established that the existing scanner destination is a
private bot conversation. Shared mode now accepts any valid numeric Telegram chat ID
only when root config explicitly opts in and the value equals the existing scanner
chat_id. Without that opt-in, -100 channel-only admission is unchanged. Other private
chats and mismatched shared destinations refuse. The owner command upgrades from
the installed 28ee6a42 bundle and sends the same fixed 🌻 test; no service starts.
The unchanged lane client still requires a -100 ID when confirmation is enabled.
Before continuous private-chat delivery, review that separate client compatibility
change and the completed rollout result. This sender test does not enable delivery.
