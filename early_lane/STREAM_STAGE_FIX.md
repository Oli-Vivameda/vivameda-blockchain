# Astra handover — activated-journal staging fix

1. Trigger: the previous stream staging bundle rejected an existing activation
   before release-directory creation. The operator traceback identified the
   initial-source-repair guard; it did not indicate journal corruption.
2. Cause: stream_stage.py imported upgrade.journal_state. That older operation
   intentionally requires an unactivated study. Its guard remains unchanged.
3. Fix: stream_stage.py now owns a read-only integrity snapshot suitable for
   staging an activated study. It returns existing counts, chain head and original
   activation, then requires identical snapshots before and after copying.
4. Integrity: mode=ro, PRAGMA query_only=ON, explicit read transaction, contiguous
   sequence numbers, previous-hash links and every event digest are verified.
   Missing or corrupt journals fail before creating a new release directory.
5. Runtime guards: the original process lock, service-state checks, root-controlled
   runtime path, old bundle verification, source hash checks and offline test gate
   remain. No systemd unit, delivery config, permission, rule or study-clock edits.
6. Tests: six regression tests exercise the real staging function with an isolated
   activated journal and cohort. They verify exact journal-byte preservation,
   repeat staging, corrupt-chain refusal, missing-journal refusal and detection
   of changes during copying. Service reads and test subprocesses are simulated;
   the journal reader and file-copy/bundle-verification paths run for real.
7. State paths: existing lane.sqlite3 and process.lock under the lane state
   directory. No reset, migration or permission change is needed. This fix changes
   no history collection, screening, alert selection or outcomes.
8. Reviewed bundle:
   e625f0b13233dd4e6ee2e20f6cdb95359e588c0414ba733a50477dd6cd7c2e38.
   stream_owner.py remains:
   d709d835078cfd33fd30ceb208fd1ce16fb119692e519b0b90530c4d077186cd.
   Source hashes are in STREAM_INTEGRATION_SHA256.json.
9. Status: source-only staging correction. No production installation or service
   start was performed by engineering. Previous public source and the installer
   failure are not successful owner rollout evidence.
10. Next: use the corrected hash-checked command in STREAM_INTEGRATION_COMMANDS.md.
    First confirm staged=true with the original activation preserved. Then use
    this new bundle for the bounded ten-minute shadow. Telegram stays disabled.
