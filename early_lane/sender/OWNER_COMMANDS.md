> Completed owner receipt: bundle 40c80bc0 installed/stopped/disabled; the direct 🌻
> private-chat test returned status 200. No need to rerun. Commands below remain an
> idempotent reference; automatic delivery stays off.

# Owner command — existing private scanner chat + 🌻 — 17 October 2026

Owner selected the same destination as the scanner. Metadata-only owner diagnostics
show this is a private bot chat, not a -100 channel. The previous shared-channel test
refused that ID before changing delivery config or making an API call. No new channel,
bot, token, manual ID lookup or scanner/credential permission changes are needed.

Current installed bundle is 28ee6a4270f371c5718fb6e944b92f672268ee608ded27421df85f0dce15c724,
owner-confirmed stopped/disabled. Run this from the existing ROOT server terminal:

```bash
python3 - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('/var/lib/vivameda-engineering/repo/early_lane/sender/owner.py')
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == 'c970b317957200b792006a5fe4ee40b3a8d31a22dd949c7aa7776b056880e9dd', 'sender owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', '40c80bc0d7b6049507bf0be3ac6758f5aed714c32e18beb7ecab21f871d9e63f', 'upgrade-scanner-test']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

The command checks bootstrap/new bundle, requires sender and continuous lane inactive
and disabled, verifies the installed old bundle/unit and preserves its private state.
It installs only the new sender release and updates that stopped unit. It then runs
a direct owner-only test: reads the existing credential at runtime, copies chat_id
alone into root-owned lane delivery.json, sets reuse_scanner_channel=true, preserves
file ownership/mode, and keeps new_channel_confirmed=false, confirmed_at=null.
The bot token is never copied, logged, printed or stored. No service is started or
enabled and the transient log-only observation is untouched.

Success: an install receipt with started=false, enabled=false, then status=200 with
real chat_id/message_id/date receipt. Check for one 🌻 EARLY LANE CHANNEL TEST in your
existing bot conversation. Paste the final receipt back privately. Repeating the
same command returns the saved test receipt. On 429, wait retry_after and rerun.
On 409, inspect the held uncertain event privately; never delete state or change keys.
Other refusal: stop and report it. No Telegram calls are made by offline tests.

Only the exact destination in root-owned config is allowed. With shared mode true,
it must also exactly match scanner chat_id, whether private chat, basic group or
-100 channel/supergroup. Without shared mode, the original -100-only admission stays.
All early-lane messages begin with 🌻. The command sends one test; automatic delivery
remains off. The unchanged lane client still has its original -100 confirmation
check; private-chat activation needs a separate reviewed client compatibility update,
the actual completed log-only report and later explicit owner activation. This
command does not change the installed lane runtime or start that process.

Bundle SHA-256: 40c80bc0d7b6049507bf0be3ac6758f5aed714c32e18beb7ecab21f871d9e63f

Bootstrap SHA-256: c970b317957200b792006a5fe4ee40b3a8d31a22dd949c7aa7776b056880e9dd
