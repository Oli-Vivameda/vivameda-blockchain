# Astra handover — meme desk v1, 17 October 2026

1. Scope and invariants. Steps 1–2 only: human-in-the-loop Solana desk. No signing,
   wallet connection, keys, signup, swaps, paid calls or direct Telegram API client.
   No scanner/scoring/policy/monitor/study/journal/service changes or protected DB
   permission changes. Phantom public address TBD; ticket destination TBD.
2. Preregistration. Commit 376c3fed540e89aeee8d8d26c2ce18636c409acf preceded replay
   code/tests. Protocol SHA-256 62c4b3e4b13dbc97a3c973cf22b9fb40eb78a2e006c315e20abd8df92b5195a2.
   The exact protocol remains unchanged. Three mandatory scanner checks, no explicit
   REJECT; fresh evidence; earliest ALERT; frozen membership excluded before export.
3. Files and release. Public source meme_desk/, server staging
   /var/lib/vivameda-engineering/repo/client_learning/meme_desk_v1_20261017/.
   BUNDLE.json pins all 15 code/test/config/protocol/README files. BUNDLE SHA-256:
   d0f25ec5398fe230f7eecf2cfa84589a8919a9f79875dd1ebd2ac0f209a9ef84. owner.py SHA-256:
   16871a05d86130e1bdee4a5dd5f1e60f4696298b9540fa4f2d4570c1da9b1d3c. All published files, including this handover and results placeholder,
   are additionally covered by the repository MANIFEST.json. No private case data
   is published. The handover/results are evidence documents, outside runtime bundle.
4. Export boundary. exporter.py alone opens scanner data with mode=ro/query_only,
   bounded consistent transaction and table/column authorizer. pl_predictions mint
   membership only; pl_results/probabilities/outcomes denied. No engineering direct
   DB attempt. owner.py snapshots verified bytes before project imports. The owner
   must run the reviewed exporter; output contains development replay rows only.
5. Replay status. BLOCKED; NO historical results measured. A/B/C all N/A, including
   regime/score/time splits and best-five exclusion. Existing snapshots lack reserve
   columns. Optional authenticated raw RPC capture archive is required to resolve
   entry/exit impact. No current-reserve backfill or displayed-liquidity proxy.
   Snapshot-only replay, fixed cost assumptions, no real-fill/profitability claim.
6. Ticket implementation. $10, +3% entry ceiling; plan A half +40%, stop -25%,
   45-minute UTC clock exit. Authenticated impact/cost, liquidity min $25k (smaller
   displayed vs authenticated reserve value), no tickets >6% all-in conservative
   split-exit round trip or >=3 TAKEN/open. Daily negative closes $15: REVIEW ONLY;
   lifetime negative closes $25: halt until explicit owner reenable. Manual marks
   and PnL are owner attestations, not verified fills. No price tracking/reconciliation.
7. Validation. 53 scoped tests passed locally; server validation receipts are
   identified below. Covers SQL leakage denial, immutable protocol, delayed replay,
   first-snapshot fills/gaps/reserves, A/B/C splits, append-only chain, duplicate and
   restart handling, liquidity/cost/position/loss rules, fixed skip reasons, owner
   callbacks, memory-only rate-limited delivery, reviewed source snapshot and nonroot
   install refusal. TESTING.md contains two clearly SYNTHETIC rendered examples.
   No test sends a message or accesses a real scanner DB/provider.
8. Shadow/service status. NOT INSTALLED/RUNNING. Startup smoke: 0 tickets,
   0 valid export polls, WAITING_FOR_OWNER_EXPORT. A real 60-minute dry run is
   BLOCKED and has NOT been performed; this is not a zero-opportunity finding.
   Do not relabel an hour of waiting as a valid pass. Existing services untouched.
9. Deployment/transport. Owner installer creates only vivameda-meme-desk.service
   plus its dedicated read-only export service/timer; own user/state/inbox. Root-owned
   immutable release /opt/vivameda-meme-desk/<bundle>, current symlink; state
   /var/lib/vivameda-meme-desk/desk.sqlite3, rotated desk.log; inbox
   /var/lib/vivameda-meme-desk-live/tickets.json, optional reserves.jsonl;
   root confirmation /etc/vivameda-meme-desk/delivery.json stays false. Desk AF_UNIX
   only; bounded resource use and 3 GiB reserve guard. Do not use deploy_crypto.
   No compatible existing authenticated sender bridge has been established. Confirm
   destination AND owner ID/socket contract before delivery. No token/API-key fallback.
   Rate limits queue globally; bridge must deduplicate idempotency keys after crashes.
10. Next steps. First owner export; inspect reserve coverage and compute/publish ONLY
    aggregates. Then owner installation/refreshing sanitized feed and 3600-second
    isolated shadow run. Report count and genuine examples (if any), otherwise retain
    honest zero and rejection counts. After destination/sender confirmation validate
    actual delivery separately. Later step 3: public-address position tracker after
    owner supplies Phantom PUBLIC address. Step 4: reconcile real fills and skipped
    ticket outcomes without inventing PnL. Step 5: weekly review. Keep future work
    separate from frozen replay protocol and existing prediction study.

