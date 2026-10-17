# Vivameda Blockchain

Public source and documentation for Vivameda's Crypto Lab: Solana small-cap discovery, wallet screening, monitoring, agent interpretation and prospective outcome research.

**Start with the [repository map](../../docs/REPOSITORY_MAP.md).** Crypto source belongs here. Company/workforce intelligence belongs in [vivameda-intelligence-stack](https://github.com/Oli-Vivameda/vivameda-intelligence-stack). Credentials, private configuration and runtime databases stay on the server.

## Latest scanner release — 16 October 2026

[Discovery safeguards](../../docs/DISCOVERY_SAFEGUARDS.md) are deployed: independent feed commits, bounded catch-up, malformed-row handling, discovery-delay measurements and system-level health warnings. The retained postflight showed both feeds saving data, with one invalid trade-feed row excluded.

The canonical scanner is [scout/early_scout.py](../../scout/early_scout.py). Its SHA-256 matches the deployed snapshot in [the release record](../../docs/releases/2026-10-16-discovery.md). This publication does not redeploy services. A dated source snapshot is not continuous live status.

| Area | Location |
|---|---|
| Scanner, wallet screening and tests | [scout/](../../scout/) |
| Independent watchlist and research monitors | [monitors/](../../monitors/) |
| Crypto agent and bounded interpretation | [agent/](../../agent/) |
| Timed learning and chart analysis | [learning/](../../learning/) |
| Frozen studies, shadow models and baseline | [research/](../../research/) |
| Paper trading scaffold | [agent_trader/](../../agent_trader/) |
| Service templates and utilities | [deploy/](../../deploy/), [scripts/](../../scripts/) |
| Explanations and dated records | [docs/](../../docs/), [changelog](../../CHANGELOG.md) |

Read [signals](../../SIGNALS.md), [full setup](../../docs/FULL_SETUP.md), [screening](../../scout/SCREENING_V2.md), [security](../../SECURITY.md) and the [maintenance policy](../../docs/REPOSITORY_POLICY.md). The [earlier overview and updates](../../docs/history/README_THROUGH_20261011.md) remain available as dated history.

## Verify

Use Python 3.12; frozen scorer AST contracts are version-bound.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt -r research/requirements.txt
.venv/bin/python -m unittest discover -s scout -p 'test_discovery_guard.py'
.venv/bin/python scripts/verify_release.py
```

Publication validation: **735 tests passed across 23 isolated suites**; see the [dated validation record](../../docs/PUBLICATION_VALIDATION_20261016.json).

The verifier checks the file manifest and runs every test directory in isolated processes. Discovery tests extract scanner definitions without importing the production module or accessing providers, Telegram or production state.

Scores are not calibrated probabilities; observed peak multiples are not realized profit. Complete discovery coverage, profitable execution and completed prospective model validation have not been established. The [published baseline result](../../research/README.md) remains experimental. Frozen study artifacts retain their dates and gates. Fresh-host installation remains unverified. No license grant has been selected.

## Isolated Solana copy paper experiment — 16 October 2026

The separate [copy-paper project](../../copy_trading/README.md) contains its frozen empty watchlist, accounting, tests and dedicated installer. It is **WAITING_FOR_VERIFIED_WALLETS**. Source publication does not mean the service is installed: the engineering connector cannot create its dedicated system unit. Strategy B and quote-provider access remain disabled. See the [release receipt](../../docs/releases/2026-10-16-copy-paper.md) for exact verification, limitations and the owner installation command.

## Human-review meme desk v1 — 17 October 2026

Separate [source and operating instructions](../../meme_desk/README.md) cover exit-rule replay and manual trade tickets. The [preregistration](../../meme_desk/REPLAY_PROTOCOL.md) was committed before replay code/tests. Historical replay and a genuine 60-minute shadow run are **blocked pending owner export and authenticated reserve evidence**. No service is installed; no ticket destination/sender confirmed. Existing scanner and frozen-study boundaries are unchanged. See the [release status](../../docs/releases/2026-10-17-meme-desk.md) and [Astra handover](../../meme_desk/ASTRA_HANDOVER.md) for exact hash-checked owner commands.
