# Copy paper release — 16 October 2026

1. Scope: dedicated Solana spot paper experiment, no real transactions, keys or Telegram; existing agents preserved.
2. Source: `copy_trading/`; server staging `client_learning/solana_copy_paper_20261016/`. Public repository remains the blockchain repository.
3. Selection: no suitable verified wallets admitted; frozen empty watchlist WAITING_FOR_VERIFIED_WALLETS. Sources/rejections in watchlist.json. No claimed social returns accepted.
4. Configuration: A $250, $25 all-in buy/token, $75 total open cost, three tokens, no repeats, 30-second entry age, 5% chase, 2-second minimum execution delay, 10% persistent drawdown pause. A proportional source exits. B disabled.
5. Execution: quote estimates only. No authorized free quote endpoint configured. Fresh reverse sellability required. Unknown blocking evidence skips. USDC peg and network/rent allowance are explicit assumptions.
6. Validation: see project VALIDATION.md and full repository release gate. Synthetic tests stay separate. Final scoped suite contains 39 tests, including closed-cycle accounting. Exact release hash below pins source, tests and instructions.
7. Connectivity/recovery: server public RPC getHealth succeeded in 2.011 seconds; repeated smoke invocation retained bindings and balances. This is not wallet-event latency or continuous monitoring.
8. Runtime: dedicated vivameda-copy-paper.service is NOT installed/running. Engineering UID has no user manager/linger; no authorized custom-unit deploy tool is exposed. Existing units were not restarted. No genuine source signals or fills observed.
9. Review: source excludes secrets/runtime databases; staged source and installer hashes verified separately. Narrow Jupiter coverage, source ROI limitations, stale marks, failed/superseded exits and reporting denominators are documented. No profitability conclusion.
10. Next gate: owner installs the exact reviewed release, then inspect heartbeat/restart/feed. Verified wallets and an authorized free quote provider require a separately frozen experiment. Inspect/pause/stop commands are in the project README.

Release SHA-256: `d7591b0f13e21a2e51993f18adc9b9691b4e45bbafc8f713a5e297dfdf3aa13e`

Installer SHA-256: `bff06b440b407833bcd2fb0b5cfc378fb1ea2569c76475df205c9b43a2e27c9a`

Owner command (hash-checks installer bytes before executing; only installs the dedicated paper service):

```sh
ssh vivameda-server 'sudo python3 -c '"'"'import hashlib,pathlib,sys; p=pathlib.Path('"'"'"'"'"'"'"'"'/var/lib/vivameda-engineering/repo/client_learning/solana_copy_paper_20261016/install.py'"'"'"'"'"'"'"'"'); b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='"'"'"'"'"'"'"'"'bff06b440b407833bcd2fb0b5cfc378fb1ea2569c76475df205c9b43a2e27c9a'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'Installer hash mismatch'"'"'"'"'"'"'"'"'; sys.argv=[str(p),'"'"'"'"'"'"'"'"'--expected-release-sha256'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'d7591b0f13e21a2e51993f18adc9b9691b4e45bbafc8f713a5e297dfdf3aa13e'"'"'"'"'"'"'"'"']; exec(compile(b,str(p),'"'"'"'"'"'"'"'"'exec'"'"'"'"'"'"'"'"'),dict(__name__='"'"'"'"'"'"'"'"'__main__'"'"'"'"'"'"'"'"',__file__=str(p)))'"'"''
```

The installer refuses an existing installation and never migrates/reset balances automatically. It must not be replaced by a scanner deployment tool. After running, confirm systemctl status, journal heartbeat and the report's frozen binding. The empty watchlist should remain WAITING_FOR_VERIFIED_WALLETS. A running process is not evidence of profitability.

Repository release gate: **774 tests passed across 24 suites**, including 39 copy-paper tests, on server Python 3.12.3 in 32.382 seconds (job `165b5fe6d55f65163b8cae2e15948f65`). All 325 source/doc hashes at that gate matched. A local attempt was blocked by Unix-socket restrictions in an existing runtime test; the server run passed that test. Only this receipt and its manifest hash were amended afterward; source and frozen project release are unchanged.

Final scoped source verification: job `68dbc174e90369ba1cb91b71d20286bb` verified release `d7591b0f13e21a2e51993f18adc9b9691b4e45bbafc8f713a5e297dfdf3aa13e`, passed 39 tests and reached the public RPC in 1.699 seconds. These are bounded smoke checks, not continuous forward monitoring.
