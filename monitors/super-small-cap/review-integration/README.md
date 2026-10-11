# Super-small-cap review-to-alert integration

11 October 2026. Owner activation completed with the corrected bundle; reviewed delivery enabled. The existing collector is installed and continues SHADOW capture. This separate review worker connects discovery, exact-pair chart evidence, supported screening, local-agent classification and reviewed-only Telegram delivery. It does not change the scanner, $100k–$500k relay, collector or interactive agent source.

## Behavior

- One due candidate per bounded invocation; independent timer runs 60 seconds after the previous invocation ends. A candidate is retried no more often than every five minutes. Recent 200 entries form the bounded queue; discovery and capture remain partial.
- Uses saved 60–180 second price observations, their receipt times, reported liquidity and rolling five-minute counts. Counts are explicitly not independent organic buyers or fresh-window net flow. Missing/gapped chart data remains EARLY_WATCH.
- Reuses fresh exact-pair prealert screening or runs the pinned existing free Pump AMM screener in its own store. At most two identity RPC requests plus 24 screening RPC requests per collection; fixed public endpoints, no API key. Unsupported bonding curves remain EARLY_WATCH. Background unknowns are disclosed; fresh core PASS is required for FIRE_REVIEWED.
- Reads the installed Crypto Lab model and trigger instructions without executing or modifying the interactive agent. Local Ollama receives a constrained JSON schema; the model selects a setup hypothesis, label and evidence references. The worker builds factual sentences from captured evidence. A valid JSON response is not proof of selection quality.
- Supplies both prior held-gain and failure cases from this collector's completed prospective one-hour samples when available. Requires uninterrupted sampling, an endpoint at most 180 seconds late and comparable reported liquidity (within a factor of two). This provisional comparison rule is not fitted or validated. Only mint identities are read from pl_predictions for exclusion; protected outcomes/probabilities are never read. Earlier larger-cap study findings are labelled non-comparable. Missing comparable cases caps classification at PROMISING_SETUP.
- Saves immutable assessments, evidence hashes, observation prices/times and a separate delivery ledger. Rechecks latest screening, observation freshness and current market-cap band after inference. Only validated FIRE_REVIEWED can send a separate message through the same existing bot/chat, starting with **🔥 SUPER SMALL CAP — EXPERIMENTAL**. Ordinary discovery does not send. Ambiguous attempts are retained as delivery_unknown and never automatically resent.

No end date, paid feed, trading, model-weight update or automatic threshold promotion. The original two triggers' delivery behavior is unchanged. This is an experimental research stream, not a validated runner detector. The worker can correctly produce no alerts while core screening or comparable cases are missing.

## Verification

35 tests passed locally and on server Python 3.12 (0.634 seconds). Installer validation passed with the exact bundle hash; both systemd units verified. Production activation completed; the first real review timed out and did not send. Tests cover discovery versus reviewed promotion, exact identity, missing comparators, screening UNKNOWN/REJECT, unsupported review facts, stale/changed evidence, current band, stop markers, Telegram-disabled mode, persistent duplicate suppression, ambiguous delivery, protected-mint exclusion, query budgets across inference waits, and both full synthetic workflow branches with a simulated sender.

Actual installed local model schema probe: owner activation: initial 48.692 seconds, warm 7.603 seconds; PROMISING_SETUP on synthetic incomplete-comparator evidence. No Telegram messages sent. This verifies the model interface and that example's safe classification, not real-world chart judgment or profitability. An earlier longer response format exceeded the 25-second timeout; the final compact schema resolved the probe. Runtime inference retains a 25-second limit, and stale reviews cannot send.

## Owner activation

The connected engineering tool runs as vivameda-engineer and cannot install root-owned systemd units. The activation script checks the exact reviewed bundle, installed agent hash, pinned screening helper hashes, service-user access and the local model schema. It copies screening helpers into its own runtime; it never edits their source or queues. It starts a first real review with Telegram disabled, verifies protected source/unit hashes, then enables reviewed delivery and only its own timer. If activation fails, it disables its review timer and delivery while preserving evidence and the existing collector. Re-running a completed installation verifies the reviewed source and timer rather than reinstalling.

Reviewed bundle SHA-256: `b6a4d41071748ebd48fdf64fe43d1596bf8bfde7041b1ad64fdcd7e9d959521a`.

```sh
ssh -i ~/.ssh/vivameda_chatgpt_ed25519 -o IdentitiesOnly=yes root@77.42.42.75 'python3 /var/lib/vivameda-engineering/repo/client_learning/crypto_super_small_cap_review_20261011/install_review.py --install --expected-sha256 b6a4d41071748ebd48fdf64fe43d1596bf8bfde7041b1ad64fdcd7e9d959521a'
```

Runtime: /opt/vivameda-super-small-cap-review. State and private screening: /var/lib/vivameda-super-small-cap. Own units: vivameda-super-small-cap-review.service and .timer. REVIEW_STOP pauses review only; STOP pauses collector and review. review_config.json can disable Telegram while continuing assessments. Installation receipt confirmed. First genuine candidate delivery remains unverified. No synthetic candidate is sent during installation.

Ollama structured output reference: https://ollama.com/blog/structured-outputs . Mint-level evidence, live credentials and raw model responses remain private; only implementation source and aggregate validation are published.

## Interrupted activation repair — 11 October 2026

The first owner activation failed before delivery enablement: the installer’s private umask created its runtime directory with mode 700, preventing the service account from opening the probe script (Python exit 2). The directory mode was independently confirmed on the server. The corrected installer explicitly sets mode 755 on this code-only directory; private state and credentials remain restricted. It accepts the exact previous bundle only when delivery is disabled and every copied source matches its pinned previous hash, then retries the normal service-user probe and delivery-disabled postflight. Two regression tests cover restrictive-umask permissions and rejected migration from active or unknown bundles. Activation and first genuine delivery remain unverified.

## Activation result — 11 October 2026

Owner receipt: installed true, independent review producer true, Telegram delivery true, mode REVIEW_ALERT, deadline null, same existing bot/chat, existing trigger and interactive agent sources unchanged, live execution false, weights unchanged. Backup: `/opt/vivameda-operations/super-small-cap-review-c587oh1z`. First delivery-disabled run (1791741335) assessed one candidate as EARLY_WATCH after TimeoutError; delivery not eligible, zero messages. The synthetic schema probe passed, but that does not validate real selection. Both third-trigger timers independently showed active/waiting; the last review service exited 0. A oneshot review service is normally inactive between timer runs. The engineering account cannot read private latest-review state; recurring timeout status is not yet verified. No additional installation command is required.

