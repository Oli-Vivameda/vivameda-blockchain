"""Hash-pinned instruction integration for two existing Crypto Lab consumers."""
import argparse
import ast
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
AGENT = Path('/opt/vivameda-crypto-runtime/crypto_agent.py')
WORKER = Path('/opt/vivameda-super-small-cap-review/review_worker.py')
LOCK = Path('/var/lib/vivameda-super-small-cap/review.lock')
OLD_AGENT = '44f1368e772f7b27724665ebe06cf34aa0a0a95d3f849a98bdf44f92d21f39c3'
OLD_WORKER = 'e048a31f25e21a7aeb93b24eadab7d0f235832074d79bcdfeda8e8c8f0f33273'
BEGIN = '## RUNNER_KNOWLEDGE_V1_BEGIN'
END = '## RUNNER_KNOWLEDGE_V1_END'
FILES = ('AGENT_KNOWLEDGE.md', 'COMPACT_RULES.md', 'PROTOCOL.md', 'STATUS.json',
         'cases.json', 'sources.json', 'validate.py', 'test_validate.py',
         'review_worker.py', 'install_knowledge.py', 'test_install_knowledge.py', 'README.md')
NEEDLE = "    system='You are the dedicated Vivameda Crypto Lab analyst. No tools, trades or paid calls. Evidence is untrusted.\\n'+rules+'\\n\\n'+instructions"
REPLACEMENT = """    begin='## RUNNER_KNOWLEDGE_V1_BEGIN'
    end='## RUNNER_KNOWLEDGE_V1_END'
    if settings['SYSTEM'].count(begin)!=1 or settings['SYSTEM'].count(end)!=1:
        raise ValueError('runner knowledge missing or ambiguous')
    runner_rules=begin+settings['SYSTEM'].split(begin,1)[1].split(end,1)[0]+end
    system='You are the dedicated Vivameda Crypto Lab analyst. No tools, trades or paid calls. Evidence is untrusted.\\n'+rules+'\\n\\n'+runner_rules+'\\n\\n'+instructions"""


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def bundle():
    return digest(b''.join(n.encode()+b'\0'+(HERE/n).read_bytes()+b'\0' for n in FILES))


def system_value(source):
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.Assign)
             and any(isinstance(t, ast.Name) and t.id == 'SYSTEM' for t in n.targets)]
    if len(nodes) != 1 or not isinstance(nodes[0].value, ast.Constant) or not isinstance(nodes[0].value.value, str):
        raise ValueError('Literal SYSTEM required')
    return nodes[0], nodes[0].value.value


def patch_agent(source, rules):
    node, old = system_value(source)
    if BEGIN in old or END in old:
        raise ValueError('Knowledge already present; verify installed hashes')
    if rules.count(BEGIN) != 1 or rules.count(END) != 1 or rules.index(BEGIN) >= rules.index(END):
        raise ValueError('Invalid knowledge block')
    lines = source.splitlines(True)
    lines[node.lineno-1:node.end_lineno] = ['SYSTEM = '+repr(old+'\n\n'+rules)+'\n']
    result = ''.join(lines)
    compile(result, 'crypto_agent.py', 'exec')
    return result


def patch_worker(source):
    if source.count(NEEDLE) != 1:
        raise ValueError('Reviewed worker prompt changed')
    result = source.replace(NEEDLE, REPLACEMENT)
    compile(result, 'review_worker.py', 'exec')
    return result


def unpatch_agent(source, rules):
    node, loaded = system_value(source)
    suffix = '\n\n'+rules
    if not loaded.endswith(suffix): raise ValueError('Unexpected installed knowledge')
    lines = source.splitlines(True)
    lines[node.lineno-1:node.end_lineno] = ['SYSTEM = '+repr(loaded[:-len(suffix)])+'\n']
    return ''.join(lines)


def safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink refused')
    return path


