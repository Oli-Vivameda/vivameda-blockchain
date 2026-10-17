# Meme desk v1 — manual Solana review, steps 1 and 2

The desk prepares, tracks manual marks and records; the owner executes manually in
Phantom. No signer, wallet connection, swap transaction, signup, key acquisition,
paid call or direct Telegram API client exists. Phantom address and destination
remain TBD. Source is exclusively a sanitized OWNER export, never the protected
scanner DB. Existing agents, admission policy, scoring, monitors, prediction ledger
and learning journal are unchanged. Do not install through deploy_crypto.

## Replay

REPLAY_PROTOCOL.md was published at commit
`376c3fed540e89aeee8d8d26c2ce18636c409acf` BEFORE replay code/tests ran. Its SHA-256
is `62c4b3e4b13dbc97a3c973cf22b9fb40eb78a2e006c315e20abd8df92b5195a2`.

Earliest retained development ALERT only; freeze out all pl_predictions mints before
exporting. Only its mint membership is used. SQL authorizer allows explicit columns
and denies pl_results, prediction probabilities, v2_outcomes, unknown tables and
writes. Connection uses URI mode=ro, query_only and one bounded read transaction.
No permission change or engineering-user database read is attempted. The exporter
only emits normalized replay/ticket rows plus aggregate coverage, no arbitrary
features, model payloads, journal rows or credentials.

The scanner mandatory set is token_controls, liquidity_control, trading_mechanics.
Those require fresh identity-bound PASS evidence; ANY explicit REJECT blocks the
desk. Background UNKNOWNs are retained. This does not modify scanner policy or the
learning journal's separate seven-PASS rule. Entry is first snapshot >=alert+60 s,
$10 notional; fees 1% buy/sell and $0.05 network per executed leg. A/B/C exit rules,
missingness, chronological splits and all denominators are frozen in the protocol.
Private input/case traces stay on server; publish only REPLAY_RESULTS.md aggregates.
Do not turn missing reserves into liquidity-derived price impact or invent returns.

Price snapshots have no reserve columns. Optional `--reserve-archive` takes JSONL
captured from existing approved raw RPC evidence, NOT fresh RPC calls or paid history.
Each capture requires:

- mint, chain=solana, pair, pool_address, observed_at, evidence_refs;
- pool_response (raw captured getAccountInfo value+context) and account_addresses;
- accounts_response (getMultipleAccounts value+context, order mint/LP/base/quote);
- quote_usd price, original observed_at and evidence_refs.

reserves.py validates the supported Pump AMM owner/discriminator/layout, pool mints,
LP authority, classic Token programs, raw vault address/owner/mint/decimals bindings,
positive balances, slot order and contemporaneous USD conversion. Virtual reserves,
mayhem mode, changed layouts, stale/future/contradictory captures are unsupported.
References/metadata are provenance, not a cryptographic proof of an RPC provider's
honesty. Quote USD conversion is independently evidenced, not guessed from current
SOL prices. Historical evidence must be <=180 s old and at/before the snapshot;
live reserves/market inputs <=30 s. Implied USD token price must agree within 3%.
The archive schema/fixtures are explicit in tests. No boolean-only authentication.
If the existing evidence cannot supply this format/provenance, remain unresolved.

## Tickets, risk and journal

New ALERTs must be <=60 s old; exporter <=30 s old; snapshot/reserves <=30 s old.
The owner export timer is 15 s and the desk polls every 5 s after installation.
Existing Learning V2 case creation can lag alerts: this desk does not relax its
60 s limit or alter V2 to manufacture tickets. Measure actual ticket ages.

Ticket fields include exact mint, symbol, age, cap/liquidity, retained regime/score,
current price +3% ceiling, $10 size, authenticated $10 impact in/out, conservative
round-trip costs, A levels and UTC clock deadline, invalidation, UNKNOWNs,
counter-evidence, regime replay stats or 'no replay yet', DEX Screener/Jupiter links
and TAKEN/SKIP actions. Levels reference current snapshot; actual manual fill can
differ and steps 3–4 will reconcile it. The desk opens no swap URL itself.

