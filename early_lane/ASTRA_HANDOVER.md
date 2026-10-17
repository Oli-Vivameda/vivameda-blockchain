# Current handover — evidence repair, 17 October 2026

See [evidence repair handover](EVIDENCE_REPAIR_20261017.md) and [current owner commands](EVIDENCE_OWNER_COMMANDS.md). 1,027 repository tests passed; owner upgrade and full live screening remain pending. This supersedes earlier rollout/readiness and private-chat compatibility status below.

# Astra handover — early lane — 17 October 2026

## Separate sender prepared after the observation startup

See [sender/ASTRA_HANDOVER.md](sender/ASTRA_HANDOVER.md) for the independent sender
bundle, hashes, install-without-start command and owner-only test-message command.
46 offline sender tests; source only, not installed/started/enabled. delivery.json,
existing credential and lane runtime are untouched. No Telegram call was made.
The numeric NEW channel remains missing. Supersedes older 'sender absent' source
statements below; dated observation/deployment evidence remains unchanged.


## Owner-confirmed running observation — 17 October 2026, 10:22 Cyprus

Owner applied the checked RPC repair (41b453fb), preserving the journal; preflight obtained 16/30 prices. Repaired exporter succeeded with 644 retained launch rows. After starting the exporter service before its timer, the new vivameda-early-lane-rollout-rpc2.service produced 10 valid polls, pricing_issue null and 129 fresh market marks among 627 watched tokens in the last supplied cycle. Selected/suppressed decisions 0; Telegram false. This confirms startup data/pricing, not full screening, complete coverage, 10x performance or the completed 7200-second result. The exact persisted activation and final receipt still need inspection. First supplied heartbeat is 07:20:58 UTC; expected finish around 12:21 Cyprus. Review is activation+14 days, expected 31 October if confirmed. No scanner/rules changes or Telegram destination/sender confirmation. Earlier sections describe their dated preparation/failure, superseded by this owner receipt.


Initial d3811acb installation completed by owner; HTTP 403 blocked the rollout.
Owner stopped early-lane rollout/export timer; engineering verified inactive.
Scanner/learner active with unchanged source hashes. Meme desk remains paused.
Prepared RPC source repair NOT applied. No Telegram/channel/sender confirmation.

Rules commit 959cdebdea5107f48bcc03b16c3968b34dc24fbe; frozen RULES hash unchanged.
New BUNDLE SHA-256 **41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d**. Owner bootstrap SHA **730096c0d5a67633289724711325c775af72b025d93e712f1a039af15d88df0c**.
Installed OLD bundle **d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442**. Canonical code in early_lane/ only.
SOURCE_REPAIR.md records diagnosis, actual probes, references, scope and caveats.
OWNER_COMMANDS.md contains the exact hash-checked root upgrade and subsequent
new 7200s log-only run; old commands must not be rerun over the installation.

## Files and hashes

| Runtime file | SHA-256 |
|---|---|
| `RULES.md` | `ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463` |
| `SOURCE_TERMS.md` | `48930c2c69a5eff6ae718429983bfd59ba1458d656bddbdce6f87483463cddaa` |
| `alerts.py` | `77f10d94bed0e7531ddca6bdc541c958b8c346c3784b4e8fe2bf6f1e19927b66` |
| `amm_layout.json` | `0d09f073d73b6c383cde4fe5d0dd6b9fe7464ad32157a129f3741be024894f14` |
| `core.py` | `9cf530c2fcd903c5e7fe5ce87072db80e4ea199da92dcbe332729ca88ef6d29f` |
| `exporter.py` | `09a3cf01201c5ae8ab5d752c9c13c91d891ea61ea4ec93fc9bc531fb6dbd3776` |
| `install.py` | `ee03897d72fa757431a8207171005ab5524075426b249e02ca7bf52d3f1c67d9` |
| `outcomes.py` | `cb8be632be6c2c9f30e90823c72ef3330a6648dc1141a914ae30de7584bc4edc` |
| `owner.py` | `730096c0d5a67633289724711325c775af72b025d93e712f1a039af15d88df0c` |
| `pricing.py` | `a30dcef7e01f447fe9e5f662ba03e7d02ac5c35e89842e4f253a7d9ca397056b` |
| `pump.py` | `7f9a46ab3fd5f144ae70f6ff5c3849c0e061cf59dd7bbd175ead7136bf0190e5` |
| `pump_layout.json` | `aec8f465e1c2cbd836df16b434a03d799a70d8373b7f21c5590eb9daa4143d14` |
| `service.py` | `c766ad143187d10fd56868fda78f1df2a5ccde57c6795b89dd4c20ab38d090b0` |
| `sources.py` | `37dea40243dc8169f9fc40d5eca86277e3000168870a3c2aab43be43433d7dc8` |
| `tests/test_evidence.py` | `c8105acba588c0eead148da73533cb102a62aac69ffd188035f0d8800e975a87` |
| `tests/test_lane.py` | `9c57d4ac9e83b02dc79dad164397bb85dbef65607bc98ff5e3a5b3fe0e7c2868` |
| `tests/test_network_contracts.py` | `fdb46921a631f9ee57ff753b09062567ce54e3493a8b1da7f234fa814cd38f1f` |
| `tests/test_pricing.py` | `add924f4c3f79616a5cf0e6d9ebff2d010fb86450982c46d2b50051c4ba1e377` |
| `tests/test_source_repair.py` | `fde4f74fa86b48235cec9a547db06d0cf0c5e08bdd767e455757e43f3ca42d1c` |
| `tests/test_transport_owner.py` | `ffab1859a4d54453cc0bce5d5f2a2fdf8513fe0d39c12e2b42167a5061c6e001` |
| `transport.py` | `98430ed385acd18319deb7e5186614dfe3a99fa3f36ad6cb0a946f624aa3e321` |
| `upgrade.py` | `a2da4ce63b0ec3314d7d2d6b54b965b20e7c781a1ebe8520b3098eef9a4aa082` |
| `verify.py` | `b6fc38cdddf9c33d331ad55f1b946bb274c23274869df39f8d090f73d1eb31b6` |

