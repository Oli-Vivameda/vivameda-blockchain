# Private price-action audit

Completed 11 October 2026. The owner ran the audit and chart recovery; the fixed-window study is complete. The audit and recovery changed no production behavior. All 20 audit, recovery and study tests passed. See FINDINGS_20261011.md for the initial audit and RECOVERED_CHART_STUDY_20261011.md for the subsequent recovered-chart analysis.

The auditor reads all retained non-holdout V2 ALERT events, matches the separate fire-delivery ledger, preserves repeat calls in the casebook and compares only first calls per mint. It excludes every pl_predictions mint without reading any prediction body, model probability or protected outcome. Missing and deleted histories remain missing.

For each call it produces a private SVG chart and case record. Before-call charts use actual retained price samples; historical case features cannot recreate expired candles. After-call charts use recorded market-cap observations and explicitly mark that proxy and unverified pool/supply continuity. Gaps above 180 seconds are disconnected. No provider, chart API, paid data, credentials, Telegram API or network calls are used.

At 1h, 3h, 6h and 24h it checks existing timely endpoints and independently verifies observation coverage. It separates first observed 2x versus 50% loss, maximum drawdown, drawdown before 2x, held gains at the endpoint, and brief spikes followed by collapse. First sampled barrier crossings do not establish intraminute execution order or realized profits. No global ATH or late backfill is used.

Before-call comparisons cover range width, buying share, volume, acceleration, liquidity, momentum and, when saved price samples suffice, slope, drawdown, higher lows, range compression and breakout position. Comparisons separately show chronological earlier/later groups and regimes. These are descriptive hypotheses; no rule is fitted, weights updated or entry/notification policy promoted.

## Owner command

The connector's nonroot engineering account cannot read the production database or the delivery ledger. The following fixed-path, source-hash-checked command performs the already requested audit using the owner's existing SSH access. It changes no production source, permissions, services, relay configuration or history.

~~~sh
ssh -i ~/.ssh/vivameda_chatgpt_ed25519 -o IdentitiesOnly=yes root@77.42.42.75 'python3 /var/lib/vivameda-engineering/repo/client_learning/crypto_chart_audit_20261011/audit.py --owner-audit --expected-sha256 a6be3b3fcf8af373ef13a06da1eb60a78f7cba14fa952693f7d60ea4b9a98bd5'
~~~

Outputs stay private in an engineering-owned 0700 timestamped results directory; files are 0600. The receipt reports coverage and outcome totals. The assistant can then read REPORT.md and audit.json through the server connection and inspect the charts. Manual conversational mentions or deleted Telegram messages are not claimed to be covered. The historical commands are retained for reproducibility; the owner already completed them. Private result files and token-level charts are excluded from this public folder.

## Verification

11 tests passed locally and on the engineering server (Python 3.12). Tests cover stop-before-rebound, spike/collapse separation, late or invalid checkpoints, gaps, future data exclusion, pending cases, mixed pools, exclusion of protected bodies/outcomes, first-call deduplication and missing charts.

~~~sh
python3 -m unittest discover -s client_learning/crypto_chart_audit_20261011 -p 'test_*.py' -v
~~~

Implementation SHA-256: a6be3b3fcf8af373ef13a06da1eb60a78f7cba14fa952693f7d60ea4b9a98bd5
Tests SHA-256: 59dbee8d79c42abb5bdc3bfbfe65ce532f5de8a846375d506c5986b30bb7e42f
