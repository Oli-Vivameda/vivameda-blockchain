# Publication policy

Applies to Vivameda's public research repositories (vivameda-prediction-markets and vivameda-blockchain). Adopted 17 October 2026.

The goal is a verifiable public track record: methods, preregistrations, aggregate results and failures are public; anything that would expose people, accounts, licensed data or live trading signals is not.

## Public

- Source code, tests and installers for research services.
- Preregistered protocols, frozen rules and configuration, committed before results exist.
- Bundle and file hashes that pin what actually ran.
- Aggregate results: counts, hit rates, Brier scores, calibration, latency, uptime, costs.
- Failed candidates and negative results, with the reason they failed.
- Research notes explaining what was learned.

## Public after a delay

- Individual alerts and decisions (token, market, time, price) are published no earlier than 24 hours after the event. At event time only a SHA-256 hash of the full alert record is published, so anyone can later check that the revealed alert was fixed in advance. (Planned; not yet implemented for every lane.)
- Where a rule set should not be copied during a live test, its hash is committed at the start and the rules are revealed when the test ends. The early lane v1 rules are already public in full.
- Per-trade paper ledgers may be released after an evaluation period closes.

## Never public

- Private keys, seed phrases, API keys, tokens, passwords, environment files.
- Server IP addresses, hostnames, SSH users and key names.
- Trading wallet addresses and live positions. Known wallets get followed and front-run, and addresses link to identity.
- Raw runtime databases, provider responses and case-level rows that are not part of a scheduled release.
- Data from the Vivameda workforce panel, Coresignal, Clean or any other licensed source. These repositories must not contain or depend on that data.
- Client names, client work and personal data.

## Wording

Results are research findings, not investment advice or recommendations to buy or sell anything. Paper results, peak multiples and backtests are labelled as such and never presented as realized profit. No performance claim without the aggregate it rests on.

## Before every push

1. No secrets, addresses, hostnames or licensed data in the diff.
2. Runtime state, databases and logs stay excluded by .gitignore.
3. New results are aggregates, or delayed releases under the rules above.
4. Claims match the published numbers, including the unflattering ones.
