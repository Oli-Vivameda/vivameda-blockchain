import base64
import copy
import json
import pathlib
import sqlite3
import sys
import tempfile
import unittest
from decimal import Decimal as D
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from common import canonical,digest,screening,PROTOCOL_SHA256,buy,sell,PLANS
from reserves import b58,authenticate,PUMP,SPL,SOL,USDC,ALPHABET
from exporter import readonly,collect
from replay import run,simulate,prepare,stats,markdown
from journal import Journal
from tickets import build,ingest,render
from delivery import flush,RateLimited,callback

ROOT=pathlib.Path(__file__).resolve().parents[1]
MINT=b58(bytes([5])*32);PAIR=b58(bytes([9])*32)
FROZEN=b58(bytes([11])*32)

def decode(s):
    n=0
    for c in s:n=n*58+ALPHABET.index(c)
    return b'\0'*(len(s)-len(s.lstrip('1')))+(n.to_bytes((n.bit_length()+7)//8,'big') if n else b'')

def proof(at=100,price='1',mint=MINT,pair=PAIR,quote=SOL):
    raw=bytearray(271);raw[:8]=bytes([241,154,109,4,17,177,109,188])
    addresses=[bytes([4])*32,decode(mint),decode(quote),bytes([6])*32,bytes([8])*32,bytes([10])*32]
    for i,a in enumerate(addresses):raw[11+32*i:43+32*i]=a
    def acct(kind,i):return {'owner':SPL,'executable':False,'data':{'parsed':{'type':kind,'info':i}}}
    x=D(100000);y=x*D(price);quote_price=D(100) if quote==SOL else D(1);qdec=9 if quote==SOL else 6
    mi=acct('mint',dict(isInitialized=True,decimals=6));lp=acct('mint',dict(mintAuthority=pair,freezeAuthority=None))
    base=acct('account',dict(mint=mint,owner=pair,state='initialized',tokenAmount={'amount':str(int(x*10**6)),'decimals':6}))
    qa=acct('account',dict(mint=quote,owner=pair,state='initialized',tokenAmount={'amount':str(int(y/quote_price*10**qdec)),'decimals':qdec}))
    return dict(mint=mint,pair=pair,chain='solana',observed_at=at,evidence_refs=['SYNTHETIC_FIXTURE_NOT_LIVE'],pool_address=pair,
                account_addresses=[mint,b58(addresses[3]),b58(addresses[4]),b58(addresses[5])],pool_response={'context':{'slot':10},'value':{'owner':PUMP,'executable':False,'data':[base64.b64encode(raw).decode(),'base64']}},
                accounts_response={'context':{'slot':10},'value':[mi,lp,base,qa]},quote_usd={'price':str(quote_price),'observed_at':at,'evidence_refs':['SYNTHETIC_PRICE']})

def review(at=100,mint=MINT,pair=PAIR):
    return dict(mint=mint,pair=pair,chain='solana',checked_at=at,checks={k:dict(status='PASS',observed_at=at,evidence_refs=['fixture']) for k in ['token_controls','liquidity_control','trading_mechanics']})

def case(alert=100,path=None):
    path=path or [(t,'1') for t in range(100,7601,60)]
    return dict(id='fixture-alert-'+str(alert),mint=MINT,decision_ts=alert,score=9,regime='CONTINUATION',symbol='TEST ONLY',created_ts=1700000000000,pair=PAIR,review=review(alert),
                snapshots=[dict(ts=t,pair=PAIR,price=float(p),liq=200000,mc=1000000) for t,p in path],reserves=[proof(t,p) for t,p in path])

def export(rows,mode='replay',now=100):
    return dict(schema='meme-desk-export-v1',mode=mode,exported_at=now,protocol_sha256=PROTOCOL_SHA256,frozen_membership_excluded=True,rows=rows)

class ReserveTests(unittest.TestCase):
    def test_authenticated_account_relationships(self):
        self.assertEqual(authenticate(proof(),MINT,PAIR,100,1)['x'],'100000')
    def test_boolean_not_proof(self):
        with self.assertRaises(ValueError):authenticate({'authenticated':True},MINT,PAIR,100,1)
    def test_vault_binding_rejected(self):
        p=proof();p['account_addresses'][2]='unrelated'
        with self.assertRaises(ValueError):authenticate(p,MINT,PAIR,100,1)
    def test_stale_and_future(self):
        for at in [-81,101]:
            with self.assertRaises(ValueError):authenticate(proof(at),MINT,PAIR,100,1)
    def test_wrong_mint_and_price(self):
        with self.assertRaises(ValueError):authenticate(proof(),FROZEN,PAIR,100,1)
        with self.assertRaises(ValueError):authenticate(proof(),MINT,PAIR,100,2)
    def test_non_cp_pool_rejected(self):
        p=proof();raw=bytearray(base64.b64decode(p['pool_response']['value']['data'][0]));raw[243]=1;p['pool_response']['value']['data'][0]=base64.b64encode(raw).decode()
        with self.assertRaises(ValueError):authenticate(p,MINT,PAIR,100,1)
    def test_constant_product_math_no_impact_double_count(self):
        x,y=D(100000),D(100000);q=buy(x,y)
        self.assertLess(q,10)
        self.assertAlmostEqual(sell(x-q,y+10,q),D(10))

class ReplayTests(unittest.TestCase):
    def execute(self,c,p='A'):
        ss,reason=prepare(c);self.assertIsNone(reason);return simulate(c,p,ss)
    def test_flat_net_negative_after_both_fees_network_impact(self):
        r=self.execute(case());self.assertTrue(r['resolved']);self.assertLess(D(r['net_pnl']),D('-.30'));self.assertEqual(r['legs'][0]['kind'],'time')
    def test_target_fills_first_observed_not_level(self):
        c=case(path=[(t,'1' if t<220 else '1.7') for t in range(100,7601,60)])
        r=self.execute(c);self.assertEqual(r['legs'][0]['snapshot_price'],'1.7');self.assertEqual(r['legs'][0]['kind'],'half_target');self.assertGreater(D(r['legs'][0]['threshold_overshoot']),0)
        self.assertEqual(len(r['legs']),2)
    def test_gap_down_stop_fills_observed(self):
        c=case(path=[(t,'1' if t<220 else '.5') for t in range(100,7601,60)])
        r=self.execute(c);self.assertEqual(r['legs'][0]['snapshot_price'],'0.5');self.assertEqual(r['legs'][0]['kind'],'stop');self.assertLess(D(r['net_pnl']),-5)
    def test_missing_entry(self):
        c=case();c['snapshots']=[s for s in c['snapshots'] if s['ts']==100 or s['ts']>340]
        self.assertFalse(self.execute(c)['resolved'])
    def test_gap_unresolved(self):
        c=case();c['snapshots']=[s for s in c['snapshots'] if not 220<=s['ts']<=400]
        self.assertEqual(self.execute(c)['unresolved_reason'],'snapshot_gap')
    def test_missing_reserves_not_liquidity_proxy(self):
        c=case();c['reserves']=[]
        self.assertEqual(self.execute(c)['unresolved_reason'],'authenticated_reserves_missing')
    def test_c_missing_120_exit_remains_unresolved(self):
        c=case();c['snapshots']=[s for s in c['snapshots'] if s['ts']<=4000]
        self.assertFalse(self.execute(c,'C')['resolved']);self.assertTrue(self.execute(c,'A')['resolved'])
    def test_no_screening_lookahead(self):
        c=case();c['review']=review(101)
        self.assertEqual(prepare(c)[1],'screening_stale')
    def test_background_reject_blocks(self):
        c=case();c['review']['checks']['developer_history']={'status':'REJECT'}
        self.assertEqual(prepare(c)[1],'screening_reject')
    def test_time_exit_strictly_after_deadline(self):
        r=self.execute(case());self.assertGreater(r['legs'][0]['time'],r['entry']['time']+2700)
    def test_partial_unresolved_not_counted_win(self):
        c=case(path=[(t,'1' if t<220 else '2') for t in range(100,7601,60)])
        c['reserves']=[p for p in c['reserves'] if p['observed_at']<280]
        r=self.execute(c);self.assertFalse(r['resolved']);self.assertTrue(r['legs']);self.assertEqual(stats([r])['resolved'],0)
    def test_best_five_and_all_splits(self):
        rows=[dict(resolved=True,net_pnl=str(i)) for i in range(1,8)]
        self.assertEqual(stats(rows)['excluding_best_5']['mean_net_pnl_usd'],'1.5')
        self.assertIsNone(stats(rows[:5])['excluding_best_5']['mean_net_pnl_usd'])
        agg,private=run(export([case()]));self.assertEqual(set(agg['plans']),set(PLANS));self.assertEqual(agg['plans']['A']['chronological_halves']['LATE']['case_count'],1)
        self.assertNotIn(MINT,markdown(agg));self.assertNotIn('snapshot_price',markdown(agg))
    def test_export_contract_and_conflicts(self):
        e=export([]);e['frozen_membership_excluded']=False
        with self.assertRaises(ValueError):run(e)
        c=case();c['snapshots'].append(dict(c['snapshots'][0],price=4))
        a,_=run(export([c]));self.assertEqual(a['eligible_cases'],0)

class ExportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'scanner.sqlite3'
        c=sqlite3.connect(self.path)
        c.executescript('''CREATE TABLE pl_predictions(mint TEXT,model_probability REAL); CREATE TABLE pl_results(mint TEXT,secret_outcome TEXT);
        CREATE TABLE v2_cases(id TEXT,mint TEXT,decision_ts INTEGER,source TEXT,score INTEGER,regime TEXT);
        CREATE TABLE launches(mint TEXT,symbol TEXT,created_ts INTEGER,pinned_pair TEXT);
        CREATE TABLE snapshots(mint TEXT,ts INTEGER,pair TEXT,price REAL,mc REAL,liq REAL);
        CREATE TABLE prealert_reviews(mint TEXT,checked_at INTEGER,review TEXT);''')
        c.execute('INSERT INTO pl_predictions VALUES(?,?)',(FROZEN,.99))
        for mint in [MINT,FROZEN]:
            c.execute('INSERT INTO v2_cases VALUES(?,?,?,?,?,?)',('case'+mint,mint,100,'ALERT',9,'CONTINUATION'))
            c.execute('INSERT INTO launches VALUES(?,?,?,?)',(mint,'test',1700000000000,PAIR))
            c.execute('INSERT INTO prealert_reviews VALUES(?,?,?)',(mint,100,canonical(review(100,mint))))
        c.commit();c.close();self.c=readonly(self.path)
    def tearDown(self):self.c.rollback();self.c.close();self.tmp.cleanup()
    def test_exclusion_before_export_private_and_public(self):
        e=collect(self.c,'replay',4000)
        self.assertEqual(len(e['rows']),1);self.assertNotIn(FROZEN,canonical(e));self.assertNotIn('model_probability',canonical(e))
    def test_forbidden_tables_and_prediction_columns_denied(self):
        for sql in ['SELECT * FROM pl_results','SELECT model_probability FROM pl_predictions','UPDATE launches SET symbol=\'bad\'']:
            with self.assertRaises(sqlite3.DatabaseError):self.c.execute(sql)
    def test_earliest_alert_not_later_favourable(self):
        e=collect(self.c,'replay',4000)
        self.assertEqual(e['rows'][0]['decision_ts'],100)
    def test_readonly_file_unchanged(self):
        import hashlib
        before=hashlib.sha256(self.path.read_bytes()).hexdigest();collect(self.c,'replay',4000)
        self.assertEqual(before,hashlib.sha256(self.path.read_bytes()).hexdigest())

class TicketTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=pathlib.Path(self.tmp.name)/'desk.sqlite3';self.j=Journal(self.path)
        self.c=case();self.c['snapshots']=[dict(ts=100,pair=PAIR,price=1,liq=200000,mc=1000000)];self.c['reserves']=[proof()]
    def tearDown(self):self.j.db.close();self.tmp.cleanup()
    def ticket(self,ident=None,now=100):
        c=copy.deepcopy(self.c)
        if ident:c['id']=ident
        return ingest(self.j,export([c],'tickets',now),now)
    def test_ticket_fields_and_no_replay_yet(self):
        t=self.ticket()[0];self.assertEqual(t['entry_ceiling'],'1.03');self.assertEqual(t['replay_a_regime'],'no replay yet');self.assertEqual(t['plan_a']['half_target'],'1.40');self.assertFalse(t['execution']);self.assertIn('jup.ag/swap/SOL-',render(t));self.assertLess(D(t['round_trip_cost_pct']),6)
    def test_duplicate_restart_chain(self):
        self.ticket();head=self.j.verify();self.ticket();self.assertEqual(self.j.verify(),head)
        self.j.db.close();self.j=Journal(self.path);self.assertEqual(len(self.j.state(100)['tickets']),1)
    def test_append_only_triggers(self):
        self.ticket()
        for query in ['DELETE FROM events','UPDATE events SET kind=\'x\'']:
            with self.assertRaises(sqlite3.IntegrityError):self.j.db.execute(query)
    def test_detect_privileged_tampering(self):
        self.ticket();self.j.db.execute('DROP TRIGGER immutable_update');self.j.db.execute("UPDATE events SET body='{}'")
        with self.assertRaises(ValueError):self.j.verify()
    def test_caps_and_low_liquidity(self):
        self.c['snapshots'][0]['liq']=24999
        self.assertEqual(self.ticket(),[])
        self.assertEqual(json.loads(self.j.db.execute('SELECT body FROM events').fetchone()[0])['reason'],'liquidity_below_25000')
    def test_high_cost_blocks(self):
        from tickets import select as original
        import tickets
        tickets.select=lambda *a,**kw:dict(x='200',y='200',observed_at=100,proof_hash='fixture')
        try:self.assertEqual(build(self.c,100,self.j.state(100))[1],'round_trip_cost_above_6pct')
        finally:tickets.select=original
    def test_three_taken_stops_new_tickets(self):
        for i in range(3):
            t=self.ticket(str(i))[0];self.j.button('press'+str(i),t['id'],'TAKEN',now=100)
        self.assertEqual(self.ticket('four'),[])
    def test_skip_reason_and_owner_callback(self):
        t=self.ticket()[0]
        with self.assertRaises(ValueError):callback(self.j,'a',t['id'],'TAKEN')
        self.assertIn('choices',callback(self.j,'a',t['id'],'SKIP',True,now=100))
        with self.assertRaises(ValueError):self.j.button('a',t['id'],'SKIP','random',100)
        self.assertTrue(self.j.button('a',t['id'],'SKIP','risk',100))
        self.assertFalse(self.j.button('b',t['id'],'TAKEN',now=100))
    def test_daily_review_only_and_lifetime_halt(self):
        t=self.ticket('first')[0];self.j.button('a',t['id'],'TAKEN',now=100);self.j.close('c',t['id'],'-15',now=100)
        t2=self.ticket('second')[0];self.assertTrue(t2['review_only']);self.j.button('b',t2['id'],'TAKEN',now=100);self.j.close('d',t2['id'],'-10',now=100)
        self.assertEqual(self.ticket('third'),[])
        self.j.reenable('owner','Reviewed cumulative limit',now=101)
        self.assertEqual(len(self.ticket('fourth')),1)
    def test_utc_daily_loss_resets_not_lifetime(self):
        t=self.ticket()[0];self.j.button('a',t['id'],'TAKEN',now=100);self.j.close('c',t['id'],'-15',now=100)
        self.assertEqual(self.j.state(86401)['daily_loss'],0);self.assertEqual(self.j.state(86401)['cumulative_loss'],15)
    def test_double_close_cannot_duplicate_pnl(self):
        t=self.ticket()[0];self.j.button('a',t['id'],'TAKEN',now=100);self.j.close('c',t['id'],'-5',now=100)
        with self.assertRaises(ValueError):self.j.close('d',t['id'],'-5',now=100)
        self.assertEqual(self.j.state(100)['cumulative_loss'],5)
    def test_missing_and_stale_reserves_no_ticket(self):
        self.c['reserves']=[];self.assertEqual(self.ticket(),[])
    def test_stale_source_and_snapshot(self):
        self.assertEqual(build(self.c,161,self.j.state(161))[1],'alert_too_old_or_future')
        self.assertEqual(build(self.c,131,self.j.state(131))[1],'stale_market_snapshot')
    def test_unknown_background_and_reject(self):
        self.c['review']['checks']['wallet_age']={'status':'UNKNOWN','reason':'not enough history'}
        t=self.ticket()[0];self.assertIn('wallet_age',t['unknown_checks'])
        self.c['review']['checks']['wallet_age']['status']='REJECT';self.c['id']='reject'
        self.assertEqual(self.ticket(),[])
    def test_delivery_disabled_without_destination(self):
        with self.assertRaises(ValueError):flush(self.j,None,{},100)
    def test_injected_transport_rate_limit_queue_age_no_network(self):
        t=self.ticket()[0]
        class MemoryOnlyTransport:
            calls=0;last_text=None
            def send(self,*args,**kwargs):
                self.calls+=1;self.last_text=args[1]
                if self.calls==1:raise RateLimited(60)
                return 'in-memory-test-receipt'
        tr=MemoryOnlyTransport();cfg={'destination':'fixture','destination_confirmed':True}
        self.assertEqual(flush(self.j,tr,cfg,100),[]);self.assertEqual(flush(self.j,tr,cfg,120),[]);self.assertEqual(tr.calls,1)
        self.assertEqual(flush(self.j,tr,cfg,170),[t['id']]);self.assertIn('LATE TICKET',tr.last_text)
        self.assertEqual(flush(self.j,tr,cfg,200),[])
    def test_export_contract_fails_closed(self):
        with self.assertRaises(ValueError):ingest(self.j,export([self.c],'tickets',0),100)


class IntegrationTests(unittest.TestCase):
    def test_preregistered_protocol_unchanged(self):
        import hashlib
        self.assertEqual(hashlib.sha256((ROOT/'REPLAY_PROTOCOL.md').read_bytes()).hexdigest(),PROTOCOL_SHA256)
    def test_service_shadow_end_to_end_and_restart(self):
        from service import Desk
        from exporter import atomic_write
        import contextlib,io
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td);cfg=json.loads((ROOT/'config.json').read_text())
            c=case();c['snapshots']=[dict(ts=100,pair=PAIR,price=1,liq=200000,mc=1000000)];c['reserves']=[proof()]
            atomic_write(p/'input.json',export([c],'tickets',100))
            d=Desk(p/'state',cfg)
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(len(d.poll(p/'input.json',100)),1)
            head=d.j.verify();d.j.db.close();d=Desk(p/'state',cfg)
            with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(d.poll(p/'input.json',100),[])
            self.assertEqual(d.j.verify(),head);d.j.db.close()
    def test_service_rejects_direct_network_configuration(self):
        from service import Desk
        with tempfile.TemporaryDirectory() as td:
            cfg=json.loads((ROOT/'config.json').read_text());cfg['network_calls_from_desk']=True
            with self.assertRaises(ValueError):Desk(td,cfg)
    def test_missing_export_report_not_live_dry_run(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            r=subprocess.run([sys.executable,str(ROOT/'service.py'),'once','--state-dir',td,'--input',td+'/missing.json'],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            receipt=json.loads((pathlib.Path(td)/'shadow_receipt.json').read_text())
            self.assertEqual(receipt['valid_export_polls'],0);self.assertIn('BLOCKED',receipt['status'])
    def test_no_sender_is_not_a_confirmed_destination(self):
        from delivery import load_confirmed
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'delivery.json';p.write_text('{"destination_confirmed":false}')
            with self.assertRaises(ValueError):load_confirmed(p)
    def test_authenticated_reserve_liquidity_floor(self):
        c=case();c['snapshots']=[dict(ts=100,pair=PAIR,price=.1,liq=200000,mc=1000000)];c['reserves']=[proof(100,'.1')]
        with tempfile.TemporaryDirectory() as td:
            j=Journal(pathlib.Path(td)/'j.sqlite3')
            self.assertEqual(build(c,100,j.state(100))[1],'authenticated_liquidity_below_25000');j.db.close()
    def test_global_rate_limit_blocks_other_tickets(self):
        with tempfile.TemporaryDirectory() as td:
            j=Journal(pathlib.Path(td)/'j.sqlite3')
            c=case();c['snapshots']=[dict(ts=100,pair=PAIR,price=1,liq=200000,mc=1000000)];c['reserves']=[proof()]
            c2=copy.deepcopy(c);c2['id']='other'
            ingest(j,export([c,c2],'tickets',100),100)
            class Fake:
                count=0
                def send(self,*a,**kw):self.count+=1;raise RateLimited(60)
            t=Fake();cfg={'destination_confirmed':True,'destination':'fixture'}
            flush(j,t,cfg,100);flush(j,t,cfg,120)
            self.assertEqual(t.count,1);j.db.close()
    def test_protocol_export_file_uri_path_with_query_characters(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'file?other.sqlite';c=sqlite3.connect(p);c.execute('CREATE TABLE launches(mint TEXT)');c.close()
            c=readonly(p);self.assertEqual(c.execute('SELECT mint FROM launches').fetchall(),[]);c.rollback();c.close()


class OwnerBoundaryTests(unittest.TestCase):
    def test_owner_snapshot_and_tamper_refusal(self):
        import hashlib,subprocess
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)
            for name in ['owner.py']:(root/name).write_bytes((ROOT/name).read_bytes())
            (root/'replay.py').write_text("import pathlib; print('SNAPSHOT_ONLY' if pathlib.Path(__file__).parent.name.startswith('vivameda-meme-desk-reviewed-') else 'BAD')")
            data={'sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['owner.py','replay.py']}}
            (root/'BUNDLE.json').write_text(canonical(data));sha=hashlib.sha256((root/'BUNDLE.json').read_bytes()).hexdigest()
            args=[sys.executable,str(root/'owner.py'),'--expected-bundle',sha,'replay']
            good=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(good.returncode,0,good.stderr);self.assertIn('SNAPSHOT_ONLY',good.stdout)
            (root/'replay.py').write_text("print('UNREVIEWED')")
            bad=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(bad.returncode,0);self.assertNotIn('UNREVIEWED',bad.stdout)
    def test_verifier_detects_wrong_digest_and_unsafe_path(self):
        import verify,hashlib
        old=verify.__file__
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);verify.__file__=str(root/'verify.py')
            try:
                (root/'BUNDLE.json').write_text(canonical({'sha256':{'../outside':'bad'}}))
                sha=hashlib.sha256((root/'BUNDLE.json').read_bytes()).hexdigest()
                with self.assertRaises(ValueError):verify.verify('wrong')
                with self.assertRaises(ValueError):verify.verify(sha)
            finally:verify.__file__=old
    def test_installer_refuses_nonroot_without_writes(self):
        import install
        from unittest.mock import patch
        with patch('sys.argv',['install.py','--expected-bundle','test']),patch.object(install.os,'geteuid',return_value=994):
            with self.assertRaisesRegex(SystemExit,'Owner root'):install.main()


class RestrictiveOwnerUmaskTest(unittest.TestCase):
    def test_service_user_can_read_staged_release_under_umask_077(self):
        import install,os,hashlib,stat
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td)/'source';root.mkdir();(root/'tests').mkdir();(root/'tests/example.py').write_text('reviewed')
            b={'sha256':{'tests/example.py':hashlib.sha256(b'reviewed').hexdigest()}};raw=canonical(b).encode()
            previous=os.umask(0o077)
            try:install.stage_release(root,pathlib.Path(td)/'release',raw,b)
            finally:os.umask(previous)
            self.assertEqual(stat.S_IMODE((pathlib.Path(td)/'release/tests').stat().st_mode),0o755)
            self.assertEqual(stat.S_IMODE((pathlib.Path(td)/'release/BUNDLE.json').stat().st_mode),0o644)

if __name__=='__main__':unittest.main()
