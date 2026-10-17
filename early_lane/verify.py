"""Verify a pinned release without importing any production code."""
import hashlib
import json
from pathlib import Path

def verify(expected,root=None):
    root=Path(root or Path(__file__).resolve().parent);raw=(root/'BUNDLE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('bundle_hash_mismatch')
    manifest=json.loads(raw)
    for name,want in manifest['sha256'].items():
        path=Path(name)
        if path.is_absolute() or '..' in path.parts or (root/path).is_symlink():raise ValueError('unsafe_bundle_path')
        if hashlib.sha256((root/path).read_bytes()).hexdigest()!=want:raise ValueError('bundle_file_mismatch:'+name)
    return manifest
