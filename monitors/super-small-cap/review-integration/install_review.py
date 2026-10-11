"""Owner activation of the isolated reviewed-only third-trigger dispatch."""
import argparse,hashlib,json,os,pwd,shutil,subprocess,tempfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
APP=Path('/opt/vivameda-super-small-cap-review')
STATE=Path('/var/lib/vivameda-super-small-cap')
AGENT=Path('/opt/vivameda-crypto-runtime/crypto_agent.py')
EXPECTED_AGENT='44f1368e772f7b27724665ebe06cf34aa0a0a95d3f849a98bdf44f92d21f39c3'
HELPER_ROOT=Path('/opt/vivameda-wallet-intelligence')
FILES=('review_worker.py','classifier.py','AGENT_REVIEW_RULES.md','helper_hashes.json','test_review.py','collector_fixture.py','probe_model.py','install_review.py','test_install_review.py','vivameda-super-small-cap-review.service','vivameda-super-small-cap-review.timer')
UNITS=('vivameda-super-small-cap-review.service','vivameda-super-small-cap-review.timer')
PREVIOUS_BUNDLE='5a43bb7cef70edb22ee8dc3709591f43f194eb225e3baecac918610740dae87f'
PREVIOUS_FILES={'review_worker.py': 'e048a31f25e21a7aeb93b24eadab7d0f235832074d79bcdfeda8e8c8f0f33273', 'classifier.py': '89d523e46c5a364ef3efb9aa97c76e78f294296d4e7b77d6a161b636c5a13129', 'AGENT_REVIEW_RULES.md': 'ba6dbb80f1bc0be0eff0999cbd1a538df2df54b036def5241ce0497ed86e6c91', 'helper_hashes.json': 'c3672d9475909f8863155b0d8fe7172e8f8c697561c48b9b06aeb9ff97fe8f2a', 'test_review.py': '789102cfac427934e5a515820069b61d1bcc75663d7af6a01e7e94054dcf3cb5', 'collector_fixture.py': '7e225095d08bd0ecc5ea6bbd841de3d5c1b3c9723719e126b252657a55456aea', 'probe_model.py': '7bf87f5c13719ccf0e7263b1f865e34f64a458d7fea0619612790845866cfb92', 'install_review.py': 'a54a42887f8d12074c8a9d3c3b255d8343472c9df67fa2c4bae411e72b6d398f', 'test_install_review.py': 'a59832c677a96b9b2a0bfce01442dc2b10ee058a3ab5909cfb61afd40742cb12', 'vivameda-super-small-cap-review.service': 'df3f71d0c5bae583762867a10e1b94e1da50ceaa7755e96e1ae64649ec8c5629', 'vivameda-super-small-cap-review.timer': '370627d6942df8a6d924ff04befc0f92fb39a32184aab3713f343e7c94068e7d'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def bundle():return hashlib.sha256(b''.join(n.encode()+b'\0'+(HERE/n).read_bytes()+b'\0' for n in FILES)).hexdigest()
def safe(p):
    if any(x.is_symlink() for x in [p,*p.parents]):raise ValueError('symlink target refused')
def atomic(path,text,uid=0,gid=0,mode=0o600):
    safe(path);fd,tmp=tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd,'w') as f:
            os.fchmod(f.fileno(),mode);os.fchown(f.fileno(),uid,gid);f.write(text);f.flush();os.fsync(f.fileno())
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
def command(argv,timeout=30):return subprocess.run(argv,check=True,capture_output=True,text=True,timeout=timeout)
def runtime_directory(path):
    safe(path);path.mkdir(mode=0o755,exist_ok=True);path.chmod(0o755)
def installed_source_hashes(marker_bundle,delivery_enabled):
    if marker_bundle==bundle():return {n:sha(HERE/n) for n in FILES}
    if marker_bundle==PREVIOUS_BUNDLE and delivery_enabled is False:return PREVIOUS_FILES
    raise ValueError('unexpected review installation')
def protected_paths():
    return [AGENT,Path('/opt/vivameda-super-small-cap/collector.py'),Path('/opt/vivameda-super-small-cap/classifier.py'),
            Path('/opt/vivameda-100x-watchlist/notifier.py'),Path('/opt/vivameda-100x-watchlist/research.py'),
            Path('/opt/vivameda-crypto-early-scout/early_scout.py'),Path('/opt/vivameda-crypto-early-scout/scout_learning_v2.py'),
            *[Path('/etc/systemd/system')/n for n in ['vivameda-super-small-cap.service','vivameda-super-small-cap.timer','vivameda-100x-watchlist.service','vivameda-100x-watchlist.timer']]]
def verify_sources(expected):
    for p,h in expected.items():
        safe(Path(p))
        if sha(Path(p))!=h:raise ValueError('protected source changed: '+str(p))
