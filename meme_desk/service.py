#!/usr/bin/env python3
"""Separate shadow daemon. It only reads an approved export and its own journal."""
import argparse
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import shutil
import signal
import time
from common import canonical,digest
from journal import Journal
from tickets import ingest,render

class Desk:
    def __init__(self,state_dir,config):
        if config.get('mode')!='human_review' or config.get('delivery_enabled') is not False or config.get('network_calls_from_desk') is not False:
            raise ValueError('Human-review configuration required; desk has no signing or direct network delivery')
        self.path=Path(state_dir);self.path.mkdir(mode=0o750,parents=True,exist_ok=True)
        if shutil.disk_usage(self.path).free<3*1024**3:raise ValueError('disk_reserve_below_3GiB')
        self.j=Journal(self.path/'desk.sqlite3');self.config=config
        self.logger=logging.getLogger('meme-desk:'+str(self.path.resolve()));self.logger.setLevel(logging.INFO);self.logger.propagate=False
        if not self.logger.handlers:
            handler=RotatingFileHandler(self.path/'desk.log',maxBytes=2*1024**2,backupCount=2)
            handler.setFormatter(logging.Formatter('%(message)s'));self.logger.addHandler(handler)
        prior=self.j.db.execute("SELECT body FROM events WHERE kind='configuration' ORDER BY seq LIMIT 1").fetchone()
        if prior and json.loads(prior[0])['sha256']!=digest(config):raise ValueError('configuration_binding_changed')
        self.j.transaction(lambda:self.j.append('configuration','configuration',{'sha256':digest(config),'config':config}))
    def poll(self,input_path,now=None,replay=None):
        now=time.time() if now is None else now
        if shutil.disk_usage(self.path).free<3*1024**3:
            raise ValueError('disk_reserve_below_3GiB')
        data=json.loads(Path(input_path).read_text())
        result=ingest(self.j,data,now,replay)
        for t in result:
            record=canonical({'kind':'SHADOW_TICKET','ticket':t['id'],'text':render(t,now)})
            self.logger.info(record);print(record,flush=True)
        return result

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['run','shadow','once','report','button','close','reenable'])
    p.add_argument('--state-dir',required=True);p.add_argument('--input');p.add_argument('--config',default=str(Path(__file__).with_name('config.json')))
    p.add_argument('--delivery-config');p.add_argument('--duration',type=int,default=3600);p.add_argument('--replay-aggregates');p.add_argument('--ticket');p.add_argument('--action',choices=['TAKEN','SKIP']);p.add_argument('--reason');p.add_argument('--net-pnl');p.add_argument('--event-id');a=p.parse_args()
    config=json.loads(Path(a.config).read_text())
    lock=None
    if a.command in ('run','shadow','once'):
        Path(a.state_dir).mkdir(parents=True,exist_ok=True);lock=open(Path(a.state_dir)/'process.lock','a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    desk=Desk(a.state_dir,config);j=desk.j
    if a.command=='button':
        if not all([a.ticket,a.action,a.event_id]):p.error('ticket, action and event-id required')
        print(j.button(a.event_id,a.ticket,a.action,a.reason));return
    if a.command=='close':
        if not all([a.ticket,a.net_pnl,a.event_id]):p.error('ticket, net-pnl and event-id required')
        print(j.close(a.event_id,a.ticket,a.net_pnl));return
    if a.command=='reenable':
        if not a.reason or not a.event_id:p.error('reason and event-id required')
        print(j.reenable(a.event_id,a.reason));return
    if a.command=='report':
        s=j.state();report={k:v for k,v in s.items() if k not in ('tickets','attempts')};report['ticket_count']=len(s['tickets']);report['journal_head']=j.verify();report['open_positions']=sorted(s['open_positions']);report['closed']=sorted(s['closed']);report['delivered']=sorted(s['delivered']);print(canonical(report));return
    if not a.input:p.error('input is required')
    running=True
    def stop(*_):
        nonlocal running
        running=False
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    started=time.time();end=time.monotonic()+a.duration if a.command=='shadow' else float('inf');cycles=0;valid=0;produced=0;errors={}
    replay=json.loads(Path(a.replay_aggregates).read_text()) if a.replay_aggregates else None
    while running:
        if shutil.disk_usage(desk.path).free<3*1024**3:raise SystemExit(75)
        cycles+=1
        try:
            tickets=desk.poll(a.input,replay=replay);produced+=len(tickets);valid+=1;status='SHADOW_ACTIVE'
        except (OSError,ValueError,KeyError,TypeError) as exc:
            key=type(exc).__name__+':'+str(exc)[:80] if isinstance(exc,ValueError) else type(exc).__name__
            errors[key]=errors.get(key,0)+1;status='WAITING_FOR_OWNER_EXPORT' if isinstance(exc,FileNotFoundError) else 'INPUT_BLOCKED'
        delivery_state='DISABLED_SHADOW'
        if a.command=='run' and a.delivery_config:
            try:
                from delivery import load_confirmed,UnixTransport,flush,callback
                delivery=load_confirmed(a.delivery_config)
                transport=UnixTransport(delivery['socket'])
                flush(j,transport,delivery,time.time())
                for update in transport.updates():
                    if str(update.get('owner_id'))!=str(delivery['owner_id']):continue
                    response=callback(j,str(update['id']),update['ticket'],update['action'],True,update.get('reason'))
                    if isinstance(response,dict) and 'choices' in response:
                        transport.prompt_skip(delivery['destination'],update['ticket'],str(update['id']))
                delivery_state='OWNER_CONFIRMED_BRIDGE' 
            except (OSError,ValueError,KeyError):
                delivery_state='BLOCKED_UNCONFIRMED_OR_SENDER_UNAVAILABLE'
        heartbeat=canonical({'kind':'heartbeat','time':time.time(),'status':status,'cycles':cycles,'valid_export_polls':valid,'tickets':produced,'delivery_state':delivery_state})
        desk.logger.info(heartbeat);print(heartbeat,flush=True)
        if a.command=='once' or time.monotonic()>=end:break
        until=min(end,time.monotonic()+config['poll_seconds'])
        while running and time.monotonic()<until:time.sleep(min(1,max(0,until-time.monotonic())))
    receipt={'started':started,'finished':time.time(),'duration_s':time.time()-started,'cycles':cycles,'valid_export_polls':valid,'tickets':produced,'errors':errors,'delivery':False,
             'mode':'shadow','status':'VALID_SHADOW_OBSERVATION' if valid else 'BLOCKED_NO_VALID_EXPORT; not a live dry-run pass'}
    from exporter import atomic_write
    atomic_write(Path(a.state_dir)/'shadow_receipt.json',receipt);print(canonical(receipt))
if __name__=='__main__':main()
