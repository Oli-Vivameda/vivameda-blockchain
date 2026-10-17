# Data-source check — 17 October 2026

Chosen: existing scanner launch/market data via owner-run read-only export, and
Solana public RPC. No protected source read by engineering; no permission changes.
Social URL resolution is a bounded public HTTPS check, not an additional trading API.

PumpPortal not selected. Its official real-time documentation labels creation and
migration streams free, but trade/account streams metered (0.01 SOL per 10,000 events)
and requiring an API key/funded linked wallet. Legal section 6 restricts copying or
distributing interface contents absent express authorization and grants a limited
personal license. This does not establish permission for this Telegram feed; no
PumpPortal connection is made and no key/account/payment is acquired.

Primary sources checked:
- https://pumpportal.fun/data-api/real-time/
- https://pumpportal.fun/legal/
- https://solana.com/docs/references/clusters
- https://github.com/pump-fun/pump-public-docs/blob/main/idl/pump.json

Solana documents public RPC access with rate limits and no production-availability
guarantee. Respect Retry-After/backoff; do not evade limits. The existing scanner's
NSFW exclusion, pagination/catchup and free RPC throughput limit coverage. 'Every
new token' is a coverage objective, not a demonstrated completeness claim. No paid
fallback is authorized. Facts not established from these sources remain UNKNOWN.
