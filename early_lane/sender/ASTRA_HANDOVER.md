# Astra handover — early-lane sender, shared channel 🌻 — 17 October 2026

Owner-confirmed installed sender: 28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724,
stopped and disabled; credential unchanged. Owner then explicitly chose the scanner's
existing channel and 🌻 prefix. This supersedes the earlier separate-channel/scanner-
chat prohibition for this owner-selected destination only. Frozen eligibility rules
and the lane executable bundle remain unchanged. Meme desk stays paused.

## New files and hashes

New independent BUNDLE.json SHA-256: `40c80bc0d7b6049507bf0be3ac6758f5aed714c32e18beb7ecab21f871d9e63f`.

| Runtime/test file | SHA-256 |
|---|---|
| `sender.py` | `5069aaeb0be79212c29b0086777d8201a9e62c35f3fd50b17afbf2b5cfb14a1a` |
| `install.py` | `9983e65df88f981a29d86f0a3d1ac57e63a30824a268fb3043683bc5cf625b8e` |
| `owner.py` | `c970b317957200b792006a5fe4ee40b3a8d31a22dd949c7aa7776b056880e9dd` |
| `tests/test_sender.py` | `6438d682dfce75c0996e5c77c1ac4b8d16052cb0b972adcc82d8b3851f59a1e9` |

Source: /var/lib/vivameda-engineering/repo/early_lane/sender/.
Proposed installed release: /opt/vivameda-early-lane-sender/40c80bc0d7b6049507bf0be3ac6758f5aed714c32e18beb7ecab21f871d9e63f/.
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

58 offline sender tests; full Python 3.12 gate 994 tests across 27 suites, 393 file
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

## Owner-confirmed private destination diagnosis and correction

Owner applied 28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724:
installed/stopped/disabled, state preserved. Its direct test returned failed_closed.
Owner's safe diagnostic: delivery channel unset, confirmed false, shared flag absent;
scanner destination type private_chat. No token or numeric ID was printed. The -100
parser caused the refusal before config mutation or Telegram delivery. New release
accepts private/basic-group numeric IDs only under explicit root shared mode and exact
scanner-destination equality. Four new regressions cover private/basic-group IDs,
no-flag denial, exact-match refusal and the full idempotent 🌻 private test path.
58 sender tests / 994 repository tests / 27 suites / 393 file hashes verified.
The owner command now upgrades from 28ee6a42, preserves state, prepares only lane
routing and runs the direct test. Main failures print exception class only, never
exception text or token URLs. Real Telegram result remains owner-run and pending.

Important remaining integration issue: installed lane transport.configuration still
requires -100 for enabled confirmation. No lane executable/source/bundle is changed
here. Before continuous private-chat activation, separately review that compatibility
update and actual log-only readiness; do not flip confirmation or start the lane.

## Owner receipt after this source release

Owner ran the checked 40c80bc0 upgrade/test: installed true, started false, enabled
false, state preserved. The direct runtime test returned status 200 with a real
Telegram receipt. Exactly one test acceptance is confirmed; private destination and
message identifiers are not published. No continuous sender/lane activation. The
unchanged lane transport's private-chat compatibility guard and completed rollout
readiness remain separate outstanding gates. This supersedes the pending-test status
above; it does not claim a live automatic alert or production service sandbox pass.
