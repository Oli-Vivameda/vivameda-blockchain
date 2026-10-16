# Isolated Solana copy paper experiment

This is a separate, standard-library-only Python 3.12 project. It has no signer,
private-key handling, swap submission, Telegram integration or live-money mode.
Source wallets are the only signal. Existing Vivameda agents are not imported or
restarted. Public source belongs in `Oli-Vivameda/vivameda-blockchain/copy_trading`.

The frozen initial watchlist is EMPTY: **WAITING_FOR_VERIFIED_WALLETS**.
Named handles are research leads, not verified wallet identities. See watchlist.json
for exclusions, selection criteria and attribution research links. An alternative
Ansem lead was rejected because the attributed wallet was reportedly denied. No
claimed social performance is used as evidence. Primary full-address attribution,
actual purchase history and delayed-copy suitability must be reviewed before a new
watchlist version. Keep this empty baseline; never silently remove losing wallets.

A has $250 cash, $25 all-in buy/token cost cap, $75 aggregate open-cost cap, three
unique tokens maximum, no repeat buys, 30-second signal freshness, 5% maximum chase,
2-second minimum detection-to-quote delay, 1% quote slippage floor and a $0.10 external
network/priority/rent allowance per side. That allowance is an explicit assumption,
not a measured network cost; embedded AMM/platform fees are already in quote output
and are not deducted again. USDC is assumed $1; depeg risk is not modeled. Position
liquidation uses size-specific net sell quotes; missing/stale marks are zero after
5 seconds. At 10% equity drawdown from the recorded peak, entries pause durably.
Exits continue. The pause cannot clear itself and the bankroll cannot reset on restart.

A exits proportionally to source pre-sale inventory, rounded down to raw token
units. Missing inventory evidence skips. Failed exits remain held and visible and
are retried without repeatedly applying the fraction. A later source sale supersedes
a failed exit intent. This conservatively avoids over-selling but may under-exit;
it is logged and should be reviewed. B has an independent $250 ledger but is disabled.
Enabling B requires a new frozen configuration with positive take_profit, stop_loss,
max_hold_s and frozen_at. It uses the same source entry eligibility, its own portfolio
caps, and full TP/SL/time exits. Portfolio paths and available capital can then diverge.

## Feed, parsing and execution limits

The default public Solana RPC is read-only, confirmed-commitment polling every
5 seconds, with up to 60-second outage backoff. A one-minute getHealth probe runs
even while the watchlist is empty; it is not evidence of wallet-event monitoring.
First startup seeds the latest signature without replay. Pagination, pending tx,
first detection, slot, block time, confirmation and cursors are persisted. A missing
cursor in available provider history blocks that wallet and records a gap. Catchup
transactions still face the 30-second age rule. Recovery can miss opportunities;
it must not manufacture fills. RPC limits may make the freshness target infeasible.
The report exposes observed latency; it does not claim the target is met in advance.

The parser supports one Jupiter route against USDC or SOL, nets routed intermediate
balances, uses integer token quantities and accounts for wrapped SOL and rent across
owner token-account lamports. It requires wallet fee-payer/signature and recognized
swap instruction evidence. It rejects failed tx, outer transfers/airdrops, Token-2022,
multiple economic assets, unsupported instructions or ambiguous considerations.
Direct Pump/Raydium swaps and other unsupported protocols are logged, not inferred.
A transfer inside a complex unsupported transaction is not assumed to be a purchase.
This deliberate coverage limit prevents treating every balance increase as a trade.

A quote is only a paper estimate, never a confirmed fill. No indicative-price fills
are admitted. `quote_url` is unset and authorized-free access is false by default.
The optional adapter accepts an explicitly authorized public HTTPS Metis-compatible
GET quote endpoint; no key lookup, signup, paid fallback or transaction POST exists.
Jupiter's current documentation labels V1 deprecated and shows API-key access:
https://developers.jup.ag/docs/swap/v1/get-quote . Do not assume an unauthenticated
endpoint remains available. Obtain authorization and validate a usable free endpoint
before freezing a new config. Until then all eligible entries skip on missing quotes.
SOL source price comparison also requires a fresh SOL/USDC conversion quote.

Risk evidence uses read-only mint-account RPC plus the public RugCheck report.
Revoked mint/freeze authorities, classic Token program, no transfer restrictions,
and no current provider scam alerts are blocking checks: unknown blocks. A sell
route and impact <=5% are also required through quotes. Concentration, bundling,
linked wallets and creator history are preserved as informational evidence; missing
coverage stays unknown. Bundling is not a fraud verdict. No browser runs in the loop.
Provider alerts are not a safety guarantee and no completeness claim is made.

## Verify and run without installation

```sh
python3 -m unittest discover -s copy_trading/tests -v
python3 copy_trading/verify.py
python3 copy_trading/service.py once --state-dir /tmp/copy-paper-smoke
python3 copy_trading/service.py report --state-dir /tmp/copy-paper-smoke
```

Synthetic fixtures use separate temporary databases. Never reuse them for forward
results. Every state database binds canonical config/watchlist hashes. Changing
those files requires a new experiment database, explicitly documented alongside the
old one; this release deliberately refuses an automatic bankroll/config migration.
Historical replay is not a daemon mode. Original frozen manifests remain in git.

## Dedicated persistent service

`install.py` is an **owner-run** installer for `vivameda-copy-paper.service` only.
It verifies exact release hashes, creates a dedicated unprivileged user, copies an
immutable release under `/opt/vivameda-copy-paper/<release-hash>`, runs offline tests
as that user, and starts a hardened systemd unit. State belongs exclusively in
`/var/lib/vivameda-copy-paper/paper.sqlite3`. It refuses existing installations and
will not overwrite state/config. An interrupted installation needs explicit review.
No existing scanner, wallet, social, Telegram or Polymarket unit is changed.

The engineering connector runs as a non-root user with no user service manager or
lingering session. It cannot install this new system service through its available
scoped deploy tools. Do not use deploy_crypto: that deploys/restarts other services.
The exact owner command is provided with the reviewed release receipt, including an
installer-byte hash check before executing it. Run through `ssh vivameda-server`.
Source publication and a successful engineering smoke run are not deployment.

After owner installation:

```sh
ssh vivameda-server 'systemctl status vivameda-copy-paper.service --no-pager'
ssh vivameda-server 'journalctl -u vivameda-copy-paper.service -n 30 --no-pager'
ssh vivameda-server 'sudo -u vivameda-copy-paper python3 -B /opt/vivameda-copy-paper/current/service.py report --state-dir /var/lib/vivameda-copy-paper'
ssh vivameda-server 'sudo -u vivameda-copy-paper python3 -B /opt/vivameda-copy-paper/current/service.py pause --state-dir /var/lib/vivameda-copy-paper'
ssh vivameda-server 'sudo systemctl stop vivameda-copy-paper.service'
```

Reports expose wallet/strategy cash, realized and conservative unrealized value,
net returns, peak/current/max drawdown, cost exposure, closed-position-cycle win/loss statistics,
external costs, skips, stale positions and health. Small samples are labelled.
Exit-leg counts are reported separately from fully closed position cycles. Per-wallet return and drawdown contributions use the full $250 strategy bankroll as a fixed denominator; wallets do not have independent cash allocations. Equity and drawdown are sampled each monitoring cycle. Source activity counts and
consideration/quantities are retained, but initial source holdings and unsupported
transactions are unknown: source total ROI and source-vs-follower excess return
cannot be inferred from this coverage. Inspect events/decisions/fills/observations
in a read-only SQLite connection for detailed audit; never edit balances directly.
State databases and provider reports are private runtime data and excluded from git.
