# Crypto repository maintenance

This is the canonical public home of Vivameda's Crypto Lab. Read docs/REPOSITORY_MAP.md and docs/REPOSITORY_POLICY.md.

- Keep one current scanner at scout/early_scout.py; keep tests beside their component.
- Put dated release evidence in docs/releases and preserve frozen research populations, protocols and source snapshots.
- Keep company/workforce work in vivameda-intelligence-stack, with crypto cross-references pointing here.
- Exclude credentials, keys, tokens, raw runtime evidence, messages and production databases.
- Refresh MANIFEST.json and run scripts/verify_release.py using Python 3.12.
- Never regenerate scientific protocol hashes to make a check pass.
- Distinguish publication, deployment and prospective validation. Publication does not authorize trading.
- Avoid duplicate full operational baselines/candidates across repositories.

Public operator commands must use the host alias `ssh vivameda-server`. Never publish the server address, SSH login identity or private-key filename in public documentation.
