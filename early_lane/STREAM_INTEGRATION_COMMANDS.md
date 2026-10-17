# Owner commands — staged stream screening shadow

Run in the existing root terminal. This stages files and runs one bounded shadow.
It does not start the continuous lane or send Telegram messages. Stop if any
command reports an error; do not substitute another bundle or bypass a hash check.

## 1. Stage reviewed files, without starting a service

```bash
python3 -B - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('/var/lib/vivameda-engineering/repo/client_learning/early_lane_v1_20261017/stream_integration_release_check/early_lane/stream_owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == 'd709d835078cfd33fd30ceb208fd1ce16fb119692e519b0b90530c4d077186cd', 'stream owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', 'f2e428814ddbb8922969287de23859d726bbb76f45b8a16db9e00597d70daebb', 'stage']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

Expected: staged/already_staged, started=false, enabled=false. No units or delivery
configuration changed. Existing journal/activation retained.

## 2. Refresh the approved export and run ten minutes, log-only

```bash
systemctl start vivameda-early-lane-export.service
systemctl start vivameda-early-lane-export.timer
```

If that succeeds:

```bash
systemd-run --collect \
  --unit=vivameda-early-lane-stream-shadow \
  --uid=vivameda-early-lane \
  --gid=vivameda-early-lane \
  --property=WorkingDirectory=/opt/vivameda-early-lane/f2e428814ddbb8922969287de23859d726bbb76f45b8a16db9e00597d70daebb \
  --property=NoNewPrivileges=yes \
  --property=UMask=0027 \
  /usr/bin/python3 -B \
  /opt/vivameda-early-lane/f2e428814ddbb8922969287de23859d726bbb76f45b8a16db9e00597d70daebb/stream_owner.py \
  --expected-bundle f2e428814ddbb8922969287de23859d726bbb76f45b8a16db9e00597d70daebb \
  shadow -- \
  --state-dir /var/lib/vivameda-early-lane \
  --input /var/lib/vivameda-early-lane-inbox/feed.json \
  --duration 600
```

Do not start a second copy. The process lock prevents concurrent lane writers.

## 3. Inspect progress; after completion, read the new receipt

```bash
journalctl -u vivameda-early-lane-stream-shadow.service -n 8 --no-pager -o cat
```

After about ten minutes:

```bash
cat /var/lib/vivameda-early-lane/stream_screening_receipt.json
```

Use this NEW receipt, not the old log_only_receipt.json. Send the output back for
review. Zero alerts may be correct. Zero fully evaluated candidates remains a
failed screening feasibility gate. This short run is not the two-hour rollout.
The two-hour run is a later explicit command after reviewing this short receipt.
