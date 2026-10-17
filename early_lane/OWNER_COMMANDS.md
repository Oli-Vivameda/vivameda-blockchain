> Current phase: the owner has already applied the repair. Do not rerun the upgrade or start duplicate workers. The active log-only unit is vivameda-early-lane-rollout-rpc2.service. After about 12:21 Cyprus, inspect `/var/lib/vivameda-early-lane/log_only_receipt.json`. The commands below are retained for their documented phases; preserve the journal.

# Owner commands — source repair, 17 October 2026

The initial d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442 installation succeeded, but Pump.fun's website API returns
HTTP 403/Cloudflare. The owner stopped the rollout and export timer. A scanner-only
read-only export returned 597 recent launches and ZERO fresh market observations.
That is discovery data, not a valid priced rollout. No Telegram or activation result.

## Apply the reviewed repair from the existing ROOT server terminal

This command checks the bootstrap bytes and the complete new bundle. The upgrader
requires the old reviewed bundle, inactive early-lane jobs and an untouched/no-cohort
journal. It first tests live pricing on up to 30 owner-exported recent mints. If no
authenticated price can be obtained, it ABORTS BEFORE changing unit files. Pricing
preflight is not a full screening or end-to-end alert pass. It preserves journal,
user and delivery config, backs up old unit definitions, and starts/stops no service.
No scanner source/permissions/services or frozen rules are changed.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, sys
p=Path('/var/lib/vivameda-engineering/repo/early_lane/owner.py')
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest() == '730096c0d5a67633289724711325c775af72b025d93e712f1a039af15d88df0c', 'owner.py hash mismatch'
sys.argv=[str(p),'--expected-bundle','41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d','upgrade','--','--from-bundle','d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442']
exec(compile(b,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
PY
```

Expected receipt: upgraded true, journal_preserved true, started false,
scanner_changed false, public_launch_refresh false, plus positive authenticated
live_pricing_preflight counts. If any check fails, paste the error; never delete the
state or bypass a hash/activation check. Do not restart the old HTTP-dependent run.

## Only AFTER successful upgrade: start a fresh log-only run

```bash
systemctl start vivameda-early-lane-export.service && systemctl start vivameda-early-lane-export.timer
systemd-run --unit=vivameda-early-lane-rollout-rpc2 --uid=vivameda-early-lane --gid=vivameda-early-lane --property=WorkingDirectory=/opt/vivameda-early-lane/41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d --property=NoNewPrivileges=yes --property=UMask=0027 /usr/bin/python3 -B /opt/vivameda-early-lane/41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d/owner.py --expected-bundle 41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d log-only -- --state-dir /var/lib/vivameda-early-lane --input /var/lib/vivameda-early-lane-inbox/feed.json --duration 7200
```

This NEW run uses the SAME preserved state; old missing-input waiting is not counted.
The old receipt may be overwritten by the new receipt, while its append-only journal
is preserved. The previous run had 0 valid polls and no alert cohort. Log-only never
sends to Telegram, even if a delivery config is present.

## Immediate check and completed receipt

```bash
journalctl -u vivameda-early-lane-export.service -u vivameda-early-lane-rollout-rpc2.service -n 20 --no-pager -o cat
```

Fresh owner-feed polls AND fresh_market_marks must appear. A running unit alone is
not a pass. Missing prices do not activate the observational clock and cannot pass
the rollout gate. JSON-RPC throttles and Retry-After are respected. Remaining UNKNOWN
checks, partial pricing coverage, USDC/mayhem/boost layouts and throughput limits
must be disclosed. No filter is relaxed to produce alerts.

After a genuine 7200 seconds:

```bash
cat /var/lib/vivameda-early-lane/log_only_receipt.json
sudo -u vivameda-early-lane /usr/bin/python3 -B /opt/vivameda-early-lane/41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d/owner.py --expected-bundle 41b453fb10042452c0f35a215973d6eb0c21fb07703ce59425558dc41946ea1d report -- --state-dir /var/lib/vivameda-early-lane
```

No Telegram destination or sender has been confirmed. Do not enable continuous
sending. No bot key, wallet, signup or paid call is needed for this repair. The public
RPC reads the on-chain Pyth oracle; it does not call Hermes or acquire an API key.
There is still no valid two-hour result or booked 14-day review date.

If stopping the experiment is needed, affect only its units:

```bash
systemctl stop vivameda-early-lane-export.timer vivameda-early-lane-rollout-rpc2.service vivameda-early-lane.service
```

Initial installation instructions are preserved in Git commit b0b4d375. They must not
be rerun over an existing installation. The original source remains installed until
the checked repair succeeds. Public operator commands may use ssh vivameda-server;
inside an existing root session, run the commands above directly.
