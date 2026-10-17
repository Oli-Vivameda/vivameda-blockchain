import base64
import copy
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_lane import facts,NOW
from core import *
from pump import *
from sources import Collector,SourceUnavailable
from service import Runner,volume_report
from install import units
from verify import verify
from transport import configuration

def key(n):return b58(bytes([n])*32)
def text(s):return struct.pack('<I',len(s.encode()))+s.encode()
def u64(n):return struct.pack('<Q',n)
MINT=key(1);USER=key(2);CURVE=key(3)

def account(creation,real=700,complete=0):
    raw=bytes([23,183,248,55,96,216,172,96])+b''.join(u64(n) for n in (1100,30,real,10,1000))+bytes([complete])+b58decode(creation['creator'])+b'\x00'
    return dict(owner=PUMP,executable=False,data=[base64.b64encode(raw).decode(),'base64'])

def tx_instruction(name,values=None,data=None):
    pm,_,_=maps();m=next(x for x in pm.values() if x['name']==name);values=values or {}
    return dict(programId=PUMP,accounts=[values.get(n,key(4)) for n in m['accounts']],data=b58(bytes(m['discriminator'])+(data or b'')))

def tx(ixs,events=(),error=None):
    logs=['Program '+PUMP+' invoke [1]']+['Program data: '+base64.b64encode(e).decode() for e in events]+['Program '+PUMP+' success']
    return dict(slot=100,blockTime=NOW,transaction=dict(message=dict(accountKeys=[dict(pubkey=USER,signer=True)],instructions=ixs)),meta=dict(err=error,logMessages=logs,innerInstructions=[]))

class Parser(unittest.TestCase):
    def test_base58_roundtrip(self):
        for data in (b'\0'*32,bytes(range(32)),b'\0abc'):self.assertEqual(b58decode(b58(data)),data)
    def test_base58_nonalphabet(self):
        with self.assertRaises(ValueError):b58decode('0OIl')
    def test_truncated_borsh(self):
        with self.assertRaises(EvidenceError):Reader(b'1').u64()
    def test_creation_authenticated(self):
        _,_,e=maps();payload=e['CreateEvent']+text('DEMO')+text('D')+text('https://example.org/meta')+b58decode(MINT)+b58decode(CURVE)+b58decode(USER)+b58decode(USER)+struct.pack('<q',NOW)+u64(1100)+u64(30)+u64(800)+u64(1000)
        ix=tx_instruction('create',dict(mint=MINT,user=USER,bonding_curve=CURVE),text('DEMO')+text('D')+text('https://example.org/meta')+b58decode(USER))
        out=decode_tx(tx([ix],[payload]),MINT,'sig');self.assertEqual(out['creation']['initial_curve_tokens'],800);self.assertEqual(out['creation']['creator'],USER)
    def test_creation_not_signer_rejected(self):
        ix=tx_instruction('create',dict(mint=MINT,user=USER,bonding_curve=CURVE),text('D')+text('D')+text('https://example.org')+b58decode(USER));value=tx([ix]);value['transaction']['message']['accountKeys'][0]['signer']=False
        with self.assertRaises(EvidenceError):decode_tx(value,MINT,'s')
    def trade(self,qty=100,sol=10,stamp=NOW):
        _,_,e=maps();payload=e['TradeEvent']+b58decode(MINT)+u64(sol)+u64(qty)+b'\x01'+b58decode(USER)+struct.pack('<q',stamp)
        ix=tx_instruction('buy',dict(mint=MINT,user=USER),u64(qty)+u64(sol));return tx([ix],[payload])
    def test_successful_economic_buy(self):self.assertEqual(decode_tx(self.trade(),MINT,'s')['trades'][0]['user'],USER)
    def test_zero_quote_rejected(self):
        with self.assertRaises(EvidenceError):decode_tx(self.trade(sol=0),MINT,'s')
    def test_trade_time_mismatch(self):
        with self.assertRaises(EvidenceError):decode_tx(self.trade(stamp=NOW-31),MINT,'s')
    def test_missing_trade_event_rejected(self):
        t=self.trade();t['meta']['logMessages']=[]
        with self.assertRaises(EvidenceError):decode_tx(t,MINT,'s')
    def test_spoofed_log_rejected(self):
        t=self.trade();t['meta']['logMessages'][0]='Program '+key(10)+' invoke [1]'
        with self.assertRaises(EvidenceError):decode_tx(t,MINT,'s')
    def test_duplicate_log_dedup(self):
        t=self.trade();t['meta']['logMessages'].insert(2,t['meta']['logMessages'][1]);self.assertEqual(len(decode_tx(t,MINT,'s')['trades']),1)
    def test_unrecognized_instruction_unknown(self):
        with self.assertRaises(EvidenceError):decode_tx(tx([dict(programId=PUMP,accounts=[MINT],data=b58(b'unknown!'))]),MINT,'s')
    def test_curve_progress_and_owner(self):
        c=dict(creator=USER,initial_supply=1000,initial_curve_tokens=800);a=account(c);self.assertEqual(number(curve(a,MINT,c)['progress_pct']),D('12.5'))
        a['owner']=key(9)
        with self.assertRaises(EvidenceError):curve(a,MINT,c)
    def test_curve_supply_mismatch_rejected(self):
        c=dict(creator=USER,initial_supply=999,initial_curve_tokens=800)
        with self.assertRaises(EvidenceError):curve(account(c),MINT,c)

