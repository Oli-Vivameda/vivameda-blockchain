# Super-small-cap review-to-alert integration

11 October 2026. Implementation prepared and tested; owner activation pending. The existing collector is installed and continues SHADOW capture. This separate review worker connects discovery, exact-pair chart evidence, supported screening, local-agent classification and reviewed-only Telegram delivery. It does not change the scanner, $100k–$500k relay, collector or interactive agent source.

## Behavior

- One due candidate per bounded invocation; independent timer runs 60 seconds after the previous invocation ends. A candidate is retried no more often than every five minutes. Recent 200 entries form the bounded queue; discovery and capture remain partial.
- Uses saved 60–180 second price observations, their receipt times, reported liquidity and rolling five-minute counts. Counts are explicitly not independent organic buyers or fresh-window net flow. Missing/gapped chart data remains EARLY_WATCH.
- Reuses fresh exact-pair prealert screening or runs the pinned existing free Pump AMM screener in its own store. At most two identity RPC requests plus 24 screening RPC requests per collection; fixed public endpoints, no API key. Unsupported bonding curves remain EARLY_WATCH. Background unknowns are disclosed; fresh core PASS is required for FIRE_REVIEWED.
- Reads the installed Crypto Lab model and trigger instructions without executing or modifying the interactive agent. Local Ollama receives a constrained JSON schema; the model selects a setup hypothesis, label and evidence references. The worker builds factual sentences from captured evidence. A valid JSON response is not proof of selection quality.
- Supplies both prior held-gain and failure cases from this collector's completed prospective one-hour samples when available. Requires uninterrupted sampling, an endpoint at most 180 seconds late and comparable reported liquidity (within a factor of two). This provisional comparison rule is not fitted or validated. Only mint identities are read from pl_predictions for exclusion; protected outcomes/probabilities are never read. Earlier larger-cap study findings are labelled non-comparable. Missing comparable cases caps classification at PROMISING_SETUP.
- Saves immutable assessments, evidence hashes, observation prices/times and a separate delivery ledger. Rechecks latest screening, observation freshness and current market-cap band after inference. Only validated FIRE_REVIEWED can send a separate message through the same existing bot/chat, starting with **🔥 SUPER SMALL CAP — EXPERIMENTAL**. Ordinary discovery does not send. Ambiguous attempts are retained as delivery_unknown and never automatically resent.

No end date, paid feed, trading, model-weight update or automatic threshold promotion. The original two triggers' delivery behavior is unchanged. This is an experimental research stream, not a validated runner detector. The worker can correctly produce no alerts while core screening or comparable cases are missing.

## Verification

33 tests passed locally and on server Python 3.12 (0.537 seconds). Installer validation passed with the exact bundle hash; both systemd units verified. Production activation is pending. Tests cover discovery versus reviewed promotion, exact identity, missing comparators, screening UNKNOWN/REJECT, unsupported review facts, stale/changed evidence, current band, stop markers, Telegram-disabled mode, persistent duplicate suppression, ambiguous delivery, protected-mint exclusion, query budgets across inference waits, and both full synthetic workflow branches with a simulated sender.

Actual installed local model schema probe: initial 19.113 seconds, warm 8.768 seconds; PROMISING_SETUP on synthetic incomplete-comparator evidence. No Telegram messages sent. This verifies the model interface and that example's safe classification, not real-world chart judgment or profitability. An earlier longer response format exceeded the 25-second timeout; the final compact schema resolved the probe. Runtime inference retains a 25-second limit, and stale reviews cannot send.

## Owner activation

The connected engineering tool runs as vivameda-engineer and cannot install root-owned systemd units. The activation script checks the exact reviewed bundle, installed agent hash, pinned screening helper hashes, service-user access and the local model schema. It copies screening helpers into its own runtime; it never edits their source or queues. It starts a first real review with Telegram disabled, verifies protected source/unit hashes, then enables reviewed delivery and only its own timer. If activation fails, it disables its review timer and delivery while preserving evidence and the existing collector. Re-running a completed installation verifies the reviewed source and timer rather than reinstalling.

Reviewed bundle SHA-256: `5a43bb7cef70edb22ee8dc3709591f43f194eb225e3baecac918610740dae87f`.

```sh
ssh -i ~/.ssh/vivameda_chatgpt_ed25519 -o IdentitiesOnly=yes root@77.42.42.75 'python3 /var/lib/vivameda-engineering/repo/client_learning/crypto_super_small_cap_review_20261011/install_review.py --install --expected-sha256 5a43bb7cef70edb22ee8dc3709591f43f194eb225e3baecac918610740dae87f'
```

Runtime: /opt/vivameda-super-small-cap-review. State and private screening: /var/lib/vivameda-super-small-cap. Own units: vivameda-super-small-cap-review.service and .timer. REVIEW_STOP pauses review only; STOP pauses collector and review. review_config.json can disable Telegram while continuing assessments. Installation receipt and first genuine candidate delivery remain pending. No synthetic candidate is sent during installation.

Ollama structured output reference: https://ollama.com/blog/structured-outputs . Mint-level evidence, live credentials and raw model responses remain private; only implementation source and aggregate validation are published.
