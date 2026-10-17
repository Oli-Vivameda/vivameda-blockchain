# Early lane sender — source release — 17 October 2026

Prepared on current main 37190d5693fa3d62aff1fe2b1e4e3fa2e540cddf, preserving the
owner's RPC repair and log-only observation. Separate early_lane/sender/ code only;
existing lane runtime bundle and all frozen/scanner code are unchanged. No service
was installed, started, stopped or enabled, no delivery config was edited and no
Telegram request was made. Credential metadata was inaccessible to engineering;
no credential contents were opened.

39 offline sender tests pass on server Python 3.12. Full scripts/verify_release.py:
975 tests in 27 suites, 393 file hashes verified. Prepared unit syntax passes
systemd-analyze verify using an existing interpreter placeholder before installation;
the owner installer checks the actual new source/runtime paths during installation.
No live root sandbox or channel delivery validation is claimed.

BUNDLE.json SHA-256: f5b6bd39c8e12fe323c0242d5a81d437e59ee190b4c67c09ba3f4e17b3fd1dcc.
Bootstrap SHA-256: e209057c437d9ca24d9220a2de13ac4e1ef18c3ded434850b63cd10d2b58f268.

[Sender design/limits](../../early_lane/sender/README.md),
[owner install-without-start and one-message test](../../early_lane/sender/OWNER_COMMANDS.md),
[Astra handover, hashes and state](../../early_lane/sender/ASTRA_HANDOVER.md).

The numeric new channel, separate owner configuration and real channel test remain
open. Telegram's API cannot atomically commit with SQLite; uncertain sends are held
instead of automatically repeated. Normal queue retries honour persisted cooldowns.
The two-hour rollout's aggregate result is still pending. Source publication does
not confirm delivery readiness, universal discovery or profitable outcomes.