def main(argv=None):
    os.umask(0o077);p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hash',action='store_true');p.add_argument('--install',action='store_true');p.add_argument('--expected-sha256');a=p.parse_args(argv)
    if a.hash:print(bundle());return
    if a.expected_sha256!=bundle():raise ValueError('reviewed bundle mismatch')
    for n in FILES:
        safe(HERE/n)
        if n.endswith('.py'):compile((HERE/n).read_text(),n,'exec')
    command(['/usr/bin/python3','-m','unittest','discover','-s',str(HERE),'-p','test_*.py'])
    command(['systemd-analyze','verify',*[str(HERE/n) for n in UNITS]])
    if not a.install:print(json.dumps({'validated':True,'installed':False,'bundle_sha256':bundle()}));return
    if os.geteuid()!=0:raise ValueError('owner root activation required')
    for target in [APP,STATE,AGENT,STATE/'review_config.json',STATE/'capture.sqlite',*[Path('/etc/systemd/system')/n for n in UNITS]]:safe(target)
    if sha(AGENT)!=EXPECTED_AGENT:raise ValueError('installed agent changed; review current source first')
    if not (STATE/'capture.sqlite').is_file():raise ValueError('third collector must be installed first')
    hashes=json.loads((HERE/'helper_hashes.json').read_text())
    for n,h in hashes.items():
        safe(HELPER_ROOT/n)
        if sha(HELPER_ROOT/n)!=h:raise ValueError('screening helper changed: '+n)
    frozen={str(p):sha(p) for p in protected_paths()}
    config=STATE/'review_config.json';marker=APP/'installed_bundle.json'
    if APP.exists():
        if not marker.is_file():raise ValueError('unexpected review installation')
        enabled=json.loads(config.read_text()).get('telegram_delivery_enabled') if config.exists() else None
        expected=installed_source_hashes(json.loads(marker.read_text()).get('bundle_sha256'),enabled)
        for n,h in expected.items():
            safe(APP/n)
            if sha(APP/n)!=h:raise ValueError('review source changed')
        for n,h in hashes.items():
            if sha(APP/n)!=h:raise ValueError('copied screening source changed')
        if config.exists() and json.loads(config.read_text()).get('telegram_delivery_enabled'):
            command(['systemctl','is-active','--quiet',UNITS[1]],10)
            print(json.dumps({'installed':True,'already_installed':True,'bundle_sha256':bundle(),'telegram_delivery_enabled':True,'independent_review_producer_enabled':True,'live_execution':False}));return
    elif any((Path('/etc/systemd/system')/n).exists() for n in UNITS) or config.exists():raise ValueError('unexpected review config or units')
    account=pwd.getpwnam('vivameda-scout');backup=Path(tempfile.mkdtemp(prefix='super-small-cap-review-',dir='/opt/vivameda-operations'));backup.chmod(0o700)
    previous=config.read_text() if config.exists() else None
    if previous is not None:(backup/'review_config.json').write_text(previous)
    (backup/'protected_source_hashes.json').write_text(json.dumps(frozen,sort_keys=True))
    cfg={'policy':'crypto-super-small-cap-v1','mode':'REVIEW_ALERT','deadline_ts':None,'telegram_delivery_enabled':False,'independent_review_producer_enabled':True,'live_execution':False,'activation_ts':int(__import__('time').time()),'bundle_sha256':bundle()}
    try:
        runtime_directory(APP)
        for n in FILES:
            shutil.copyfile(HERE/n,APP/n);(APP/n).chmod(0o644)
        for n in hashes:
            shutil.copyfile(HELPER_ROOT/n,APP/n);(APP/n).chmod(0o644)
        atomic(marker,json.dumps({'bundle_sha256':bundle()}),mode=0o644)
        for n in UNITS:shutil.copyfile(HERE/n,Path('/etc/systemd/system')/n);(Path('/etc/systemd/system')/n).chmod(0o644)
        atomic(config,json.dumps(cfg,sort_keys=True)+'\n',account.pw_uid,account.pw_gid)
        # Runtime permissions, mint-only exclusion inventory, model schema, and screening imports checked as the actual service user.
        probe=json.loads(command(['runuser','-u','vivameda-scout','--','/usr/bin/python3',str(APP/'probe_model.py')],130).stdout)
        if probe.get('model_schema_probe')!='passed':raise ValueError('model probe failed')
        command(['runuser','-u','vivameda-scout','--','/usr/bin/python3','-c',"import sys;sys.path.insert(0,"+repr(str(APP))+");import review_worker as w;import full_screening;assert w.protected_mints() is not None;w.read_json(w.SCOUT/'credentials.json');print('runtime access verified')"],15)
        command(['systemctl','daemon-reload'],20)
        command(['systemctl','start',UNITS[0]],160)
        first=json.loads((STATE/'review_status.json').read_text())
        if first.get('status') not in ('waiting','assessed') or first.get('telegram_messages_sent')!=0:raise ValueError('dry delivery postflight failed')
        verify_sources(frozen)
        cfg['telegram_delivery_enabled']=True;atomic(config,json.dumps(cfg,sort_keys=True)+'\n',account.pw_uid,account.pw_gid)
        command(['systemctl','enable','--now',UNITS[1]],20)
        command(['systemctl','is-active','--quiet',UNITS[1]],10)
        verify_sources(frozen)
    except Exception:
        subprocess.run(['systemctl','disable','--now',UNITS[1]],capture_output=True,timeout=20)
        subprocess.run(['systemctl','stop',UNITS[0]],capture_output=True,timeout=20)
        if previous is not None:atomic(config,previous,account.pw_uid,account.pw_gid)
        else:
            cfg['telegram_delivery_enabled']=False;atomic(config,json.dumps(cfg,sort_keys=True)+'\n',account.pw_uid,account.pw_gid)
        raise
    print(json.dumps({'installed':True,'bundle_sha256':bundle(),'backup':str(backup),'mode':'REVIEW_ALERT','deadline_ts':None,'independent_review_producer_enabled':True,'telegram_delivery_enabled':True,'same_existing_bot_and_chat':True,'existing_trigger_sources_unchanged':True,'interactive_agent_source_unchanged':True,'weights_updated':False,'live_execution':False,'model_schema_probe':probe,'first_dry_delivery_run':first,'first_real_candidate_delivery_verified':False},sort_keys=True))
if __name__=='__main__':main()
