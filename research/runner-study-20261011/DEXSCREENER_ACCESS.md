# DEX Screener historical access pilot — 11 October 2026

The owner requested DEX Screener as the source for the full runner study. Direct browser inspection confirmed that the GOAT/SOL Raydium chart reaches October 2024 at weekly, daily and hourly resolution. The hourly view loaded 11–13 October 2024 using the chart's Go to date/time control. Loading can take tens of seconds; the unchanged latest-date view before loading finishes must not be mistaken for unavailable history.

This corrects the earlier blanket archive-access blocker: historical **visual chart access is available for this pair**. It does not establish a complete dataset or rank the biggest 100 runners.

Sources: [verified pair](https://dexscreener.com/solana/9tb2ohu5p16bpbarqd3n27wnkf51ukfs8z1gzzldxvzw), [official API reference](https://docs.dexscreener.com/api/reference), [official data-source FAQ](https://docs.dexscreener.com/). The documented API lists current pair/search/token/profile/meta endpoints, with no historical OHLCV endpoint identified. The tested chart context menu did not offer CSV export. No undocumented endpoint, browser-internal data or fabricated candles were used.

## Evidence boundary

One access pilot, zero machine-readable candles, zero verified ranked runners. Historical $10k–$20k crossing, dead-pool coverage and contemporaneous audience metrics remain unverified. The present sidebar and floating latest-price line are current, even while the chart displays October 2024. The OHLC legend can also remain on the latest candle unless a historical candle is selected. Do not copy these as launch-time evidence.

## Visual-review method

Bind each case to its mint and pool; distinguish original launch/bonding-curve data from subsequent pools. Confirm dates and resolutions visibly. Save one view ending at the decision time and a separate subsequent outcome view. Describe consolidation, failed breaks, pullbacks and volume behavior as observations, not numerical optimized rules. Match failures from the same launch period and comparable cap/liquidity stage; fame or a rising historical chart alone cannot promote FIRE_REVIEWED. If the first $10k–$20k stage is missing, use the case only for the later stage actually visible.

A selected 100-case visual study can be useful, but must be labelled selected cases unless a complete historical universe and ranking are recovered. A comprehensive greatest-return ranking and quantitative early-signal evaluation remain unfinished. No selection-quality or trained-weight claim follows from this access pilot.

## Installed knowledge receipt

The owner supplied a successful activation receipt for bundle 5e5c860c39c18d9dfddcb652e0c592194409cfc878d4daf33e4669e55f5af49c: installed=true, both prompt consumers integrated, 25 tests passed, no relay resumption, no scanner change, no trading, no weight update. Backup: /opt/vivameda-operations/runner-knowledge-2shknagu. This is owner-reported installation evidence; it does not make the full study complete. The original STATUS.json inside the pinned bundle is a preparation snapshot and is deliberately preserved to keep its checksum valid.
