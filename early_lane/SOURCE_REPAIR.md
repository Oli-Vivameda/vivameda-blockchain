# Source repair evidence — 17 October 2026

Initial installed runtime: d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442. Prepared replacement bundle: 41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d.
Replacement has NOT been applied by engineering; root owner action is required.
Original frozen rules commit 959cdebdea5107f48bcc03b16c3968b34dc24fbe and RULES SHA
ce4ec9f2af33afc637ac403755e3b1f567666c52cca6573c55af9b6eb994a463 remain unchanged.

## Actual failure and owner evidence

Owner reported missing-input cycles and 0 valid polls. Engineering job
b712bd7fe62e9e0ed6ababb35717dafd confirmed HTTP 403, Cloudflare 'Just a moment' HTML
from the public launch endpoint. No attempt to evade that challenge, use cookies,
rotate IPs or obtain API keys. Owner stopped only early-lane timer/rollout; job
24f35f69e75ad6f3a68a5d41ffef54a3 confirmed both inactive. Scanner and learning were
active with their original source hashes. Owner's approved query_only diagnostic
export reported 597 launches and 0 fresh market snapshots. It made no scanner writes.
This is NOT a genuine two-hour run and is NOT a valid zero-alert result.

## Permitted replacement path

Root exporter emits the retained launch identities without --refresh-launch-feed.
The separate worker derives exact Pump/standard PumpSwap PDAs, reads mint supply,
curve reserves or authenticated pool vaults and Pyth PriceUpdateV2 via public RPC.
The SOL/USD account owner, Anchor discriminator, full verification level, feed ID
and publish age <=60s are checked. Read context block time must be <=60s old.
Market cap = quote/base raw reserve ratio * CURRENT raw mint supply * SOL/USD /1e9.
Decimals cancel; current supply may be lower after burns, but cannot exceed curve's
initial supply. These are sampled spot marks, not executable prices or trade profit.

A block-time mark keeps its real slot timestamp: the older oracle timestamp is NOT
assigned retroactively to the current curve price. Expiry is set by the oldest
component so a long screening refresh cannot pass a now-stale quote. Standard SOL
curves and non-boost SOL PumpSwap pools only; unsupported quote/layout stays UNKNOWN.
Pool quote liquidity zero can provide positive missing-liquidity evidence if both
vault identities are authenticated; undefined empty-base prices remain unknown.

One <=30-token RPC pricing batch per poll competes fairly across exported launches
and tracked cohorts, with due outcome checkpoints prioritized. Cached marks keep
original timestamps and expiry. Existing 12-call cycle budget and one call/sec remain;
large universes may have low coverage. Full history and holder census are still
mandatory. JSON-RPC embedded throttles receive persisted backoff as HTTP throttles do.
Missing prices cannot activate the observation clock or pass the rollout gate.

## Live checks and their limits

Public RPC account/census capability job bd1c2dd5266d14ebd1fd5b3e2fd6cf3d passed
getAccountInfo and an empty filtered getProgramAccounts request. This proves method
availability, not complete large-token census throughput. On-chain Pyth read job
3562032d5771cbc563ee71353d003cea returned the documented receiver owner and 134-byte
PriceUpdateV2 account. Live mint layout checks confirmed derived Pump/PumpSwap
accounts exist; one older token had burns/unsupported boost layout. A recent v3
trade probe returned a non-SOL curve and correctly remained UNKNOWN. No sampled
eligible full-screened token, live alert or outcome is claimed. Some getTransaction
probes returned transient JSON-RPC errors; throttles now back off.

Owner upgrade therefore performs its own LIVE pricing preflight on up to 30 current
owner-exported mints and ABORTS without modifying units if no authenticated mark
exists. Even a successful pricing preflight is NOT a full safety/screening pass.
No activation/journal reset or automatic service start. Original bundle and exact
unit definitions are verified, jobs must be inactive, process lock held, journal
chain verified with no previous observational activation/cohort. Existing state,
config, user and old source are preserved; unit definitions backed up and restored
on write/reload failure. New source is a separate root-owned hash directory.

## Primary references

- https://github.com/pump-fun/pump-public-docs/tree/639b87fb45c3adeffa6f7c4a1bf0cb85e392bf22
- https://docs.pyth.network/price-feeds/core/push-feeds/solana
- https://docs.pyth.network/price-feeds/core/contract-addresses/solana
- https://github.com/pyth-network/pyth-crosschain/blob/main/target_chains/solana/pyth_solana_receiver_sdk/src/price_update.rs

Pyth's sponsored on-chain push account is read through the already permitted public
Solana RPC. No Hermes/API account, signature, write transaction or provider bill.
Oracle account 7UVimffxr9ow1uXYxsr4LHAcV58mLzhmwaeKvJ1pjLiE;
receiver rec5EKMGg6MxZYaMdyBfgwp4d5rB9T1VQH5pJv5LtFJ;
feed ef0d8b6fda2ceba41da15d4095d1da392a0d2f8ed0c6c7bc0f4cfac8c280b56d.

## Next evidence

Apply OWNER_COMMANDS' reviewed repair, inspect preflight/upgrade receipt, then start
a NEW 7200s log-only run using the preserved state. Inspect fresh feed/priced poll
counts and coverage before treating it as observation. No Telegram until the new
channel and compatible existing authenticated sender are confirmed. The 14-day
review date stays unbooked until first genuinely fresh observational input; do not
count the failed missing-input wait. Peak multiples remain sampled, not profit.
