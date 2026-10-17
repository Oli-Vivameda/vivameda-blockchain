# Exact owner commands — not executed

No root privilege is available to engineering. These commands install only NEW
lane units, without starting/enabling any unit during installation. Scanner units,
source, data permissions and frozen studies remain unchanged. Review this source
and the blocked rollout record first. The public host alias is used below.

## 1. Hash-checked owner installer

The bootstrap reads owner.py once, hashes those exact bytes, then executes them.
owner.py verifies/snapshots every pinned bundle file before importing project code.

```sh
ssh vivameda-server 'sudo /usr/bin/python3 -' <<'PY'
from pathlib import Path
import hashlib, sys
p=Path('/var/lib/vivameda-engineering/repo/early_lane/owner.py')
b=p.read_bytes()
assert hashlib.sha256(b).hexdigest() == '169412fafe354bb875e18bd7dd14a6a069b0b5ebd9320d0a8921eb84aa578eb3', 'owner.py hash mismatch'
sys.argv=[str(p),'--expected-bundle','d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442','install']
exec(compile(b,str(p),'exec'),{'__name__':'__main__','__file__':str(p)})
PY
```

Expected receipt: installed true, started false, enabled false, channel TBD. If any
installation path/user/unit exists, the installer refuses to overwrite it. Do not
remove an old state directory to bypass this guard. Source DB defaults to the
existing scanner path; if that layout differs, stop and review the exact source.
No ownership/mode changes are made to the scanner database or directory.

## 2. Start only the new read-only exporter and a durable two-hour LOG-ONLY run

```sh
ssh vivameda-server 'sudo systemctl enable --now vivameda-early-lane-export.timer'
ssh vivameda-server 'sudo systemd-run --unit=vivameda-early-lane-rollout --uid=vivameda-early-lane --gid=vivameda-early-lane --property=WorkingDirectory=/opt/vivameda-early-lane/d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442 --property=NoNewPrivileges=yes --property=UMask=0027 /usr/bin/python3 -B /opt/vivameda-early-lane/d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442/owner.py --expected-bundle d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442 log-only -- --state-dir /var/lib/vivameda-early-lane --input /var/lib/vivameda-early-lane-inbox/feed.json --duration 7200'
```

This transient unit survives a laptop disconnect. It sends **no Telegram**, even if
a confirmation file were present. It shares the journal with eventual live operation,
so selection identities, suppression cohorts and the freeze clock survive promotion.
Do not start the continuous lane concurrently; its process lock rejects that.

## 3. Inspect actual receipts before deciding to enable continuous operation

```sh
ssh vivameda-server 'sudo systemctl status vivameda-early-lane-rollout.service vivameda-early-lane-export.timer --no-pager'
ssh vivameda-server 'sudo cat /var/lib/vivameda-early-lane/log_only_receipt.json'
ssh vivameda-server 'sudo -u vivameda-early-lane /usr/bin/python3 -B /opt/vivameda-early-lane/d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442/owner.py --expected-bundle d3811acb413725198003870b55b39ad775261289a53cf85f906c657e384a8442 report -- --state-dir /var/lib/vivameda-early-lane'
```

The completed receipt must actually cover two hours with fresh feed. No valid polls,
large gaps, UNKNOWN RPC gates, missing checkpoints or incomplete pagination are
reported as limitations, never converted into a pass. A zero-alert valid run is a
valid observation; an absent feed is not. Keep logs/SQLite private; only publish
aggregates. Choose three actual messages from the private log if any exist.

## 4. Delivery remains blocked until the NEW channel and an existing sender are confirmed

No generic command is provided to fabricate these missing owner inputs. Do not
supply a bot token or create an account/API key. A compatible existing sender must
accept the root-authenticated Unix-socket protocol in transport.py, enforce durable
idempotency by event key and return actual delivery receipts or Telegram Retry-After.
No sender is installed here. Then an owner may write root-owned, non-group/world-
writable /etc/vivameda-early-lane/delivery.json with these fields:

```json
{"new_channel_confirmed": false, "channel": null, "confirmed_at": null, "socket": null}
```

The initial file remains as shown. Only after explicit destination confirmation,
sender validation and real rollout review should those values change. Confirmation
must name a NEW Telegram channel (numeric -100... ID), not the scanner's chat, and
use the actual confirmation epoch. Shadow cohort records never enter delivery,
even if confirmation predated them. Retry queues persist and late messages show age.
After these prerequisites, the owner can start the dedicated continuous unit:

```sh
ssh vivameda-server 'sudo systemctl enable --now vivameda-early-lane.service'
```

This command is a documented future action, not executed or currently cleared by a
successful rollout/destination check. Existing scanner/monitor services are untouched.

To stop only this experiment:

```sh
ssh vivameda-server 'sudo systemctl stop vivameda-early-lane.service vivameda-early-lane-export.timer'
```

The journal is retained. A future reviewed upgrade must preserve/backup state rather
than reinstalling over it. Review is due at the journal's activation epoch +14 days;
final cohort maturation is +15 days +120 seconds. There is no activation date yet.
