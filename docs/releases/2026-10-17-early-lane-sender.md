# Early lane sender — source release — 17 October 2026

Prepared on current main 37190d5693fa3d62aff1fe2b1e4e3fa2e540cddf, preserving the
owner's RPC repair and log-only observation. Separate early_lane/sender/ code only;
existing lane runtime bundle and all frozen/scanner code are unchanged. No service
was installed, started, stopped or enabled, no delivery config was edited and no
Telegram request was made. Credential metadata was inaccessible to engineering;
no credential contents were opened.

46 offline sender tests pass on server Python 3.12. Full scripts/verify_release.py:
982 tests in 27 suites, 393 file hashes verified. Prepared unit syntax passes
systemd-analyze verify using an existing interpreter placeholder before installation;
the owner installer checks the actual new source/runtime paths during installation.
No live root sandbox or channel delivery validation is claimed.

BUNDLE.json SHA-256: 5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b.
Bootstrap SHA-256: 4f49e1ed7cd166527c2df008e4231fdf15bc2e2ecb040c973e6949209d2a3274.

[Sender design/limits](../../early_lane/sender/README.md),
[owner install-without-start and one-message test](../../early_lane/sender/OWNER_COMMANDS.md),
[Astra handover, hashes and state](../../early_lane/sender/ASTRA_HANDOVER.md).

The numeric new channel, separate owner configuration and real channel test remain
open. Telegram's API cannot atomically commit with SQLite; uncertain sends are held
instead of automatically repeated. Normal queue retries honour persisted cooldowns.
The two-hour rollout's aggregate result is still pending. Source publication does
not confirm delivery readiness, universal discovery or profitable outcomes.

## Owner-reported credential ownership correction

The first install stopped before writes: existing credential is a regular 0600 file
owned by vivameda-scout, not root as initially assumed. Source now accepts only root
or the existing scanner UID with owner-only access. Root-only delivery configuration
checks stay intact. Installer still inspects metadata only; runtime reads the existing
file without copying or changing it. The sandbox bounds capabilities to
CAP_DAC_READ_SEARCH to permit that read, with scanner data inaccessible. Seven added
regression tests pass: 46 sender tests, 982 full repository tests across 27 suites;
393 file hashes and proposed unit syntax verified. No service installed/started or
Telegram message sent by engineering. The first failed attempt requires no cleanup;
use the corrected bundle command linked above.

## Owner amendment: existing scanner channel with 🌻

Owner confirmed the corrected sender installed, stopped, disabled, with delivery
config untouched. Owner subsequently chose the scanner's existing chat and 🌻 prefix.
New source permits that one exact root-config destination only with an explicit
reuse_scanner_channel=true flag. The owner command hash-checks a stopped upgrade,
preserves state, prepares lane-only routing and sends one fixed direct 🌻 test;
new_channel_confirmed remains false, confirmed_at null, no services start/enable.
The scanner credential/source/permissions and frozen rules remain unchanged.
58 sender tests; complete Python 3.12 gate 994 tests / 27 suites / 393 hashes;
proposed unit syntax passes. Engineering sent no Telegram. See superseding
sender/ASTRA_HANDOVER.md for hashes and sender/OWNER_COMMANDS.md for the exact command.

## Private bot-chat correction

Owner metadata-only diagnostic established private_chat destination; delivery unset,
confirmation false. Installed 28ee6a42's test refused its -100-only parser before any
config mutation/API send. Corrected sender permits private/basic-group numeric IDs
only under explicit root-config shared opt-in and exact scanner chat_id match. The
new owner command upgrades the stopped 28ee6a42 install and runs one idempotent 🌻
test, leaving continuous confirmation off. Four new regressions, 58 sender tests,
994 full tests / 27 suites / 393 hashes; proposed unit syntax verified. No Telegram
sent by engineering. Current lane transport still requires -100 on activation;
separate client compatibility and rollout readiness review remain explicit blockers.
