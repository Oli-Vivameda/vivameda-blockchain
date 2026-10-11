# Coin classification policy v1

Prepared 11 October 2026. Fourteen engineering-server tests passed. Full instructions: AGENT_RULES.md. The operational validator requires current authoritative evidence and a separately produced review; it does not fetch prices, make investment predictions, send Telegram messages or persist delivery history.

Labels: DISCOVERY, EARLY_WATCH, PROMISING_SETUP, FIRE_REVIEWED, AVOID. Only a separately evidenced FIRE_REVIEWED transition can be fire-message eligible. A negative short-term return, missing higher lows, or incomplete background research is not an automatic veto. Explicit current screening rejects block promotion. Evidence gaps and missing core checks remain WATCH. No numerical prediction threshold was learned or activated.

Sources: the recovered chart study in ../../learning/chart-audit-20261011/RECOVERED_CHART_STUDY_20261011.md. Private historical identities and price traces are excluded from this rules bundle. The 97 protected alert events remain excluded from the study.

## Activation

The connection writes the engineering checkout and cannot write the production Crypto Lab application. This owner command loads the rules into the existing dedicated agent's SYSTEM instructions and places classification.py beside it:

~~~sh
ssh -i ~/.ssh/vivameda_chatgpt_ed25519 -o IdentitiesOnly=yes root@77.42.42.75 'python3 /var/lib/vivameda-engineering/repo/client_learning/crypto_coin_classification_20261011/install_agent_rules.py --install --expected-sha256 8bdfaff77426b1f4ee33a36702f8ad0361c6fe4a379df6bc643252a55eee388e'
~~~

The installer verifies the known agent hash, backs up its source, preserves existing safeguards, copies only the reviewed instructions/validator, and checks the resulting SYSTEM text and file hashes. Fresh agent processes load the new instructions. It does not restart services, read outcomes, change scanner or frozen paper policies, train weights, or change the separate fire relay. Crypto rules can display the new SYSTEM text after activation. If the live agent source differs from the reviewed version, the installer refuses the patch.

## Integration boundary

Loading instructions is not complete bot integration. The current factual evidence guard and existing command/tool dispatch remain intact. The caller must collect authoritative current observations and screening, resolve ordinary historical comparators without protected outcomes, produce a separately audited review, and call classify(). Persist original decision evidence and actual decision time. The dispatcher must recheck current screening, track delivery atomically, and send only eligible transitions; it must not accept a model's unsupported PASS or fabricated facts as authoritative input. No free-text coin classification, review producer or relay wiring is enabled by the instruction installer alone.

The fire classification denotes speculative research priority and has no validated 100x probability. Owner installation confirmed on 11 October 2026. Fresh agent processes load the instructions; classifier dispatch and Telegram relay integration remain disabled.

Bundle SHA-256: 8bdfaff77426b1f4ee33a36702f8ad0361c6fe4a379df6bc643252a55eee388e

## Owner installation receipt — 11 October 2026

The hash-bound installation receipt confirms installed=true, fresh_agent_processes_load_instructions=true, policy=crypto-coin-classification-v1, classifier_dispatch_integration_enabled=false, telegram_relay_changed=false, scanner_changed=false, paper_policy_changed=false, weights_updated=false and live_execution=false. Installed agent source SHA-256: 68f7891f089a35c25e284c78d2ca7475b888d21c24ab1afb3cf3b3e98d9c1cec. This is instruction loading and validator installation; no independent review producer or fire-selection integration is claimed.
