# Rollout record — 17 October 2026

Status: **BLOCKED, not a live rollout pass.** No early-lane service installed or
started. No Telegram delivery, channel TBD. Meme desk remains paused.

- Frozen rules commit: `959cdebdea5107f48bcc03b16c3968b34dc24fbe`, before selection.
- 83 isolated offline early-lane tests pass locally and on the engineering server
  (Python 3.12.3, non-root UID 994). Tests include parser/authentication, first-two-
  produced-block union, aggregated holders, supply gaps, incomplete history/cursor,
  rate limits, thresholds, immutability/restart, checkpoints and DST.
- Final full-repository gate c99101fea031cee44714cb587da5317b: 910 tests across 26
  isolated suites pass; 378 file hashes verified; complete live setup false.
- Server test/probe job: `1a0919e201d3febe88c6142a8b58be44` succeeded. Input path
  absent; one immediate missing-input probe; 0 valid owner-feed polls; 0 Telegram
  messages. This probe does not measure two-hour candidate volume or qualify a
  rollout. Counts by hour/filter and three genuine example alerts are unavailable.
- Separate connectivity probe `0b3d2a58e8ffe19b3a87fa3a2e03985d` returned RPC health
  `ok` and a public RPC WebSocket HTTP 101 handshake. No feed subscription or full
  history/census integration was established by that probe.
- Three synthetic message examples are in EXAMPLES.md, clearly labelled. No real
  live alert/case rows are published.

Required next evidence: install reviewed source using the owner command, enable only
its read-only export timer, then run the dedicated 7200-second log-only command in
the SAME state directory intended for live use. Inspect the receipt's start/end,
valid polls, maximum gap, hourly unique candidate/pass counts and UNKNOWN reasons.
The convenience continuity gate requires elapsed >=7200s and no valid-feed gap >120s;
this does not establish universal launch coverage, sufficient RPC throughput or an
end-to-end delivery pass. Report those separately. Missing-input waiting is failure.

Telegram remains disabled throughout log-only regardless of any delivery config.
After inspecting the real receipt and confirming a new destination and compatible
sender, the separate continuous lane can run. Do not reset the journal to promote.