## Exact owner commands

Export history read-only; this gives engineering read access to the NEW export file
only, never to the scanner DB. Without an archive it establishes counts/coverage but
cannot manufacture authenticated historical reserves:

```sh
ssh vivameda-server 'sudo python3 -B -c '"'"'import hashlib,pathlib,sys; p=pathlib.Path('"'"'"'"'"'"'"'"'/var/lib/vivameda-engineering/repo/client_learning/meme_desk_v1_20261017/owner.py'"'"'"'"'"'"'"'"'); b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='"'"'"'"'"'"'"'"'16871a05d86130e1bdee4a5dd5f1e60f4696298b9540fa4f2d4570c1da9b1d3c'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'Owner runner hash mismatch'"'"'"'"'"'"'"'"'; sys.argv=[str(p),'"'"'"'"'"'"'"'"'--expected-bundle'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'d0f25ec5398fe230f7eecf2cfa84589a8919a9f79875dd1ebd2ac0f209a9ef84'"'"'"'"'"'"'"'"']+sys.argv[1:]; exec(compile(b,str(p),'"'"'"'"'"'"'"'"'exec'"'"'"'"'"'"'"'"'),dict(__name__='"'"'"'"'"'"'"'"'__main__'"'"'"'"'"'"'"'"',__file__=str(p)))'"'"' export -- --mode replay --output /var/lib/vivameda-meme-desk-export/replay.json --reader-uid 994'
```

If an approved archived capture file exists, append
`--reserve-archive /absolute/path/to/approved-captures.jsonl` to that export command
INSIDE the remote command argument. The archive is read-only, original timestamps
must be preserved, and its schema/authentication must pass reserves.py. Do not create
fake captures to get resolved cases. Owner export directory is root-owned, reader
primary group read-only; exported frozen mints are absent.

Offline replay after that export (no live service change):

```sh
ssh vivameda-server 'sudo python3 -B -c '"'"'import hashlib,pathlib,sys; p=pathlib.Path('"'"'"'"'"'"'"'"'/var/lib/vivameda-engineering/repo/client_learning/meme_desk_v1_20261017/owner.py'"'"'"'"'"'"'"'"'); b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='"'"'"'"'"'"'"'"'16871a05d86130e1bdee4a5dd5f1e60f4696298b9540fa4f2d4570c1da9b1d3c'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'Owner runner hash mismatch'"'"'"'"'"'"'"'"'; sys.argv=[str(p),'"'"'"'"'"'"'"'"'--expected-bundle'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'d0f25ec5398fe230f7eecf2cfa84589a8919a9f79875dd1ebd2ac0f209a9ef84'"'"'"'"'"'"'"'"']+sys.argv[1:]; exec(compile(b,str(p),'"'"'"'"'"'"'"'"'exec'"'"'"'"'"'"'"'"'),dict(__name__='"'"'"'"'"'"'"'"'__main__'"'"'"'"'"'"'"'"',__file__=str(p)))'"'"' replay -- --input /var/lib/vivameda-meme-desk-export/replay.json --private-rows /var/lib/vivameda-meme-desk-export/private_replay_rows.json --aggregates /var/lib/vivameda-meme-desk-export/replay_aggregates.json --markdown /var/lib/vivameda-meme-desk-export/REPLAY_RESULTS.md'
```

The markdown output contains only aggregates; private_replay_rows.json stays server
private. Return/publish the aggregate markdown only. A successful command with zero
resolved cases is not evidence of profitability.

OPTIONAL owner installation, after reviewing the source/bundle:

```sh
ssh vivameda-server 'sudo python3 -B -c '"'"'import hashlib,pathlib,sys; p=pathlib.Path('"'"'"'"'"'"'"'"'/var/lib/vivameda-engineering/repo/client_learning/meme_desk_v1_20261017/owner.py'"'"'"'"'"'"'"'"'); b=p.read_bytes(); assert hashlib.sha256(b).hexdigest()=='"'"'"'"'"'"'"'"'16871a05d86130e1bdee4a5dd5f1e60f4696298b9540fa4f2d4570c1da9b1d3c'"'"'"'"'"'"'"'"', '"'"'"'"'"'"'"'"'Owner runner hash mismatch'"'"'"'"'"'"'"'"'; sys.argv=[str(p),'"'"'"'"'"'"'"'"'--expected-bundle'"'"'"'"'"'"'"'"','"'"'"'"'"'"'"'"'d0f25ec5398fe230f7eecf2cfa84589a8919a9f79875dd1ebd2ac0f209a9ef84'"'"'"'"'"'"'"'"']+sys.argv[1:]; exec(compile(b,str(p),'"'"'"'"'"'"'"'"'exec'"'"'"'"'"'"'"'"'),dict(__name__='"'"'"'"'"'"'"'"'__main__'"'"'"'"'"'"'"'"',__file__=str(p)))'"'"' install'
```

