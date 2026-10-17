# Evidence repair: exact owner commands — 17 October 2026

Run in the existing root server terminal. These stop only early-lane components,
upgrade from installed RPC bundle 41b453fb, preserve all journal rows/activation,
and run log-only. They do not start the sender or continuous lane, edit delivery
configuration, touch scanner permissions, or change scanner/learner/monitors.
If a checked precondition fails, stop and share that error. Do not bypass it.

1. Stop the lane exporter and lane before the checked migration. Previously
completed transient rollouts must also be inactive; the installer checks them.

```bash
systemctl stop vivameda-early-lane-export.timer vivameda-early-lane-export.service vivameda-early-lane.service
```

2. Verify the owner bootstrap and install the reviewed candidate without starting.

```bash
python3 - <<'PYOWNER'
from pathlib import Path
import hashlib, sys
p = Path('/var/lib/vivameda-engineering/repo/early_lane/owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == 'd97bb8e4474418b8ba5d02bdf41f1e97e575d91e9290fdca78b79db9d79d5c47', 'owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', '0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91', 'evidence-upgrade', '--', '--from-bundle', '41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PYOWNER
```

Expected: upgraded true, journal_preserved true, original activation retained,
started false, screening_ready false, delivery_enabled false. Root preflight
prices a recent exported sample only; it does not establish full screening.
It can refuse on public-RPC throttling before modifying installation.

3. Refresh the approved read-only feed, then start a bounded two-hour shadow run.
The exporter timer was already owner-enabled; these commands start it again.

```bash
systemctl start vivameda-early-lane-export.service
systemctl start vivameda-early-lane-export.timer
systemd-run --collect \
  --unit=vivameda-early-lane-evidence-shadow \
  --uid=vivameda-early-lane --gid=vivameda-early-lane \
  --property=WorkingDirectory=/opt/vivameda-early-lane/0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91 \
  --property=NoNewPrivileges=yes --property=UMask=0027 \
  /usr/bin/python3 -B \
  /opt/vivameda-early-lane/0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91/owner.py \
  --expected-bundle 0fe47cf110ada00f33172f66ac02dcc1403e3214aa19610e6d60185e36e30d91 log-only -- \
  --state-dir /var/lib/vivameda-early-lane \
  --input /var/lib/vivameda-early-lane-inbox/feed.json --duration 7200
```

4. Inspect fresh heartbeats and paste the output back. collection_issues now names
account/history/social blockers. enriched_candidates and fully_evaluated_candidates
are per poll, not distinct mints. UNKNOWN still withholds alerts.

```bash
journalctl -u vivameda-early-lane-evidence-shadow.service -n 5 --no-pager -o cat
```

After two hours, obtain the NEW receipt (check started_at matches this run):

```bash
cat /var/lib/vivameda-early-lane/log_only_receipt.json
```

transport_rollout_pass requires duration >=7200s and valid/priced observation gaps
<=120s. screening_rollout_pass additionally requires at least one fully evaluated
candidate poll with no UNKNOWN gates; it does not require an eligible alert or
prove population-wide coverage. live_rollout_pass now uses both gates. Review
missing data and throughput before enabling delivery; no activation command is
included. No new test message is needed: the owner's earlier one-shot receipt
already confirms the destination. Replays of that test are idempotent.
