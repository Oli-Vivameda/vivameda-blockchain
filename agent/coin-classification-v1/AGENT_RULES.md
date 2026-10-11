# Vivameda small-cap coin classification rules v1

Use these instructions to classify research candidates. This is a judgment policy informed by retrospective cases, not a validated prediction model. No live trading is authorized.

## Labels

| Classification | Meaning | Notification |
|---|---|---|
| DISCOVERY | Scanner surfaced a token; its setup has not been assessed. | Existing scanner message only. |
| EARLY_WATCH | Evidence is incomplete, stale, conflicting, or the setup is still developing. | Research state; no fire message. |
| PROMISING_SETUP | A fresh chart has a defensible setup, with risks and missing confirmation stated. | Research state; no automatic fire message. |
| FIRE_REVIEWED | A separate evidence-based review selects it as a speculative research priority. | Start the candidate message with 🔥. |
| AVOID | Current explicit screening rejection or evidenced thesis failure. | State the concrete reason; never infer fraud from UNKNOWN. |

FIRE_REVIEWED means research priority, not a buy recommendation, verified 100x probability, guaranteed runner or complete safety screening.

## How to judge

1. Establish the exact mint, chain and pool. Use fresh saved price observations, not a symbol match or a provider's global ATH. Compare a consistent ten-minute pre-decision window. Describe the observed range, pullback depth, location within the range and sequence of movements. State gaps and missing candles. Never reconstruct intraminute OHLC from minute samples.
2. Identify the setup: a developing base, a pullback with evidence of support, a reclaim, or continuation with evidence of participation. Name what supports that interpretation. A declining last price, missing higher lows, or a wide range alone is not a veto. A sharp move alone is not confirmation.
3. Treat narrow ranges and higher recorded buying shares as supporting observations. Do not hard-code the winner medians as admission thresholds. The post-hoc range <=20% plus buy-share >=70% screen had 6 held-gain cases and 9 half-loss cases out of 16. Buying counts do not prove unique organic buyers. Compare pressure, activity and liquidity across time rather than citing one headline volume number.
4. Separate the chart thesis from project claims. Explain why demand or participation might persist, cite what was actually observed, and label claims and unknowns. No public evidence or unverifiable catalyst is missing evidence, not evidence of legitimacy or fraud. A volume-generation or fee/buyback narrative does not establish sustainable demand.
5. Check current token controls, liquidity control and selling mechanics. Fresh explicit REJECT means AVOID. Core checks not supplied or not fresh mean EARLY_WATCH. Background developer history, wallet age or cluster evidence may remain UNKNOWN; display those risks rather than requiring every background field to PASS.
6. Compare with both historical winners and failures. Prefer the same regime, horizon, similar cap/liquidity and comparable chart windows. Include at least one historical failure pattern when promoting to FIRE_REVIEWED, or disclose that no comparable case is available and retain PROMISING_SETUP. Do not cherry-pick the most similar winner, conflate different mints with the same ticker, or inspect protected evaluation outcomes.
7. Write a specific invalidation condition: which observed price structure, selling behavior, liquidity change or factual development would contradict the thesis? A vague 'risky coin' disclaimer is not an invalidation rule. Thresholds used as trade risk limits must be identified as proposed risk limits, not learned optimal cutoffs.

## Fire promotion and duplicates

Never produce FIRE_REVIEWED just because the scanner called it a potential runner, the core screen passed, its cap is small, it has a narrow range, volume is high, or a timer elapsed.

A fire promotion requires a separate review tied to the exact evidence version and policy version, a fresh chart, core screening, a supported thesis, a documented failure comparison, and an invalidation condition. The review must use at least one observation newer than the original alert. This is a workflow distinction, not a learned delay or price threshold.

Only send on an actual transition into FIRE_REVIEWED. An already delivered fire candidate must not be sent again merely because a classifier, model or timer reran. A later reassessment must show a material evidence change and be labelled an update. The dispatch layer must persist delivery history and recheck latest screening; this rules module does not send messages or create that delivery ledger.

## Output for each assessed coin

- Mint and pool; observation and decision times; policy version.
- Classification and chart setup.
- What supports it: dated facts and evidence references.
- Why this classification now: the separate review decision, not scanner wording.
- Relevant historical success and failure examples; sample counts and limitations.
- What could go wrong; specific invalidation condition.
- Unknowns: distinguish unsupported claims, missing research and explicit rejection.
- Evidence coverage: partial or assessed. Never invent a calibrated probability or predictive confidence score.

## Learn from subsequent outcomes

Keep the original classification, evidence snapshot, policy version and decision time immutable. Record later reassessments separately. Preserve price histories before rolling cleanup removes them.

Evaluate both the original alert time and actual promotion time separately; never give a later decision the earlier entry price. Separate sustained gain, spike followed by collapse, loss before the rally and unresolved/missing outcome. Use fixed 1h/3h/6h/24h outcomes and first observed target-versus-loss order where coverage permits. Keep maximum excursion separate from the endpoint. Recorded market-cap multiples are not price returns, fills, exits or realized profit.

Daily evidence can update case memory and produce hypotheses. Changes to classification rules must be versioned and compared prospectively. Do not quietly fit weights or move production scanner thresholds. Keep the protected evaluation cohort excluded until its protocol permits review.

## Evidence behind these instructions

The retrospective study reviewed 139 retained first-call tokens, recovered usable ten-minute price histories for 132, and matched 74 to complete 24-hour observed outcomes. Those 74 include 8 held-gain cases, 18 spikes followed by collapse, 42 half-loss cases without 2x and 6 intermediate outcomes. Only two of seven matched winners had a narrower range than the matched loser; five had a higher recorded buying share. Two sustained winners had a negative last-ten-minute price change and four did not show the defined higher-lows pattern. These are descriptive findings, not a validated 100x model.

## Activation boundary

Engineering preparation does not establish production activation. The owner install receipt is authoritative for agent instruction loading. The validator is available for agent and dispatcher integration; loading these instructions does not itself connect the fire relay to independent reviews. Historical policy versions, paper rules and scanner thresholds remain unchanged.
