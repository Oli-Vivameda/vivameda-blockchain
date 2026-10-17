# Validation and ticket examples

53 scoped offline tests pass locally. Fixtures are synthetic and independent of the scanner database. Server validation receipts are recorded in ASTRA_HANDOVER.md. No test sends Telegram or calls a provider.

Live 60-minute shadow run: BLOCKED, not performed. The bounded startup probe recorded 0 tickets and 0 valid export polls because no owner export exists. This is not a zero-opportunity result and not a passed dry run. Two rendered examples below test format only, not live production.

```text
SYNTHETIC EXAMPLE — NOT A LIVE ALERT; DO NOT TRADE
MANUAL REVIEW; desk never executes
TEST-1 | LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
Alert age 0s
Token age: 3600.0 seconds | MC $1000000.0 | liquidity $200000.0
Regime CONTINUATION | score 9
Current 1.0; entry ceiling 1.030; size $10
Impact in/out: 0.0099990000999900009999000100% / 0.0099990000999900009999000100%; round-trip estimate 3.519998000199980001999800020%
Costs: 1% swap each side + three $0.05 network charges for split plan A.
Plan A: half at 1.400; stop unsold at 0.750; time exit 06:07:04 UTC
Levels reference current snapshot; adjust to actual manual fill.
VOID if liquidity <$160000.00, any new REJECT, ceiling breached or data stale.
UNKNOWN: none reported
Counter-evidence: Authenticated reserve captures and screening do not guarantee sellability; protocol upgrade/admin risk remains.
Replay A, this regime: no replay yet
https://dexscreener.com/solana/LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
https://jup.ag/swap/SOL-LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
[TAKEN] [SKIP → fixed reason]
```

```text
SYNTHETIC EXAMPLE — NOT A LIVE ALERT; DO NOT TRADE
MANUAL REVIEW; desk never executes
TEST-2 | LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
Alert age 0s
Token age: 3600.0 seconds | MC $2000000.0 | liquidity $400000.0
Regime RECLAIM | score 10
Current 2.0; entry ceiling 2.060; size $10
Impact in/out: 0.0049997500124993750312484400% / 0.0049997500124993750312484400%; round-trip estimate 3.509999500024998750062496880%
Costs: 1% swap each side + three $0.05 network charges for split plan A.
Plan A: half at 2.800; stop unsold at 1.500; time exit 06:07:04 UTC
Levels reference current snapshot; adjust to actual manual fill.
VOID if liquidity <$320000.00, any new REJECT, ceiling breached or data stale.
UNKNOWN: none reported
Counter-evidence: Authenticated reserve captures and screening do not guarantee sellability; protocol upgrade/admin risk remains.
Replay A, this regime: no replay yet
https://dexscreener.com/solana/LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
https://jup.ag/swap/SOL-LbUiWL3xVV8hTFYBVdbTNrpDo41NKS6o3LHHuDzjfcY
[TAKEN] [SKIP → fixed reason]
```

Final server release gate: 827 tests across 25 suites passed, including 53 desk tests (33.885 seconds), job d30bdb5932f7d18ad98c8c49e3acf64f. Live replay/dry-run gates remain blocked.