Human documentation is pinned by root MANIFEST.json, not inside the executable
bundle. Added pricing.py, upgrade.py, tests/test_pricing.py and source-repair tests.
Updated runner to use fresh on-chain marks without the website API; exporter unit
now uses scanner-only owner export. Embedded JSON-RPC throttles persist cooldowns.
No threshold or source-discovery population change. Unsupported quotes stay UNKNOWN.

## Results and open issues

109 offline tests pass locally and on server Python 3.12. Final gate
ef0ec2880fa7f644694937a5486b1919 passed 936 tests across 26 suites and verified
384 file hashes. Earlier initial-source release passed 910 repository tests; it did not
establish live feed access. Owner diagnostic: 597 launches, zero fresh market
snapshots. 0 valid polls/alerts/deliveries; no real two-hour result or outcome rates.
RPC health/account/census methods and on-chain oracle were observed. A recent
non-SOL curve remained unknown; no eligible alert or successful real full screening
claimed. Mandatory owner upgrade preflight aborts before unit changes if it cannot
obtain current authenticated prices from up to 30 owner-exported mints. A successful
pricing preflight does not establish full screening, complete coverage or profits.

Own user/config/state preserved. The upgrade requires inactive units, process lock,
valid old bundle/unit definitions and a hash-verified journal without activation or
cohort rows; never reset a nonempty study to bypass it. It backs up unit definitions,
installs a new root-owned hash directory and reloads definitions, starts no service.
No scanner database permission changes or other service restarts.

Installed source paths: /opt/vivameda-early-lane/<bundle-sha256>/.
Engineering staging: /var/lib/vivameda-engineering/repo/early_lane/.
State: /var/lib/vivameda-early-lane/; lane.sqlite3 (+WAL/SHM), mutable rpc_cache.sqlite3,
lane.log, tracked.json, process.lock, log_only_receipt.json. Inbox:
/var/lib/vivameda-early-lane-inbox/feed.json; root delivery config:
/etc/vivameda-early-lane/delivery.json. Current diagnostic-feed.json is private.
Original runtime stays intact. Proposed new root directory ends in 41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d.

Remaining: root preflight/application, new priced two-hour run, actual per-hour
candidate/pass/UNKNOWN coverage, full history/census throughput and three real
messages if any. NSFW excluded, source gaps, unsupported non-SOL/mayhem/boost pools,
metadata blocking and sampling remain limits. Telegram requires NEW confirmed
channel and existing authenticated sender; no keys/signup/paid calls authorized.
No claim of every token coverage or profitable execution. No automatic spending.

## Review date

No activation yet. Review is first fresh observational activation +14*86400s;
final cohort maturity +15*86400+120s. Failed input waiting never counts. Actual
calendar date must be calculated from that eventual receipt, not the old planned
31 October date. Daily summary remains 08:00 Asia/Nicosia. Review observed
multiples/dead/median peak time and suppressed 10x rate with coverage/denominators;
label associations exploratory and change no filters automatically.

Sender ownership correction: the owner reported vivameda-scout:vivameda-scout 0600
for the existing credential; the initial sender installer refused before writes.
The corrected independent sender preserves ownership/permissions, accepts the existing
scanner owner and adds the bounded read capability. See sender/ASTRA_HANDOVER.md
and its superseding install-only command. No credential/config/service mutation.

Latest owner amendment: use the existing scanner channel with 🌻. Old sender is
installed/stopped/disabled per owner receipt. Separate sender/ASTRA_HANDOVER.md and
sender/OWNER_COMMANDS.md supersede the earlier new-channel requirement, bundle
hashes and commands for this routing choice. New stopped upgrade/direct test pending;
continuous delivery remains off. Frozen rules and existing scanner are untouched.

Latest diagnosis: scanner destination is a private bot chat; 28ee6a42 installed/stopped
but one-off test refused the -100-only parser before config/API. Sender fix and
superseding owner command are in sender/ASTRA_HANDOVER.md and OWNER_COMMANDS.md.
Private-chat client compatibility remains open before automatic activation; no lane
runtime changes, service starts or confirmation changes were performed by engineering.