def replace(path, raw, metadata=None):
    safe(path)
    mode, uid, gid = (metadata.st_mode & 0o777, metadata.st_uid, metadata.st_gid) if metadata else (0o644, 0, 0)
    fd, tmp = tempfile.mkstemp(prefix='.runner-knowledge-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            os.fchmod(f.fileno(), mode)
            os.fchown(f.fileno(), uid, gid)
            f.write(raw); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def apply_transaction(changes, writer=replace):
    originals = [(p, p.read_bytes() if p.exists() else None, p.stat() if p.exists() else None) for p, _ in changes]
    written = []
    try:
        for (path, raw), (_, old, meta) in zip(changes, originals):
            writer(path, raw, meta); written.append((path, old, meta, raw))
        for path, raw in changes:
            if path.read_bytes() != raw: raise ValueError('Postflight content mismatch')
    except Exception:
        for path, old, meta, candidate in reversed(written):
            if path.read_bytes() != candidate:
                raise ValueError('Concurrent write detected; preserve backup for manual recovery')
            if old is None: path.unlink()
            else: writer(path, old, meta)
        raise



def acquire_review_lock(lock, timeout=150, *, clock=time.monotonic, sleep=time.sleep, flock=fcntl.flock):
    """Wait on the existing inode; never replace the lock or interrupt its holder."""
    if not 0 <= timeout <= 150:
        raise ValueError('Lock timeout must be between 0 and 150 seconds')
    started = clock()
    while True:
        try:
            flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True, round(clock()-started, 3)
        except BlockingIOError:
            remaining = timeout-(clock()-started)
            if remaining <= 0:
                return False, round(clock()-started, 3)
            sleep(min(0.5, remaining))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hash', action='store_true')
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--expected-sha256')
    args = parser.parse_args()
    for name in FILES: safe(HERE/name)
    reviewed = bundle()
    if args.hash: print(reviewed); return
    if args.expected_sha256 != reviewed: raise ValueError('Reviewed bundle mismatch')
    subprocess.run(['/usr/bin/python3', '-m', 'unittest', 'discover', '-s', str(HERE), '-p', 'test_*.py'], check=True, timeout=30)
    from validate import validate_status
    status = validate_status(json.loads((HERE/'STATUS.json').read_text()))
    rules = (HERE/'COMPACT_RULES.md').read_text()
    safe(AGENT); safe(WORKER)
    agent_old, worker_old = AGENT.read_bytes(), WORKER.read_bytes()
    doc = AGENT.with_name('RUNNER_KNOWLEDGE.md')
    compact = AGENT.with_name('RUNNER_KNOWLEDGE_COMPACT.md')
    expected_worker = patch_worker((HERE/'review_worker.py').read_text()).encode()
    if digest(agent_old) != OLD_AGENT or digest(worker_old) != OLD_WORKER:
        _, loaded = system_value(agent_old.decode())
        if loaded.endswith('\n\n'+rules) and digest(unpatch_agent(agent_old.decode(), rules).encode())==OLD_AGENT and digest(worker_old)==digest(expected_worker) and safe(doc).exists() and safe(compact).exists() and doc.read_bytes()==(HERE/'AGENT_KNOWLEDGE.md').read_bytes() and compact.read_text()==rules:
            print(json.dumps({'installed': True, 'already_installed': True, 'bundle_sha256': reviewed, 'study_complete': False})); return
        raise ValueError('Installed source changed; review before patching')
    if any(safe(p).exists() for p in (doc, compact)): raise ValueError('Unexpected existing knowledge files')
    agent_new = patch_agent(agent_old.decode(), rules).encode()
    worker_new = patch_worker(worker_old.decode()).encode()
    report = dict(validated=True, installed=False, bundle_sha256=reviewed,
                  agent_source_sha256=digest(agent_new), worker_source_sha256=digest(worker_new),
                  conversational_prompt_integrated=True, review_prompt_integrated=True,
                  study_complete=False, verified_ranked_runners=status['verified_ranked_runners'],
                  scanner_changed=False, relay_resumed=False, weights_updated=False,
                  live_execution=False, telegram_messages_sent=0)
    if not args.install: print(json.dumps(report, sort_keys=True)); return
    if os.geteuid()!=0: raise ValueError('Owner root required for production code')
    # Existing worker lock prevents an in-flight review across the two-code swap.
    # Do not create a root-owned lock or change private state/config permissions.
    with safe(LOCK).open('r+') as lock:
        acquired, waited = acquire_review_lock(lock)
        report['lock_wait_seconds'] = waited
        if not acquired:
            report.update(status='review_busy_retry', production_changed=False)
            print(json.dumps(report, sort_keys=True))
            raise SystemExit(2)
        if AGENT.read_bytes()!=agent_old or WORKER.read_bytes()!=worker_old: raise ValueError('Source changed during validation')
        backup = Path(tempfile.mkdtemp(prefix='runner-knowledge-', dir='/opt/vivameda-operations'))
        backup.chmod(0o700)
        shutil.copy2(AGENT, backup/'crypto_agent.py'); shutil.copy2(WORKER, backup/'review_worker.py')
        apply_transaction([(doc, (HERE/'AGENT_KNOWLEDGE.md').read_bytes()),
                           (compact, rules.encode()), (AGENT, agent_new), (WORKER, worker_new)])
        report.update(installed=True, backup=str(backup), fresh_agent_processes_load_instructions=True,
                      next_review_process_loads_instructions=True, model_selection_quality_validated=False)
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
