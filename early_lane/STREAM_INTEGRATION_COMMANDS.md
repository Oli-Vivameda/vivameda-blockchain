# Owner commands — corrected activated-journal staging

This release fixes the staging integrity reader for an already activated study.
Run from the reviewed release's early_lane directory, using Python 3.12.
Server-specific source locations are supplied separately to the owner.

Verify the entrypoint before staging. Staging copies reviewed files only; it
does not start or enable services, edit delivery configuration or reset a study.

```bash
python3 -B - <<'PY'
from pathlib import Path
import hashlib, sys
p = Path('stream_owner.py').resolve()
b = p.read_bytes()
assert hashlib.sha256(b).hexdigest() == 'd709d835078cfd33fd30ceb208fd1ce16fb119692e519b0b90530c4d077186cd', 'stream owner.py hash mismatch'
sys.argv = [str(p), '--expected-bundle', 'e625f0b13233dd4e6ee2e20f6cdb95359e588c0414ba733a50477dd6cd7c2e38', 'stage']
exec(compile(b, str(p), 'exec'), {'__name__': '__main__', '__file__': str(p)})
PY
```

Expected: staged/already_staged, started=false, enabled=false. Existing journal
activation and cohorts are verified and preserved. Stop on any error. Bounded
shadow operation remains a separate owner action using this same reviewed bundle.
