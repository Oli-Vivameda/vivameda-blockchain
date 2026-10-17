# Astra handover — early lane v1 — 17 October 2026

Source built and offline tested; LIVE VALIDATION BLOCKED, NOT INSTALLED. No early-
lane service, export timer or sender was started. Scanner/scoring/screening/alert
population/monitors/studies/running services were not changed. Meme desk remains
paused at commit 18bd27ae77d56fb258dea090113f461e70936382; do not execute its old
handover's next actions.

## Published identity and files

Canonical repository: Oli-Vivameda/vivameda-blockchain; source ONLY in early_lane/.
Frozen rules commit: **959cdebdea5107f48bcc03b16c3968b34dc24fbe** (before any alerts
or fixture selection). Official Pump instruction/account maps pinned to public-docs
commit 639b87fb45c3adeffa6f7c4a1bf0cb85e392bf22. Never change RULES.md for this cohort.

Runtime bundle SHA-256: **d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442**. BUNDLE.json lists executable-source/fixture/
layout/rules hashes; explanatory Markdown is pinned by repository MANIFEST.json.
owner.py's bootstrap hash is independently specified in OWNER_COMMANDS.md. Every
owner operation snapshots verified bytes before executing project imports.

| File | SHA-256 |
|---|---|
| `RULES.md` | `ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463` |
| `SOURCE_TERMS.md` | `48930c2c69a5eff6ae718429983bfd59ba1458d656bddbdce6f87483463cddaa` |
| `alerts.py` | `77f10d94bed0e7531ddca6bdc541c958b8c346c3784b4e8fe2bf6f1e19927b66` |
| `amm_layout.json` | `0d09f073d73b6c383cde4fe5d0dd6b9fe7464ad32157a129f3741be024894f14` |
| `core.py` | `0499f1f31ee7a8c50c3ed4ef04777f1ead4f3bebabc4c48521d0730b69a9dbb1` |
| `exporter.py` | `09a3cf01201c5ae8ab5d752c9c13c91d891ea61ea4ec93fc9bc531fb6dbd3776` |
| `install.py` | `20e0372db1188c4a5949d3931ce0e39ae6ae2b15403fde6fc0439687bfe190ed` |
| `outcomes.py` | `cb8be632be6c2c9f30e90823c72ef3330a6648dc1141a914ae30de7584bc4edc` |
| `owner.py` | `169412fafe354bb875e18bd7dd14a6a069b0b5ebd9320d0a8921eb84aa578eb3` |
| `pump.py` | `7f9a46ab3fd5f144ae70f6ff5c3849c0e061cf59dd7bbd175ead7136bf0190e5` |
| `pump_layout.json` | `aec8f465e1c2cbd836df16b434a03d799a70d8373b7f21c5590eb9daa4143d14` |
| `service.py` | `051b1020447252bc84debd8abe7eee6d8e5eec9820f415708fb3b4ce77f18677` |
| `sources.py` | `6652458f1f3a414b508ed3d1f22086bd22276254c063ffbda7e2e2af7f89dcc7` |
| `tests/test_evidence.py` | `b5c1958b2cf8d151bf11d40f4c5355fdd5fca6a3501a23a1860ec35819da5d7a` |
| `tests/test_lane.py` | `9c57d4ac9e83b02dc79dad164397bb85dbef65607bc98ff5e3a5b3fe0e7c2868` |
| `tests/test_network_contracts.py` | `fdb46921a631f9ee57ff753b09062567ce54e3493a8b1da7f234fa814cd38f1f` |
| `tests/test_transport_owner.py` | `ffab1859a4d54453cc0bce5d5f2a2fdf8513fe0d39c12e2b42167a5061c6e001` |
| `transport.py` | `98430ed385acd18319deb7e5186614dfe3a99fa3f36ad6cb0a946f624aa3e321` |
| `verify.py` | `b6fc38cdddf9c33d331ad55f1b946bb274c23274869df39f8d090f73d1eb31b6` |

Files: core predicates/journal; outcomes; normalized Pump parser + pinned layouts;
bounded public HTTPS/RPC collector; owner exporter; compact messages/outbox;
optional Unix transport; runner; verifier/bootstrap/installer; four test modules;
RULES/SOURCE_TERMS; README/STATUS/ROLLOUT/EXAMPLES/OWNER_COMMANDS/this handover.

## Verification and actual results

83 offline tests pass locally and under server Python 3.12.3. Final release job
c99101fea031cee44714cb587da5317b passed 910 tests across 26 isolated suites and
verified 378 file hashes. Earlier job 839d92d65f2274b426b57a79b4a6f13a ran
systemd-analyze verify: exit 0 for all three NEW unit definitions. Tests make no
network calls or Telegram sends. Complete live setup remains false.

