"""Owner-reviewed third shadow trigger and additive agent instructions."""
import argparse, ast, hashlib, json, os, pwd, shutil, subprocess, tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
APP=Path('/opt/vivameda-super-small-cap');STATE=Path('/var/lib/vivameda-super-small-cap')
AGENT=Path('/opt/vivameda-crypto-runtime/crypto_agent.py')
OLD='68f7891f089a35c25e284c78d2ca7475b888d21c24ab1afb3cf3b3e98d9c1cec'
FILES=('classifier.py','collector.py','AGENT_RULES.md','test_trigger.py','install.py','test_install.py','vivameda-super-small-cap.service','vivameda-super-small-cap.timer')
MARKER='Vivameda super-small-cap trigger v1'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bundle():return hashlib.sha256(b''.join(n.encode()+b'\0'+(HERE/n).read_bytes()+b'\0' for n in FILES)).hexdigest()
def patch(source,rules):
    nodes=[n for n in ast.parse(source).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SYSTEM' for t in n.targets)]
    if len(nodes)!=1 or not isinstance(nodes[0].value,ast.Constant) or not isinstance(nodes[0].value.value,str):raise ValueError('literal SYSTEM required')
    n=nodes[0]
    if MARKER in n.value.value:raise ValueError('already installed')
    lines=source.splitlines(True);lines[n.lineno-1:n.end_lineno]=['SYSTEM = '+repr(n.value.value+'\n\n'+rules)+'\n']
    result=''.join(lines);compile(result,'crypto_agent.py','exec');return result
def replace(path,raw,meta):
    fd,tmp=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:
            os.fchmod(f.fileno(),meta.st_mode&0o777);os.fchown(f.fileno(),meta.st_uid,meta.st_gid);f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def main():
    p=argparse.ArgumentParser();p.add_argument('--hash',action='store_true');p.add_argument('--install',action='store_true');p.add_argument('--expected-sha256');a=p.parse_args()
    if a.hash:print(bundle());return
    if a.expected_sha256!=bundle():raise ValueError('reviewed bundle mismatch')
    for n in FILES:
        if (HERE/n).is_symlink():raise ValueError('source symlink')
        if n.endswith('.py'):compile((HERE/n).read_text(),n,'exec')
    subprocess.run(['/usr/bin/python3','-m','unittest','discover','-s',str(HERE),'-p','test_*.py'],check=True,timeout=30)
    if not a.install:print(json.dumps({'validated':True,'installed':False,'bundle_sha256':bundle()}));return
    if os.geteuid()!=0:raise ValueError('owner root required')
    units=[Path('/etc/systemd/system')/n for n in FILES if n.endswith(('.service','.timer'))]
    for target in [APP,STATE,AGENT,*units]:
        if any(p.is_symlink() for p in [target,*target.parents]):raise ValueError('target symlink')
    if APP.exists() or STATE.exists() or any(p.exists() for p in units):raise ValueError('unexpected third-trigger installation; review first')
    if sha(AGENT)!=OLD:raise ValueError('installed agent changed; review first')
    # Freeze existing trigger sources and unit bytes; never stop or edit their services.
    protected=[Path('/opt/vivameda-100x-watchlist/notifier.py'),Path('/opt/vivameda-100x-watchlist/research.py'),
               Path('/opt/vivameda-crypto-early-scout/early_scout.py'),Path('/opt/vivameda-crypto-early-scout/scout_learning_v2.py'),
               Path('/etc/systemd/system/vivameda-100x-watchlist.service'),Path('/etc/systemd/system/vivameda-100x-watchlist.timer')]
    frozen={str(p):sha(p) for p in protected};account=pwd.getpwnam('vivameda-scout')
    backup=Path(tempfile.mkdtemp(prefix='super-small-cap-',dir='/opt/vivameda-operations'));backup.chmod(0o700)
    shutil.copy2(AGENT,backup/'crypto_agent.py');source=AGENT.read_text();meta=AGENT.stat();new=patch(source,(HERE/'AGENT_RULES.md').read_text());changed=False
    try:
        APP.mkdir(mode=0o755);STATE.mkdir(mode=0o700);os.chown(STATE,account.pw_uid,account.pw_gid)
        for n in ['classifier.py','collector.py','AGENT_RULES.md']:
            shutil.copyfile(HERE/n,APP/n);(APP/n).chmod(0o644)
        for unit in units:shutil.copyfile(HERE/unit.name,unit);unit.chmod(0o644)
        subprocess.run(['systemd-analyze','verify',*[str(p) for p in units]],check=True,capture_output=True,timeout=20)
        if sha(AGENT)!=OLD:raise ValueError('concurrent agent change')
        replace(AGENT,new.encode(),meta);changed=True
        subprocess.run(['systemctl','daemon-reload'],check=True,timeout=20)
        subprocess.run(['systemctl','start','vivameda-super-small-cap.service'],check=True,timeout=30)
        first=json.loads((STATE/'status.json').read_text())
        if first.get('mode')!='SHADOW' or first.get('telegram_messages_sent')!=0:raise ValueError('shadow postflight')
        if any(sha(Path(p))!=h for p,h in frozen.items()):raise ValueError('existing source integrity changed')
        subprocess.run(['systemctl','enable','--now','vivameda-super-small-cap.timer'],check=True,timeout=20)
        subprocess.run(['systemctl','is-active','--quiet','vivameda-super-small-cap.timer'],check=True,timeout=10)
    except Exception:
        subprocess.run(['systemctl','disable','--now','vivameda-super-small-cap.timer'],capture_output=True,timeout=20)
        subprocess.run(['systemctl','stop','vivameda-super-small-cap.service'],capture_output=True,timeout=20)
        if changed and sha(AGENT)==hashlib.sha256(new.encode()).hexdigest():replace(AGENT,source.encode(),meta)
        # Preserve captured evidence and failed installation for diagnosis; no automatic history deletion.
        raise
    print(json.dumps({'installed':True,'mode':'SHADOW','trigger':'SUPER_SMALL_CAP','policy':'crypto-super-small-cap-v1',
      'bundle_sha256':bundle(),'agent_source_sha256':sha(AGENT),'backup':str(backup),'deadline_ts':None,
      'existing_trigger_sources_unchanged':True,'existing_trigger_configuration_changed':False,'first_run':first,
      'fresh_agent_processes_load_instructions':True,'independent_review_producer_enabled':False,
      'telegram_delivery_enabled':False,'weights_updated':False,'live_execution':False},sort_keys=True))
if __name__=='__main__':main()
