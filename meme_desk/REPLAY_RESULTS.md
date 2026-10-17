# Meme desk v1 replay results

Status: BLOCKED — owner-run read-only export not yet supplied. No historical replay
has been computed. Preregistration commit: 376c3fed540e89aeee8d8d26c2ce18636c409acf.

| Plan | Half target / stop / time | Cases | Unresolved | Win rate | Average win/loss | Largest loss | Mean net per $10 | Excluding best 5 |
|---|---|---|---|---|---|---|---|---|
| A | +40% / -25% / 45 min | Not measured | Not measured | N/A | N/A | N/A | N/A | N/A |
| B | +25% / -20% / 30 min | Not measured | Not measured | N/A | N/A | N/A | N/A | N/A |
| C | +100% / -35% / 120 min | Not measured | Not measured | N/A | N/A | N/A | N/A | N/A |

Regime, score-band and chronological-half results are also not measured. The replay
engine produces these aggregate cells after a valid export; it never substitutes
fixture values. Private case rows stay on the server.

The engineering account cannot read the scanner database. Permissions were not
changed. The existing snapshot schema contains price/cap/liquidity but no reserves.
The owner exporter optionally accepts authenticated contemporaneous reserve captures;
without them eligible cases will be unresolved. Current reserves cannot backfill
history, and displayed liquidity cannot authenticate constant-product price impact.

These will be snapshot replays, not real fills. Human delay, coarse observations,
missing intraminute excursions, reserve coverage, fixed fee assumptions and existing
retrospective features limit interpretation. No positive result is assumed; a
negative result or zero resolved cases is valid. No frozen results/probabilities are
required or permitted. No conclusion about profitability can yet be drawn.