Owner-input probe job 1a0919e201d3febe88c6142a8b58be44: required feed absent, 0 valid
polls, 0 deliveries, rollout false. This is not a genuine two-hour run. No measured
candidate/hour or filter pass counts and no three real examples exist. EXAMPLES.md
contains three synthetic formatting fixtures only. Public RPC health/HTTP101 probe
0b3d2a58e8ffe19b3a87fa3a2e03985d establishes connectivity only, not trade-history,
holder-census or universal launch coverage. No real 10x result is available.

Selected source: owner-run read-only scanner data/public-feed refresh plus public
Solana RPC. PumpPortal excluded: metered trade streams require funded wallet/API
key; public terms did not establish redistribution permission. SOURCE_TERMS.md
records primary sources. No credentials, accounts, payments or wallet connection.

## State, units and owner commands

Engineering source: /var/lib/vivameda-engineering/repo/early_lane/.
Private engineering probe: client_learning/early_lane_v1_20261017/probe-state/;
it has no activation or real cohorts and must not seed the observational state.

Installed source (NOT created): /opt/vivameda-early-lane/d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442/.
State (NOT created): /var/lib/vivameda-early-lane/; append-only lane.sqlite3 (+WAL/
SHM), mutable rpc_cache.sqlite3, tracked.json, bounded lane.log, process.lock and
log_only_receipt.json. Never reset state on promotion; it binds one-ever selection,
cap-suppressed anchors and activation. Root-controlled inbox:
/var/lib/vivameda-early-lane-inbox/feed.json and feed_cooldown.json. Root-controlled
delivery configuration: /etc/vivameda-early-lane/delivery.json (unconfirmed).

Units (NOT installed): vivameda-early-lane.service, vivameda-early-lane-export.service,
vivameda-early-lane-export.timer. Own unprivileged user vivameda-early-lane; only the
owner-approved exporter can read scanner DB. No DB permission changes. Installer
creates root-owned source/config and units, refuses existing installs, and starts
or enables nothing. New exporter alone has CHOWN/DAC_READ_SEARCH for its own output
and read-only DB access under ProtectSystem=strict. Root operations unavailable via
engineering connector; no escalation attempted.

Use **OWNER_COMMANDS.md**, in order: hash-checked installer, only the new read-only
export timer, durable 7200-second log-only rollout, private aggregate receipt review.
The two-hour state becomes the eventual continuous state, preserving all cohort
anchors. Commands have passed shell syntax checks; they were not run. Log-only never
sends, and its cohorts remain excluded from future delivery even if confirmation
predated them. Actual delivery additionally needs Oli's NEW channel and a compatible
existing authenticated Unix sender. None is available or installed. Only then use
the documented continuous-unit start. A stop command affects only new lane units.

## Open issues and next actions

1. Owner installation/export is necessary before real rollout. Measure actual
   discovery delay, candidate throughput/hour, unique-mint pass-each and sequential
   counts, UNKNOWN reasons, rolling suppression, checkpoint availability and disk.
2. Existing NSFW-excluded feed cannot prove every Pump launch. Pagination may hit
   its bound. Public RPC may block full census/history or overwhelm the 12-call
   cycle; incomplete evidence blocks alerts. Never relax rules to manufacture volume.
3. Provider market caps are response observations, not executable prices. Sampling
   misses peaks/crossings. Independent liquidity-drain evidence is absent; unknown
   liquidity is never zero. Dead is normally cap <30%, not proof of fraud.
4. Unsupported layouts, USDC quote/mayhem and non-metadata Token-2022 extensions
   remain UNKNOWN. Reaching a social URL proves neither authenticity nor safety.
   Rug-name reuse rule was explicitly omitted, without an eligible verified registry.
5. Sender is a contract, not an installed Telegram adapter. Require actual receipts,
   durable idempotency and Retry-After. Destination TBD; do not use scanner's chat.
6. Daily 08:00 Asia/Nicosia summaries are provisional. Day-14 explorer uses within-
   PASS feature contrasts, cannot causally rank filters or estimate outcomes of
   dropping a filter. Failed-filter outcomes are unavailable; say not estimable.
   Ten-percent observed 10x is a descriptive owner benchmark, never a funding action.

## 14-day review date

**Not started: activation is null.** Freeze/review starts at the first successful
fresh owner-input observational polling cycle, including the approved log-only run.
Day 14 = that UTC epoch +1,209,600s; final maturation = +1,296,120s. If activation is
17 October, review date is 31 October 2026 and final follow-up 1 November +120s at
the corresponding UTC time. Cyprus DST can shift the local hour. Report alerts,
2x/3x/5x/10x rates with denominators/coverage, dead rate and median observed time to
peak, suppressed 10x rate, and labelled exploratory associations. Change nothing
automatically. No synthetic or missing-input probe starts that clock.