It creates a fresh dedicated system user, immutable source, own export timer and
shadow desk unit. It refuses any pre-existing installation/path and has no upgrade
or balance-reset mode. Initial reserve archive is empty. Existing services unchanged.

Once the export timer supplies fresh actual inputs, run exactly 60 minutes in
separate shadow state; no Telegram even if delivery is configured later:

```sh
ssh vivameda-server 'sudo -u vivameda-meme-desk python3 -B /opt/vivameda-meme-desk/current/service.py shadow --duration 3600 --state-dir /var/lib/vivameda-meme-desk/shadow-20261017 --input /var/lib/vivameda-meme-desk-live/tickets.json'
```

Read /var/lib/vivameda-meme-desk/shadow-20261017/shadow_receipt.json and desk.log;
require duration >=3600 AND valid_export_polls>0, and check coverage/freshness/reasons.
Counts from a blocked run are not a passed dry run. Reuse of the same shadow state
would deduplicate tickets, so a second run needs a separately named state directory.

Inspect/stop only the desk:

```sh
ssh vivameda-server 'systemctl status vivameda-meme-desk.service --no-pager'
ssh vivameda-server 'sudo -u vivameda-meme-desk python3 -B /opt/vivameda-meme-desk/current/service.py report --state-dir /var/lib/vivameda-meme-desk'
ssh vivameda-server 'sudo systemctl stop vivameda-meme-desk.service vivameda-meme-desk-export.timer'
```

No service was installed by the engineering connector. Owner commands are necessary
because protected data access and new system-unit installation require owner/root
capabilities that the connector does not expose. They are concrete reviewed actions,
not requests for permission to repeat already authorized routine work.

## Exact scoped server validation

Job `52950fbdaa6a41e92129f20362f52aec`: all 15 runtime bundle files verified; 52 tests passed on server Python 3.12 in 1.289 seconds; bounded startup status WAITING_FOR_OWNER_EXPORT, 0 tickets and 0 valid export polls. No protected database was opened and no service was installed.

## Runtime file hashes

```json
{
  "README.md": "d944137c4ecbc82e17647980208c348aca4a1a3ad04b4a0dcd2a086332ac86c3",
  "REPLAY_PROTOCOL.md": "62c4b3e4b13dbc97a3c973cf22b9fb40eb78a2e006c315e20abd8df92b5195a2",
  "common.py": "68203a84dc556357c026718fbca16cc9b232cbc2762877a40473222b6c8a753b",
  "config.json": "701474d4653f201a331007584a34494041746e362df59558043a2cc198234c25",
  "delivery.py": "33d8fa260ceae7850b62537c1b9ee551294bb096e9c94871895495e2520e3a61",
  "exporter.py": "2cccb950fab9859e54afec820af18287f5b489dcc3539e636926f2bef6789cf0",
  "install.py": "d472e20964eab553172c7e2263a3cfce03ecc72ad31f84c7749acb08f9ca8043",
  "journal.py": "abf2c8fdebc2c3cc30c8d1513c19f5da70ae42afcb19d2f31c3953deb1483ba8",
  "owner.py": "16871a05d86130e1bdee4a5dd5f1e60f4696298b9540fa4f2d4570c1da9b1d3c",
  "replay.py": "470e6544a8a229f4bc5e485792c0e8e3afd04246309d7616f5de565bd84f033a",
  "reserves.py": "ea7a80b383eae64f328b9f349671d4d486e37c4da2d40de3be614b72d64bff2a",
  "service.py": "4c95331af27b3a704ec7a6c996aadd51ca3a4b3c73ff8d49d1cb67a2b5244e4b",
  "tests/test_desk.py": "99d4789c90a83b990f0c94bb6ee16cc016b85d5220ce5602ac190fad6ccbf200",
  "tickets.py": "000a71c331468fd28335da4a237ab72aa767977bd979f86eda2161190099ed56",
  "verify.py": "57188a78561b26ae954142b497e34da4c6a18df4050a5fc8a9f1897c0f6d802c"
}
```

Final installer review added a restrictive-umask staging test and explicit read/traverse permissions for public source and the desk inbox/config directory. The local scoped suite is now 53 tests; the final repository gate verifies that final bundle. Prior 52-test receipts describe the earlier exact bundle, not this amendment. No unit has been installed.

## Final repository gate

Job `d30bdb5932f7d18ad98c8c49e3acf64f` passed **827 tests across 25 suites**, including **53 meme-desk tests**, on server Python 3.12 in 33.885 seconds. All 347 repository file hashes matched. Final runtime BUNDLE SHA-256 is `d0f25ec5398fe230f7eecf2cfa84589a8919a9f79875dd1ebd2ac0f209a9ef84`. Only evidence documentation and its manifest hashes were amended afterward; protocol and executable source are unchanged. Data-dependent gates remain blocked.
