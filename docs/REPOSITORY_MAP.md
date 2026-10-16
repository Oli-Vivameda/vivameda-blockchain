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
