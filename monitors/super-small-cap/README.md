# Third trigger: super-small-cap research

11 October 2026. An independent SHADOW collector for Solana tokens first observed at $10k–$20k reported market cap, plus additive agent instructions and a separate short-window review validator. Existing scanner and $100k–$500k watchlist sources, configuration and delivery histories are not changed. No expiry or live trading.

This first version samples DexScreener latest profiles. It is not complete launch discovery: unprofiled coins can be missed, provider data can lag, and bounded rotating polling can miss rapid band crossings. The current scanner selects tokens from $30k; its alert feed cannot supply this earlier universe. PumpPortal's documented token trade feed is metered and is not enabled. No paid provider, API key, wallet or trading endpoint is used.

The collector polls at most two fixed free endpoints per cycle, follows profiled candidates for 24 hours after discovery, saves each available exact-pair price/cap/liquidity sample and freezes each mint's first observed band entry. Different pools remain separate in observations. Provider response hashes and receipt times are recorded; provider event time, organic buyers and executable exits remain unknown. Missing market cap is not replaced by FDV. Evidence remains in a dedicated private SQLite database. Storage above 512 MiB pauses capture without deleting history. There is no complete-all-launches claim.

AGENT_RULES.md carries the learned distinctions: peak versus held gain, winners and failures, no mandatory positive return/higher lows, narrow-range/buying-share hypotheses without hard profitability thresholds, protocol-specific screening and explicit unknowns. classifier.py validates independent reviews with a provisional 60–180 second observed window. It does not produce reviews, verify the semantic truth of evidence, send messages or train weights. Even a validated FIRE_REVIEWED result cannot send Telegram in this SHADOW installation. Agent fixed dispatch and factual safeguards remain intact; fresh processes load the additional instructions, but autonomous review dispatch is not enabled.

## Owner activation

The installer's --hash prints the reviewed bundle hash. Run --expected-sha256 HASH without --install for validation. Root --install checks the previously installed agent hash, appends only this trigger's instructions, installs separate units/private storage, runs the first shadow collection, verifies the existing trigger source hashes, and enables only its own timer. The owner installation receipt confirms activation of this separate SHADOW collector. It never restarts the existing triggers. A failed install restores its own agent patch where safe and preserves captured evidence for diagnosis.

Engineering source: client_learning/crypto_super_small_cap_20261011. Runtime: /opt/vivameda-super-small-cap. State: /var/lib/vivameda-super-small-cap. Timer: vivameda-super-small-cap.timer. To pause only this trigger, disable its timer and stop its service. STOP in its state directory suppresses collection.

## Validation and remaining work

16 synthetic tests cover short-window evidence, incomplete/rejected screening, evidence version binding, band boundaries, deduplication, pair identity, FDV exclusion, immutable first entries, failure retention, provider errors, actual receipt time after fetching, request budget, shadow isolation and additive instruction loading. Private records are excluded from publication.

Next: verify capture latency/coverage from owner installation, add a reviewed direct launch/transaction adapter within an approved data budget, implement transaction-level buyer/funding evidence and venue-specific screening, and integrate independent review plus prospective outcomes before enabling a separately labelled experimental Telegram stream. No short-window profitability or validated 100x probability is claimed.

Sources: https://docs.dexscreener.com/api/reference ; https://pumpportal.fun/data-api/real-time/ ; https://solana.com/docs/rpc/websocket/logssubscribe .

Reviewed bundle SHA-256: 371e55050a77d27a222764d5365968fae013528f5dbfc116aacaa1dac320137d

```sh
ssh vivameda-server 'python3 /var/lib/vivameda-engineering/repo/client_learning/crypto_super_small_cap_20261011/install.py --install --expected-sha256 371e55050a77d27a222764d5365968fae013528f5dbfc116aacaa1dac320137d'
```

Validation: all 16 tests passed on server Python 3.12; both unit files verified. A single live free profile request returned 30 profiles. No private production data, Telegram messages or paid requests were used in that feed check. Owner installation completed; the first collection reported no errors.

## Owner installation receipt — 11 October 2026

The owner reported successful installation, 16 passing tests and enabling `vivameda-super-small-cap.timer`. The first SHADOW run at Unix timestamp `1791738657` observed 22 tokens, saved 22 samples, recorded four band entries and completed two provider requests with no errors. Band entries are DISCOVERY records; they are not independently reviewed runner calls.

No expiry is configured. Existing trigger sources and configuration remained unchanged. Fresh agent processes load the additional instructions. Independent review production and Telegram delivery remain disabled; zero messages were sent. No live execution or weight update occurred. Coverage remains limited to profiled Solana tokens and bounded polling. Capture latency, continuing service health and prospective outcomes have not been independently verified from this receipt.

Installed agent source SHA-256: `44f1368e772f7b27724665ebe06cf34aa0a0a95d3f849a98bdf44f92d21f39c3`. Reviewed bundle SHA-256 remains `371e55050a77d27a222764d5365968fae013528f5dbfc116aacaa1dac320137d`. Evidence source: owner terminal receipt; no independent production re-read.
