# Discovery safeguards — 16 October 2026

The owner authorized independent discovery persistence, bounded catch-up and system-level warnings. Public code lives once at [scout/early_scout.py](../../scout/early_scout.py), with [offline tests](../../scout/test_discovery_guard.py) beside it.

| Artifact | SHA-256 |
|---|---|
| Deployed/published scanner | `6790a2c192bbdecfcd17abbe6f41f774675f059e5fab52edb0b6b2ab99b4dbf1` |
| Reviewed pre-release scanner | `94760d552d54bdba8ed047276e44e8b5d44cd9ec2413f295065464a4f71c96a5` |
| Unchanged tracker | `a519ad19680ba72f0d593c4627fe5faa2d8dfa93fcd112eaba21abcf5a6da9b6` |
| Scoped deployment bundle | `532e1f7a863f55637e4c698a575d8ad1829f539757fc0a75d471572462226a56` |

## Verification

The server release passed 41 focused discovery, 13 transport and 10 existing stack checks. Deployment reported scanner and learning services active. Retained logs at 06:10 UTC showed a creation page saved and a trade page saving 69 valid rows after excluding one malformed row.

The first strict whole-page validator rejected a trade page because of one invalid market field. The final correction excludes bad rows independently and records persistent degraded quality. That corrected source is published here.

Public tests extract definitions without importing or running production. The AST contract checks 60 preserved functions. No private response bodies, token-level outcomes or secrets are included. Full publication checks are recorded in [PUBLICATION_VALIDATION_20261016.json](../PUBLICATION_VALIDATION_20261016.json).

## Remaining acceptance

Catch-up effectiveness and real outage/recovery delivery need forward evidence. The trade feed had partial data quality in the retained postflight. Complete discovery, predictive accuracy and realized profit are not established. Frozen study gates, notification mutes and trading configuration remain unchanged.

## Repository handover

This publication organizes source; it is not a new deployment. The server retains the deployment archive. The stack repository retains a redirect, and historical commits remain available. The earlier root overview is preserved in [history](../history/README_THROUGH_20261011.md), with relative links adjusted. No frozen research artifact was moved or rewritten.

## Public-layout release check

735 tests passed across 23 isolated suites using Python 3.12. Two existing AST fixtures now supply the math/re imports required by the current scanner; their assertions are unchanged. The local environment denied Unix sockets, and the first server run encountered the archive's real storage guard. The successful run used isolated temporary storage without weakening that guard. Two existing stale manifest entries were refreshed without altering their historical files.