class Census(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.collector=Collector(Path(self.tmp.name)/'cache')
        self.creation=dict(creator=USER,mint=MINT,curve=CURVE,slot=100,created_at=NOW-600,uri='https://example.org/meta',signature='create',initial_supply=1000,initial_curve_tokens=800)
        users=[key(i+10) for i in range(30)]
        trades=[dict(user=u,side='buy',slot=103 if i==0 else 110+i,at=NOW-301 if i<20 else NOW-1) for i,u in enumerate(users)]
        self.rows=[dict(trades=trades,creation=self.creation,migration=None)]
        def item(owner,amount):return dict(account=dict(owner=SPL,data=dict(parsed=dict(type='account',info=dict(mint=MINT,owner=owner,tokenAmount=dict(amount=str(amount),decimals=6))))))
        self.census=dict(context=dict(slot=200),value=[item(CURVE,700),item(USER,20),item(key(5),10)]+[item(u,9) for u in users])
        mint=dict(owner=SPL,data=dict(parsed=dict(info=dict(supply='1000',decimals=6,isInitialized=True,mintAuthority=None,freezeAuthority=None))))
        self.market=dict(context=dict(slot=200),value=[mint,account(self.creation)])
    def tearDown(self):self.collector.cache.close();self.tmp.cleanup()
    def enrich(self):
        def rpc(method,params):
            if method=='getBlocks':return [100,103,104]
            if method=='getMultipleAccounts':return self.market
            if method=='getProgramAccounts':return self.census
            raise AssertionError(method)
        launch=facts(MINT);launch['creator']=USER
        with patch.object(self.collector,'history',return_value=(self.rows,self.creation,NOW)),patch.object(self.collector.rpc,'call',side_effect=rpc),patch.object(self.collector,'social',return_value=facts()['socials']),patch('sources.time.time',return_value=NOW):return self.collector.enrich(launch,NOW)
    def test_complete_authenticated_all_pass(self):self.assertEqual(set(checks(self.enrich(),NOW).values()),{'PASS'})
    def test_owner_aggregation(self):
        # Split same owner's accounts still combine to >8%, never getTokenLargestAccounts.
        self.census['value'][2]['account']['data']['parsed']['info']['owner']=USER
        self.census['value'][2]['account']['data']['parsed']['info']['tokenAmount']['amount']='90'
        self.census['value'][0]['account']['data']['parsed']['info']['tokenAmount']['amount']='620'
        f=self.enrich();self.assertEqual(number(f['dev_pct']),11);self.assertEqual(checks(f,NOW)['developer'],'FAIL');self.assertEqual(checks(f,NOW)['top_holder'],'FAIL')
    def test_supply_gap_cannot_pass(self):
        self.census['value'].pop();f=self.enrich();self.assertIn('holder_supply_not_reconciled',f['collection_issue'])
        # Input facts are launch data, not previously authenticated normalized facts.
        self.assertNotEqual(set(checks(f,NOW).values()),{'PASS'});self.assertEqual(checks(f,NOW)['developer'],'UNKNOWN')
    def test_actual_creation_time_replaces_provider_estimate(self):
        self.creation['created_at']=NOW-650;self.assertEqual(self.enrich()['created_at'],NOW-650)
    def test_first_two_produced_blocks_union(self):self.assertEqual(number(self.enrich()['dev_first_pct']),D('2.9'))

class Integration(unittest.TestCase):
    def test_runner_fixture_no_activation_and_unique_report(self):
        with tempfile.TemporaryDirectory() as d,contextlib.redirect_stdout(io.StringIO()):
            r=Runner(d);f=facts(MINT);frame=dict(schema='early-lane-feed-v1',rules_sha256=RULES_SHA,exported_at=NOW,source_live=True,launches=[dict(mint=MINT,created_at=NOW-600,mc=10000,fixture_facts=f)],observations=[])
            self.assertEqual(r.poll(frame,NOW,fixtures=True)['selected'],1);self.assertIsNone(r.lane.activation());self.assertEqual(r.poll(frame,NOW,fixtures=True)['selected'],0)
            report=next(iter(volume_report(r.j).values()));self.assertEqual(report['first_seen_candidates'],1);self.assertEqual(report['unique_mints_passing_each']['developer'],1);r.j.db.close();r.collector.cache.close()
    def test_stale_frame_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runner(d)
            with self.assertRaises(ValueError):r.poll(dict(schema='early-lane-feed-v1',rules_sha256=RULES_SHA,exported_at=NOW-61),NOW)
            r.j.db.close();r.collector.cache.close()
    def test_installer_units_separate_and_no_scanner_execution(self):
        result=units('/opt/reviewed','hash',999,'/opt/scanner/data/db.sqlite')
        self.assertEqual(len(result),3);self.assertIn('User=vivameda-early-lane',result['vivameda-early-lane.service']);self.assertNotIn('--refresh-launch-feed',result['vivameda-early-lane-export.service']);self.assertIn('CAP_DAC_READ_SEARCH',result['vivameda-early-lane-export.service'])
        self.assertNotIn('early_scout.py',''.join(result.values()));self.assertNotIn('Restart=always',''.join(result.values()))
    def test_bundle_tamper_and_unsafe_path(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'x').write_text('x');raw=canonical({'sha256':{'x':hashlib.sha256(b'x').hexdigest()}}).encode();(p/'BUNDLE.json').write_bytes(raw);want=hashlib.sha256(raw).hexdigest();verify(want,p);(p/'x').write_text('bad')
            with self.assertRaises(ValueError):verify(want,p)
    def test_config_refuses_user_writable(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'delivery.json';p.write_text('{}');p.chmod(0o666)
            with self.assertRaises(ValueError):configuration(p)

if __name__=='__main__':unittest.main()
