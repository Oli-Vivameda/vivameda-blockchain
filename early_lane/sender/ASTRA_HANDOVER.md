# Astra handover — early-lane sender, shared channel 🌻 — 17 October 2026

Owner-confirmed installed sender: 5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b,
stopped and disabled; credential unchanged. Owner then explicitly chose the scanner's
existing channel and 🌻 prefix. This supersedes the earlier separate-channel/scanner-
chat prohibition for this owner-selected destination only. Frozen eligibility rules
and the lane executable bundle remain unchanged. Meme desk stays paused.

## New files and hashes

New independent BUNDLE.json SHA-256: `28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724`.

| Runtime/test file | SHA-256 |
|---|---|
| `sender.py` | `4d09c3e992d597486938f2da5b8469769f3f774fa79fa00b0662e4e4d0518d81` |
| `install.py` | `9983e65df88f981a29d86f0a3d1ac57e63a30824a268fb3043683bc5cf625b8e` |
| `owner.py` | `3c5d1d91438a39f919d10a2ef5cf94f282e7adc2340894ddf401adbe50f32232` |
| `tests/test_sender.py` | `940f152add74d83f03ce79215e2953211e556485fca6d9bef3ef74b26659463e` |

Source: /var/lib/vivameda-engineering/repo/early_lane/sender/.
Proposed installed release: /opt/vivameda-early-lane-sender/28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724/.
Unit: vivameda-early-lane-sender.service. Existing dedicated root state is preserved:
/var/lib/vivameda-early-lane-sender/ (0700), sender.sqlite plus WAL/SHM and sender.lock.
The old unit is backed up there before a checked stopped upgrade. Socket remains
/run/vivameda-early-lane-sender/sender.sock (root:lane 0660, directory 0750).
Runtime credential remains /opt/vivameda-crypto-early-scout/credentials.json;
owner metadata: vivameda-scout UID 996, regular file, 0600. Never copied/changed.
Root service has CAP_DAC_READ_SEARCH only; scanner data is inaccessible.

## Owner action

[Exact one-command stopped upgrade + direct test](OWNER_COMMANDS.md). Starts/enables
no service. Requires inactive/disabled sender and continuous lane, verifies the old
bundle/unit, preserves sender state, leaves the transient log-only rollout alone.
Only the runtime test reads the credential contents. It copies chat_id alone into
/etc/vivameda-early-lane/delivery.json, adds reuse_scanner_channel=true, exact socket,
and keeps new_channel_confirmed=false, confirmed_at=null. Other destinations remain
refused, and the scanner chat is still refused without that explicit root flag.
The legacy confirmation field name is retained for the unchanged transport contract.
Every early-lane send now starts with 🌻. Test event/key are fixed and idempotent.
No test or command has been executed against Telegram by engineering.

## Verification and limits

54 offline sender tests; full Python 3.12 gate 990 tests across 27 suites, 393 file
hashes; proposed unit syntax verified. New coverage: explicit shared-channel flag,
unchanged destination/confirmation guards, atomic token-free config write, 🌻 prefix
and test idempotency, old-bundle integrity, refusal of active/enabled units and state
preservation. Existing Retry-After, real whitelisted receipts, credential ownership,
private snapshot imports and uncertain/crash holds remain tested. No live root
upgrade/sandbox/channel delivery result is claimed for the new release.

Telegram has no atomic sendMessage idempotency guarantee. Uncertain network sends
stay held for manual review, never automatically resent. Definite rate limits stay
queued and caller-driven. The owner's command can be repeated for the same test;
it does not create another event or enable delivery. Shared bot/channel limits can
affect both feeds; scanner operation is not coordinated or changed.

Open: owner must run the checked command and confirm the single 🌻 test message.
Continuous delivery remains off. The final 7200s log-only result and screening/
coverage limits still need review; no success/outcome rates are inferred from source
tests. Owner startup evidence remains 129 fresh marks/627 watched, zero selections,
Telegram false at the supplied snapshot. Expected finish around 12:21 Cyprus; inspect
actual receipt. Review date remains observational activation+14 days, expected
31 October only if journal confirms 17 October activation. No clock/reset/rule changes.
