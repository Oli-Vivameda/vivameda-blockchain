# Repository map

Updated 16 October 2026. This repository is the canonical public home of Vivameda's Crypto Lab.

| Material | Home |
|---|---|
| Current scanner, wallet code and tests | `scout/`; scanner entry point `scout/early_scout.py` |
| Independent monitors | `monitors/<component>/` |
| Agent interpretation | `agent/` |
| Learning, frozen studies and shadow models | `learning/`, `research/` |
| Service templates and utilities | `deploy/`, `scripts/` |
| Current explanations | `docs/` |
| Dated releases and historical overview | `docs/releases/`, `docs/history/` |
| Company/workforce intelligence | [vivameda-intelligence-stack](https://github.com/Oli-Vivameda/vivameda-intelligence-stack) |
| Private operations, credentials and runtime evidence | Access-controlled server archive |

Both GitHub repositories reported public visibility on 16 October 2026. A repository name or old description is not a privacy control.

## Discovery release

- [Canonical source](../scout/early_scout.py)
- [Portable offline tests](../scout/test_discovery_guard.py)
- [Preserved-function contract](../scout/discovery_function_contract.json)
- [Explanation](DISCOVERY_SAFEGUARDS.md)
- [Dated evidence](releases/2026-10-16-discovery.md)

The stack's former discovery folder becomes a redirect. Its historical Git commits remain available; current scanner fixtures and operational candidates are not duplicated between repositories. Existing frozen research source snapshots remain intact because they are provenance records.

This cleanup covers the discovery release and navigation. It does not claim every later server component has been audited or synchronized.

## Isolated Solana copy paper experiment — 16 October 2026

The separate [copy-paper project](../copy_trading/README.md) contains its frozen empty watchlist, accounting, tests and dedicated installer. It is **WAITING_FOR_VERIFIED_WALLETS**. Source publication does not mean the service is installed: the engineering connector cannot create its dedicated system unit. Strategy B and quote-provider access remain disabled. See the [release receipt](releases/2026-10-16-copy-paper.md) for exact verification, limitations and the owner installation command.

## Human-review meme desk v1 — 17 October 2026

Separate [source and operating instructions](../meme_desk/README.md) cover exit-rule replay and manual trade tickets. The [preregistration](../meme_desk/REPLAY_PROTOCOL.md) was committed before replay code/tests. Historical replay and a genuine 60-minute shadow run are **blocked pending owner export and authenticated reserve evidence**. No service is installed; no ticket destination/sender confirmed. Existing scanner and frozen-study boundaries are unchanged. See the [release status](releases/2026-10-17-meme-desk.md) and [Astra handover](../meme_desk/ASTRA_HANDOVER.md) for exact hash-checked owner commands.
