#!/usr/bin/env python3
import hashlib
import json
import pathlib
root = pathlib.Path(__file__).resolve().parent
release = json.loads((root / 'RELEASE.json').read_text())
for name, expected in release['sha256'].items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != expected:
        raise SystemExit('Mismatch: ' + name)
print(json.dumps({'verified_files': len(release['sha256']), 'release_sha256': hashlib.sha256((root / 'RELEASE.json').read_bytes()).hexdigest()}))
