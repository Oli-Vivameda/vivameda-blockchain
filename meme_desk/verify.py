"""Offline release verification, no protected data or network."""
import hashlib
import json
from pathlib import Path

def verify(expected):
    root=Path(__file__).resolve().parent
    raw=(root/'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('reviewed_bundle_mismatch')
    b=json.loads(raw)
    for name,want in b['sha256'].items():
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or (root/p).is_symlink():raise ValueError('unsafe_bundle_path')
        if hashlib.sha256((root/p).read_bytes()).hexdigest()!=want:raise ValueError('reviewed_source_mismatch:'+name)
    return b
