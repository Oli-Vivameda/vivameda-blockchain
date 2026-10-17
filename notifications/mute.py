"""Notification-only source transformations. Never reads credentials or live data."""
import ast
import hashlib

CHANGED={'pool':{'drain'},'moves':{'run'},'watch':{'notify'},'fire':{'run'},'prediction':{'dispatch','startup'}}
def sha(data):return hashlib.sha256(data).hexdigest()
def replace_once(source,old,new):
    if source.count(old)!=1:raise ValueError('notification_source_shape_changed')
    return source.replace(old,new,1)
def body(source,name,code):
    tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name]
    if len(nodes)!=1:raise ValueError('notification_function_shape_changed:'+name)
    n=nodes[0]
    if n.decorator_list:raise ValueError('unexpected_notification_decorator')
    # Keep the signature and all surrounding source bytes exactly as they were.
    lines=source.splitlines(keepends=True);first=n.body[0].lineno-1
    if first==n.lineno-1:raise ValueError('inline_notification_function_not_supported')
    return ''.join(lines[:first])+code+''.join(lines[n.end_lineno:])
def rewrite(kind,source):
    if kind=='pool':
        source=body(source,'drain', '''    # Owner Telegram allowlist: this auxiliary pool route is muted.
    store.db.execute("UPDATE outbox SET status='expired' WHERE status='pending' AND expires<=?",(now,))
    store.db.execute("UPDATE outbox SET status='suppressed_owner',message_id=NULL WHERE status='pending'")
    store.commit()
''')
    elif kind=='moves':
        start=source.index("        if state.get('setup_digest') != digest:")
        end=source.index('        atomic(path,state)',start)
        source=source[:start]+"        if state.get('setup_digest') != digest:\n            report['setup_notification']='suppressed_owner'\n"+source[end:]
        start=source.index('                if event:');end=source.index("                item.pop('provider_retry_at'",start)
        source=source[:start]+"                if event:\n                    report['products'][product]['notification']='suppressed_owner'\n"+source[end:]
    elif kind=='watch':
        n=next((n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef)and n.name=='notify'),None)
        if n is None:raise ValueError('watch_notify_missing')
        # A notification helper containing capture/file/SQL writes needs its own
        # reviewed migration; do not silently remove observation work.
        denied={'open','execute','executemany','executescript','commit','write','write_text','write_bytes','writerow','save','atomic'}
        for call in ast.walk(n):
            if isinstance(call,ast.Call):
                name=call.func.id if isinstance(call.func,ast.Name)else call.func.attr if isinstance(call.func,ast.Attribute)else ''
                if name in denied:raise ValueError('watch_notify_contains_state_write_requires_review')
        source=body(source,'notify',"    print('TELEGRAM_SUPPRESSED_OWNER: auxiliary watchlist',flush=True)\n    return False\n")
    elif kind=='fire':
        start=source.index("        text=message(row,now,assessment)\n")
        end=source.index("    atomic(state/'status.json',report);return report",start)
        source=source[:start]+"        # Keep research evidence; record suppression without a send attempt.\n        report['state']='suppressed_owner';report['candidate_messages_suppressed']=1\n        break\n"+source[end:]
    elif kind=='prediction':
        source=body(source,'dispatch', '''    now=time.time() if now is None else now
    result={'sent':0,'failed':0,'deduplicated':0,'eligible_groups':None,
            'generated_at':now,'live_execution':False,'state':'suppressed_owner'}
    s.write_json(root,'telegram_latest.json',result)
    return result
''')
        source=body(source,'startup',"    return {'startup_sent':False,'state':'suppressed_owner'}\n")
    else:raise ValueError('unknown_notification_route')
    compile(source,'notification-candidate.py','exec');return source

def patch(kind,source,expected_sha256):
    raw=source.encode()
    if sha(raw)!=expected_sha256:
        # Idempotency is handled by the installer receipt, not by guessing source.
        raise ValueError('installed_source_changed:'+kind)
    candidate=rewrite(kind,source)
    old=ast.parse(source);new=ast.parse(candidate)
    unchanged=lambda tree:[ast.dump(n,include_attributes=False)for n in tree.body if not(isinstance(n,ast.FunctionDef)and n.name in CHANGED[kind])]
    if unchanged(old)!=unchanged(new):raise ValueError('non_notification_source_changed')
    return candidate
