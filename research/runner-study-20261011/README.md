# Runner research and provisional agent knowledge — 11 October 2026

Owner request: study the biggest 100 runners over 24 months, their early setups, audience, behavior and breakout explanations; create agent knowledge.

**Not complete.** Historical archive coverage blocks the requested ranking and chart replay. Completed: source/access audit, eleven preliminary case cards, a provisional agent knowledge pack, a study protocol, and a temporal-evidence/completion validator. Verified ranked runners: **0/100**. Audited early chart setups: **0**. Do not describe this as a 100-chart learning result.

Files: `AGENT_KNOWLEDGE.md`, `PROTOCOL.md`, `sources.json`, `cases.json`, `validate.py`, `test_validate.py`, `STATUS.json`. No raw proprietary data, credentials, protected pilot outcomes or licensed datasets are published.

The case cards document actual exchange events and qualitative retrospective accounts. They do not supply missing early prices or prove causal returns. Official events show why launch-time and later-listing hypotheses must be separated. Investigator reports show why audience fame and liquidity/distribution safety need separate assessment. Agent knowledge describes how to evaluate those distinctions without becoming needlessly strict or inventing conviction.

The full study requires a timestamped archive covering dead as well as surviving pools, contemporaneous social evidence and matched failures. The current chart connector does not expose the needed per-point times; free on-chain history does not reach the complete window. No paid service is enabled. MELT is a possible academic research reference, not licensed commercial agent data.

The knowledge pack is committed research for the agent, **not loaded into the production review prompt**. Its rules are provisional; no weight update, production eligibility change, Telegram send, collector restart or relay resumption occurs. The original automatic 100x relay remains paused per owner STOP-command receipt; the separately reviewed third trigger remains installed.

Validator usage: `python3 validate.py --status STATUS.json`. It prints the honest evidence counts and blockers, exits 0 for a valid incomplete research status, and rejects an unsupported complete=true claim. Tests exercise late evidence exclusion, unverified knowledge times, identity binding, duplicate-ranked identities, return provenance and false-completion rejection. This validator does not constitute model or trading validation.