For conservative risk, round-trip cost includes both side impacts, 1% fees each
side and THREE $0.05 network charges for split plan A; reject >6%. Use the smaller
of displayed and authenticated 2*quote-USD reserves for the $25,000 liquidity floor.
Stop tickets with >=3 manually marked TAKEN/open positions. At $15 realized losses
in a UTC day tickets continue REVIEW ONLY. At $25 cumulative realized losses halt
until explicit owner reenable. Loss means the sum of NEGATIVE owner-attested closed
net PnL: profits do not replenish limits. Reenable preserves full cumulative history;
a further negative close above the lifetime threshold halts again. UTC rollover
resets only the daily window. Unknown/unrecorded Phantom fills cannot enforce a loss
budget: v1 only knows manual marks; steps 3–4 remain essential. TAKEN records intent,
not a verified fill; it can record an owner's action even on a review-only ticket.

Own state: append-only SQLite events protected by UPDATE/DELETE triggers, sequential
hash chain, BEGIN IMMEDIATE transitions, unique source/button IDs and verification
at startup/before mutations. This detects tampering; a privileged administrator can
replace the database. State is reconstructed from the chain. Closed positions need
an explicit unique owner-attested net-PnL event; no automatic PnL fabrication. Existing
tickets remain visible if later invalidated; the ticket lists void conditions. V1
does NOT continuously track positions or automatically re-screen open trades.

## Delivery remains disabled

No destination is confirmed and no sender is installed by this project. Tests only
use memory transports; service shadow/once never sends. delivery.py has a durable
queue interface and an OPTIONAL local Unix client for an already authorized,
root-owned authenticated sender. No tokens, API keys, Telegram credential files or
account signups are read. Reusing such a sender requires owner confirmation of the
destination, owner identity and socket; there is no direct API fallback.

The optional bridge must implement newline JSON operations send_ticket,
owner_updates and send_skip_reasons, with idempotency-key deduplication, authenticated
owner_id on updates and {ok,receipt,updates,retry_after} responses. Owner-only callbacks
produce fixed SKIP reasons. Rate limits persist next_try globally and queue tickets;
late deliveries show age. A transport failure after an ambiguous send can be retried,
so bridge idempotency is required. No compatible bridge is assumed available.
Root-owned delivery.json must be non-writable by other users, destination_confirmed
true, and contain destination, confirmed_at, owner_id, socket. Until then the service
stays shadow. Confirming a destination alone does not establish a working transport.

## Owner commands and operation

Exact hash-checked commands, bundle hash and paths are in ASTRA_HANDOVER.md. owner.py
snapshots reviewed bytes to a private temporary directory before importing/running
project code. This avoids importing mutable staging modules under root. The installer
copies verified source to a root-owned immutable release and runs tests as its new
unprivileged user. It refuses existing paths/installations; no automatic migrations.

The optional owner installer creates ONLY vivameda-meme-desk.service and its own
read-only exporter service/timer. The desk user cannot read the scanner DB; root
producer opens it read-only and writes sanitized files to its own inbox. The service
is AF_UNIX-only, read-only filesystem except its state, has a 3 GiB disk guard and
bounded CPU/memory. No existing unit is stopped/restarted/edited. Installation
itself does not establish valid input, historical reserve coverage or live delivery.

```sh
python3 -m unittest discover -s meme_desk/tests -v
ssh vivameda-server 'systemctl status vivameda-meme-desk.service --no-pager'
ssh vivameda-server 'journalctl -u vivameda-meme-desk.service -n 30 --no-pager'
ssh vivameda-server 'sudo -u vivameda-meme-desk python3 -B /opt/vivameda-meme-desk/current/service.py report --state-dir /var/lib/vivameda-meme-desk'
ssh vivameda-server 'sudo systemctl stop vivameda-meme-desk.service'
```

TAKEN/SKIP/close/reenable are also available through the local service.py CLI. Run as
the desk user with --state-dir, --event-id (unique), --ticket and --action/--reason;
close also requires --net-pnl. Reenable requires a reason and does not erase history.
Do not run a second daemon against installed state. Shadow research uses separate
state and a bounded --duration 3600, not existing service modification. A missing or
stale export yields a BLOCKED receipt; one hour of waiting is not a valid dry run.

Steps 3–5 are excluded: public-address position tracker, real-fill/skipped-outcome
reconciliation and weekly review. Neither a positive replay nor passed tests is
proof of executable profitability. A negative result is a valid result.
