# Owner command — shared scanner channel + 🌻 — 17 October 2026

Owner explicitly replaced the separate-channel requirement: reuse the scanner's
existing Telegram channel, and prefix every early-lane message with 🌻.
No new channel, bot, token or pasted channel ID is required.

Current owner receipt confirms sender bundle
5ae872c9f5295ef58cc954d7f9eddac6319fecab2afebe6cf3f81d13b706518b
installed, stopped, disabled; delivery config unchanged. Do not rerun initial install.

From the existing ROOT server terminal, paste this entire command. It:

1. Checks bootstrap and complete new source bundle.
2. Requires sender and continuous lane units inactive and disabled, and unconfirmed
   delivery config. Leaves the separate transient log-only observation untouched.
3. Hash-verifies the old sender, preserves its state, backs up its unit, installs the
   new root-owned release and updates its definition. Starts/enables no service.
4. At runtime reads the existing scanner credential in place; copies only chat_id
   into root-owned delivery.json and sets reuse_scanner_channel=true. The token is
   never copied, printed, logged or stored. Scanner files/permissions are unchanged.
5. Keeps new_channel_confirmed=false and confirmed_at=null. Runs a direct, fixed,
   owner-only 🌻 channel test and saves its real receipt in sender state.

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('/var/lib/vivameda-engineering/repo/early_lane/sender/owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == '3c5d1d91438a39f919d10a2ef5cf94f282e7adc2340894ddf401adbe50f32232', 'sender owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', '28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724', 'upgrade-scanner-test']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

Success prints an install/upgrade receipt with started=false, enabled=false, followed
by status=200 and a Telegram receipt (chat_id/message_id/date only). Look for one
🌻 EARLY LANE CHANNEL TEST message in the existing scanner channel. Paste the final
output back privately. This sends a test only; it does not start continuous alerts.
Repeating the same command safely reuses the installed bundle and test event key.
429: wait retry_after seconds and rerun it. 409: uncertain delivery is held; inspect
the channel privately and report the result, without deleting state or changing keys.
Other refusal: stop and report the fixed error. Do not change credential permissions.

Root-only delivery.json remains an exact destination allowlist. Without its explicit
reuse_scanner_channel=true flag, the sender still refuses the scanner chat. The
legacy field new_channel_confirmed retains its wire-contract name but stays false
for this test. A later, separately authorized activation is required for continuous
traffic. No start/enable command is supplied here. No Telegram is ever sent by tests.

Bundle SHA-256: 28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724

Bootstrap SHA-256: 3c5d1d91438a39f919d10a2ef5cf94f282e7adc2340894ddf401adbe50f32232
