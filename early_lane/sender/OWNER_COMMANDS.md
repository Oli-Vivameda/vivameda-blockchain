# Owner commands — sender only — 17 October 2026

Run from the existing ROOT server terminal. Source is staged in the separate
engineering checkout. These commands do not start or enable either service.
Do not rerun early-lane installation/upgrade or interrupt its log-only observation.

## 1. Install sender definitions, without starting

The bootstrap checks its own bytes, verifies the complete independent sender bundle,
and executes captured reviewed source in a private temporary directory. Installation
runs offline tests, verifies unit syntax, checks credential metadata without reading
its contents, creates only the new sender release/state/unit, and daemon-reloads.
It never changes the existing credential, delivery.json, scanner, lane units or rules.
It refuses an existing sender installation rather than overwriting it. Python 3.12
and the existing vivameda-early-lane account are required. Existing credential must
be an owner-only regular file (0400/0600) owned by root or vivameda-scout. Existing
scanner ownership and permissions are preserved. The service's only bounded
capability is CAP_DAC_READ_SEARCH for this runtime read; no permission change or
credential copy is required.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('/var/lib/vivameda-engineering/repo/early_lane/sender/owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == '4f49e1ed7cd166527c2df008e4231fdf15bc2e2ecb040c973e6949209d2a3274', 'sender owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', '5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b', 'install']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

Expected JSON: installed=true, started=false, enabled=false,
delivery_config_changed=false, credential_contents_read=false.
If checks fail, retain state and report the fixed error; do not change permissions
or bypass a hash. Owner metadata confirmed vivameda-scout ownership and mode 0600. The original
sender installer wrongly assumed root ownership and stopped before any install
writes. This corrected bundle accepts the existing scanner account and still
rejects other owners, symlinks and all group/world access. Partial installation failures are visible and
require review; the installer does not start anything or remove existing state.

## 2. Owner-only channel test, when the channel ID is available

Prerequisites: the existing bot is an admin in the NEW private channel, and its numeric
-100... ID is already the channel value in root-owned
/etc/vivameda-early-lane/delivery.json through a separately authorized owner action.
That file is currently unconfirmed/TBD. **This task and these commands do not edit
it.** Keep new_channel_confirmed=false for this test. The test cannot substitute
another channel or the scanner chat. No bot token is entered into a command.

Replace PASTE_NUMERIC_NEW_CHANNEL_ID below with that same numeric ID. Run only after
installation, with the sender service still stopped. It sends one fixed test message,
prints only the real Telegram receipt, and leaves delivery confirmation unchanged.
Repeating the command returns the saved receipt rather than sending another message.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('/opt/vivameda-early-lane-sender/5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b/owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == '4f49e1ed7cd166527c2df008e4231fdf15bc2e2ecb040c973e6949209d2a3274', 'sender owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', '5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b', 'test-channel', '--', '--expected-channel', 'PASTE_NUMERIC_NEW_CHANNEL_ID']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

Success: status=200, receipt with chat_id/message_id/date. Check that single message
in Telegram. A 429 reply includes retry_after; wait at least that long and rerun this
same command. Status 409 means uncertain delivery: inspect the channel privately,
report the held event, and do not change its key or delete the journal. Status 403
means destination/configuration/credential checks failed; no message was attempted.
No exception text, API description, token or raw Telegram response is returned.

## 3. Verify stopped state (read-only)

```bash
systemctl show vivameda-early-lane-sender.service -p ActiveState -p UnitFileState
systemctl show vivameda-early-lane.service -p ActiveState -p UnitFileState
```

Sender should remain inactive/disabled. The existing log-only transient rollout is
separate. No start/enable command is supplied: continuous delivery is outside this
task and requires the owner-confirmed channel, a reviewed rollout result and a later
explicit activation action. Test-channel confirmation alone does not enable it.

Bundle SHA-256: 5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b

Bootstrap SHA-256: 4f49e1ed7cd166527c2df008e4231fdf15bc2e2ecb040c973e6949209d2a3274
