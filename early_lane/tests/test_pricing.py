import base64
import copy
import hashlib
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pricing import *
from test_evidence import key,account
from test_lane import NOW,facts
from core import checks

def wrap(raw,owner):return dict(owner=owner,executable=False,data=[base64.b64encode(raw).decode(),'base64'])
def oracle_account(at=NOW,verification=1,price=20000000000,feed=SOL_FEED):
    raw=hashlib.sha256(b'account:PriceUpdateV2').digest()[:8]+bytes(32)+bytes([verification])+feed+struct.pack('<qQiqqqQQ',price,1000000,-8,at,at-1,price,1000000,100)+b'\0'
    return wrap(raw,RECEIVER)
def mint_account(n=1000):
    raw=bytearray(82);raw[36:44]=n.to_bytes(8,'little');raw[44]=6;raw[45]=1;return wrap(raw,SPL)
def curve_account(complete=0):
    return wrap(CURVE_DISC+struct.pack('<5Q',1100,60000000,700,10,1000)+bytes([complete])+b58decode(key(2))+bytes(34),PUMP)
def token_account(mint,owner,n):
    raw=bytearray(165);raw[:32]=b58decode(mint);raw[32:64]=b58decode(owner);raw[64:72]=n.to_bytes(8,'little');raw[108]=1;return wrap(raw,SPL)

class Pricing(unittest.TestCase):
    def test_pda_deterministic_off_curve(self):
        a=addresses(key(1));self.assertEqual(a,addresses(key(1)));self.assertTrue(all(not on_curve(b58decode(x)) for x in a))
    def test_pda_seed_limits(self):
        with self.assertRaises(ValueError):pda([bytes(33)],PUMP)
    def test_edwards_point_recognition(self):
        self.assertTrue(on_curve(bytes.fromhex('58'+'66'*31)));self.assertFalse(on_curve(bytes([255])*32))
    def test_authenticated_oracle(self):
        price,at,conf=oracle(oracle_account(),NOW);self.assertEqual(price,200);self.assertEqual(at,NOW)
    def test_oracle_stale_future_partial_wrong_feed(self):
        for args in (dict(at=NOW-61),dict(at=NOW+1),dict(verification=0),dict(feed=bytes(32)),dict(price=-1)):
            with self.subTest(args=args),self.assertRaises(ValueError):oracle(oracle_account(**args),NOW)
    def test_oracle_wrong_owner(self):
        a=oracle_account();a['owner']=PUMP
        with self.assertRaises(ValueError):oracle(a,NOW)
    def test_curve_mc_uses_raw_supply_no_decimal_error(self):self.assertEqual(curve_mark(curve_account(),key(1),1000,D(200)),D(12000)/1100)
    def test_curve_completed_has_no_curve_price(self):self.assertIsNone(curve_mark(curve_account(1),key(1),1000,D(200)))
    def test_curve_bad_supply_rejected(self):
        with self.assertRaises(ValueError):curve_mark(curve_account(),key(1),1001,D(200))
    def test_supply_burn_uses_current_supply(self):
        self.assertAlmostEqual(curve_mark(curve_account(),key(1),500,D(200)),curve_mark(curve_account(),key(1),1000,D(200))/2,delta=D('1e-20'))
    def test_curve_non_sol_rejected(self):
        a=curve_account();raw=bytearray(base64.b64decode(a['data'][0]));raw[83]=1;a=wrap(raw,PUMP)
        with self.assertRaises(ValueError):curve_mark(a,key(1),1000,D(200))
    def test_pool_vault_owner_and_mint_authenticated(self):
        pool=key(9);self.assertEqual(pool_mark(token_account(key(1),pool,100),token_account(WSOL,pool,1000000000),key(1),pool,1000,D(200)),(D(2000),D(400)))
        with self.assertRaises(ValueError):pool_mark(token_account(key(1),key(8),100),token_account(WSOL,pool,1000000000),key(1),pool,1000,D(200))
    def test_zero_quote_authenticates_zero_mark(self):
        p=key(9);self.assertEqual(pool_mark(token_account(key(1),p,100),token_account(WSOL,p,0),key(1),p,1000,D(200)),(0,0))
    def test_empty_base_does_not_invent_price(self):
        p=key(9)
        with self.assertRaises(ValueError):pool_mark(token_account(key(1),p,0),token_account(WSOL,p,100),key(1),p,1000,D(200))
    def test_marks_batch_binds_same_slot_and_no_retro_timestamp(self):
        class Rpc:
            def call(self,method,params):
                if method=='getBlockTime':return NOW
                return dict(context=dict(slot=100),value=[oracle_account(NOW-50),mint_account(),curve_account(),None])
        m=Marks(Rpc()).read([dict(mint=key(1))],NOW)[key(1)]
        self.assertEqual(m['market_at'],NOW);self.assertEqual(m['market_expires_at'],NOW+10)
    def test_market_expires_with_oldest_component(self):
        f=facts();f['market_expires_at']=NOW-1;self.assertEqual(checks(f,NOW)['market_cap'],'UNKNOWN')
    def test_context_stale_rejected(self):
        class Rpc:
            def call(self,method,params):return NOW-61 if method=='getBlockTime' else dict(context=dict(slot=100),value=[oracle_account(),mint_account(),curve_account(),None])
        with self.assertRaises(ValueError):Marks(Rpc()).read([dict(mint=key(1))],NOW)
    def test_graduated_pool_batch_price(self):
        mint=key(1);curve,pool,authority=addresses(mint)
        raw=POOL_DISC+b'\0\0\0'+b58decode(authority)+b58decode(mint)+b58decode(WSOL)+b58decode(key(4))+b58decode(key(5))+b58decode(key(6))+bytes(8)+b58decode(key(2))+bytes(2)
        pa=wrap(raw,AMM)
        class Rpc:
            reads=0
            def call(self,method,params):
                if method=='getBlockTime':return NOW
                self.reads+=1
                values=[oracle_account(),mint_account(),curve_account(1),pa] if self.reads==1 else [oracle_account(),mint_account(),token_account(mint,pool,100),token_account(WSOL,pool,1000000000)]
                return dict(context=dict(slot=100),value=values)
        mark=Marks(Rpc()).read([dict(mint=mint)],NOW)[mint]
        self.assertEqual(number(mark['mc']),2000);self.assertEqual(number(mark['liquidity']),400)

if __name__=='__main__':unittest.main()
