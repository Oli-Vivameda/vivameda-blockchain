"""Offline fixtures only. No production file reads and no network calls."""
import contextlib
import io
import json
import os
from pathlib import Path
import socket
import sqlite3
import struct
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import sender
import install
import owner

CHANNEL = '-1001234567890'
SCANNER = '-1009999999999'
TOKEN = '123456789:' + 'x' * 35

def request(key='event:one', text='A token alert'):
    return {'protocol': sender.PROTOCOL, 'channel': CHANNEL, 'parse_mode': 'HTML', 'text': text, 'idempotency_key': key}

def config(confirmed=True):
    return {'channel': CHANNEL, 'socket': str(sender.SOCKET), 'new_channel_confirmed': confirmed, 'confirmed_at': 1234}

class API:
    def __init__(self, outcomes=None): self.calls = []; self.outcomes = list(outcomes or [])
    def send(self, token, channel, text):
        self.calls.append((token, channel, text))
        if self.outcomes:
            value = self.outcomes.pop(0)
            if isinstance(value, BaseException): raise value
            return value
        return 'sent', {'chat_id': channel, 'message_id': 42, 'date': 1792220000}, 0

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.path = Path(self.temp.name) / 'state.sqlite'
        self.journal = sender.Journal(self.path); self.now = 1000; self.api = API()
        self.auth = Mock(return_value=TOKEN)
        self.engine = sender.Engine(self.journal, self.api, self.auth, lambda: self.now)
    def tearDown(self): self.journal.close(); self.temp.cleanup()
    def restart(self):
        self.journal.close(); self.journal = sender.Journal(self.path)
        self.engine = sender.Engine(self.journal, self.api, self.auth, lambda: self.now)
    def test_duplicate_returns_real_receipt_once(self):
        first = self.engine.handle(request()); second = self.engine.handle(request())
        self.assertEqual(first, second); self.assertEqual(first['receipt']['message_id'], 42); self.assertEqual(len(self.api.calls), 1)
    def test_receipt_survives_restart(self):
        first = self.engine.handle(request()); self.restart()
        self.assertEqual(self.engine.handle(request()), first); self.assertEqual(len(self.api.calls), 1)
    def test_dynamic_late_text_uses_original_event(self):
        self.engine.handle(request()); self.engine.handle(request(text='LATE 80s — same event'))
        self.assertEqual(len(self.api.calls), 1)
    def test_retry_after_survives_restart(self):
        self.api.outcomes = [('retry', None, 90)]
        self.assertEqual(self.engine.handle(request()), {'status': 429, 'retry_after': 90})
        self.restart(); self.now += 30
        self.assertEqual(self.engine.handle(request())['retry_after'], 60); self.assertEqual(len(self.api.calls), 1)
        self.now += 60; self.assertEqual(self.engine.handle(request())['status'], 200)
        self.assertTrue(self.api.calls[-1][2].startswith('🌻 LATE 90s'))
    def test_cooldown_applies_to_other_events(self):
        self.api.outcomes = [('retry', None, 30)]; self.engine.handle(request())
        self.assertEqual(self.engine.handle(request('event:two'))['status'], 429); self.assertEqual(len(self.api.calls), 1)
    def test_original_payload_retained_during_retry(self):
        self.api.outcomes = [('retry', None, 5)]; self.engine.handle(request()); self.now += 5
        self.engine.handle(request(text='changed')); self.assertEqual(self.api.calls[-1][2], '🌻 A token alert')
    def test_exception_token_never_logged_or_persisted(self):
        self.api.outcomes = [RuntimeError('https://api.telegram.org/bot' + TOKEN)]
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out): response = self.engine.handle(request())
        self.assertEqual(response['status'], 409); self.assertNotIn(TOKEN, out.getvalue() + json.dumps(response))
        self.restart(); self.engine.handle(request()); self.assertEqual(len(self.api.calls), 1)
        self.assertNotIn(TOKEN.encode(), self.path.read_bytes())
    def test_inflight_crash_held_after_restart(self):
        self.api.outcomes = [KeyboardInterrupt()]
        with self.assertRaises(KeyboardInterrupt): self.engine.handle(request())
        self.restart(); self.assertEqual(self.engine.handle(request())['status'], 409); self.assertEqual(len(self.api.calls), 1)
    def test_untrusted_receipt_cannot_leak_token(self):
        self.api.outcomes = [('sent', {'chat_id': CHANNEL, 'message_id': 42, 'date': 1, 'raw': TOKEN}, 0)]
        self.assertEqual(self.engine.handle(request())['status'], 409)
        self.assertNotIn(TOKEN, '\n'.join(self.journal.db.iterdump()))
    def test_reauthorization_on_duplicate(self):
        self.engine.handle(request()); self.auth.side_effect = sender.Refused('changed')
        self.assertEqual(self.engine.handle(request())['status'], 403); self.assertEqual(len(self.api.calls), 1)
    def test_wrong_destination_with_same_key(self):
        self.engine.handle(request()); value = request(); value['channel'] = '-1002222222222'
        self.assertEqual(self.engine.handle(value)['status'], 409); self.assertEqual(len(self.api.calls), 1)
    def test_no_secret_in_text_or_key(self):
        for value in (request(text=TOKEN), request(key=TOKEN)):
            self.assertEqual(self.engine.handle(value)['status'], 403)
        self.assertEqual(self.journal.db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)
        self.assertEqual(len(self.api.calls), 0)
    def test_reserved_owner_key_refused_on_socket(self):
        self.assertEqual(self.engine.handle(request('owner-channel-test-v1:' + CHANNEL))['status'], 403)
    def test_owner_test_fixed_and_idempotent(self):
        value = request('owner-channel-test-v1:' + CHANNEL, sender.TEST_TEXT)
        self.assertEqual(self.engine.handle(value, owner_test=True)['status'], 200)
        self.restart(); self.assertEqual(self.engine.handle(value, owner_test=True)['status'], 200)
        self.assertEqual(len(self.api.calls), 1)
        self.assertEqual(self.engine.handle(request(), owner_test=True)['status'], 403)
    def test_invalid_wire_values(self):
        values = [[], {}, dict(request(), extra=True), dict(request(), parse_mode='Markdown'),
                  dict(request(), text=''), dict(request(), text='x' * 4097), dict(request(), text='\ud800'),
                  dict(request(), idempotency_key='bad key'), dict(request(), channel='@alias')]
        for value in values: self.assertEqual(self.engine.handle(value)['status'], 403)
        self.assertFalse(self.api.calls)

class AuthorizationTests(unittest.TestCase):
    def authorize(self, c=None, creds=None, channel=CHANNEL, owner=False, uid=0):
        with patch.object(sender, 'secure_json', side_effect=[c if c is not None else config(), creds if creds is not None else {'chat_id': SCANNER, 'bot_token': TOKEN}]) as reader, patch.object(sender.os, 'geteuid', return_value=uid):
            return sender.authorize(channel, owner_test=owner)
    def test_confirmed_channel_allowed(self): self.assertEqual(self.authorize(), TOKEN)
    def test_wrong_chat_denied_before_credential_read(self):
        with patch.object(sender, 'secure_json', return_value=config()) as reader:
            with self.assertRaises(sender.Refused): sender.authorize('-1002222222222')
            reader.assert_called_once_with(sender.CONFIG)
    def test_scanner_chat_refused_string_and_integer(self):
        for chat in (CHANNEL, int(CHANNEL)):
            with self.assertRaises(sender.Refused): self.authorize(creds={'chat_id': chat, 'bot_token': TOKEN})
    def test_unknown_scanner_chat_fails_closed(self):
        with self.assertRaises(sender.Refused): self.authorize(creds={'chat_id': '@alias', 'bot_token': TOKEN})
    def test_unconfirmed_or_wrong_socket_refused(self):
        for c in (config(False), dict(config(), socket='/tmp/socket'), dict(config(), confirmed_at=None), dict(config(), channel=None)):
            with self.assertRaises(sender.Refused): self.authorize(c=c)
    def test_owner_test_unconfirmed_but_exact_destination(self):
        self.assertEqual(self.authorize(c=config(False), owner=True), TOKEN)
        with self.assertRaises(sender.Refused): self.authorize(c=config(False), owner=True, uid=994)
        with self.assertRaises(sender.Refused): self.authorize(c=dict(config(False), channel=None), owner=True)
    def test_token_invalid_refused(self):
        with self.assertRaises(sender.Refused): self.authorize(creds={'chat_id': SCANNER, 'bot_token': 'bad'})

class SharedChannelTests(unittest.TestCase):
    def test_scanner_channel_allowed_only_with_explicit_root_flag(self):
        for value in (True, False, 'true', None):
            settings = dict(config(), reuse_scanner_channel=value)
            with patch.object(sender, 'secure_json', side_effect=[settings, {'chat_id': CHANNEL, 'bot_token': TOKEN}]):
                if value is True: self.assertEqual(sender.authorize(CHANNEL), TOKEN)
                else:
                    with self.assertRaises(sender.Refused): sender.authorize(CHANNEL)
    def test_shared_flag_does_not_bypass_confirmation_or_destination(self):
        for settings, destination in ((dict(config(False), reuse_scanner_channel=True), CHANNEL),
                                      (dict(config(), reuse_scanner_channel=True), SCANNER)):
            with patch.object(sender, 'secure_json', return_value=settings):
                with self.assertRaises(sender.Refused): sender.authorize(destination)
    def test_atomic_configuration_keeps_delivery_off_and_never_copies_token(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'delivery.json'; path.write_text(json.dumps(config(False))); path.chmod(0o640)
            base = dict(config(False), channel=None, confirmed_at=None)
            original_lstat = Path.lstat
            def root_metadata(p):
                actual = original_lstat(p)
                if p == path or p == path.parent:
                    return Mock(st_mode=actual.st_mode, st_uid=0, st_gid=actual.st_gid)
                return actual
            with patch.object(sender, 'CONFIG', path), patch.object(sender.os, 'geteuid', return_value=0), patch.object(sender, 'secure_json', side_effect=[base, {'chat_id': CHANNEL, 'bot_token': TOKEN}]), patch.object(Path, 'lstat', root_metadata), patch.object(sender.os, 'fchown'):
                self.assertEqual(sender.prepare_scanner_test(), CHANNEL)
            saved = json.loads(path.read_text())
            self.assertEqual(saved['channel'], CHANNEL); self.assertTrue(saved['reuse_scanner_channel'])
            self.assertIs(saved['new_channel_confirmed'], False); self.assertIsNone(saved['confirmed_at'])
            self.assertNotIn(TOKEN, path.read_text()); self.assertEqual(path.stat().st_mode & 0o777, 0o640)
    def test_shared_prepare_requires_root_and_disabled_config(self):
        with patch.object(sender.os, 'geteuid', return_value=994), patch.object(sender, 'secure_json') as reader:
            with self.assertRaises(sender.Refused): sender.prepare_scanner_test()
            reader.assert_not_called()
        for value in (config(True), dict(config(False), confirmed_at=123), dict(config(False), channel=SCANNER, confirmed_at=None)):
            with patch.object(sender.os, 'geteuid', return_value=0), patch.object(sender, 'secure_json', side_effect=[value, {'chat_id': CHANNEL, 'bot_token': TOKEN}]):
                with self.assertRaises(sender.Refused): sender.prepare_scanner_test()
    def test_sunflower_prefix_on_test_and_alert(self):
        for test in (False, True):
            with tempfile.TemporaryDirectory() as temp:
                journal = sender.Journal(Path(temp) / 'state.sqlite'); api = API()
                try:
                    engine = sender.Engine(journal, api, lambda *a, **k: TOKEN)
                    value = request('owner-channel-test-v1:' + CHANNEL, sender.TEST_TEXT) if test else request()
                    self.assertEqual(engine.handle(value, owner_test=test)['status'], 200)
                    self.assertTrue(api.calls[0][2].startswith('🌻 '))
                    engine.handle(value, owner_test=test); self.assertEqual(len(api.calls), 1)
                finally: journal.close()

class UpgradeTests(unittest.TestCase):
    def test_upgrade_validates_old_source_without_execution(self):
        import hashlib
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / 'fixture.py'; source.write_text('raise RuntimeError("must not execute")')
            raw = json.dumps({'sha256': {'fixture.py': hashlib.sha256(source.read_bytes()).hexdigest()}}).encode()
            (root / 'BUNDLE.json').write_bytes(raw); expected = hashlib.sha256(raw).hexdigest()
            install.verify_release(root, expected)
            source.write_text('tampered')
            with self.assertRaises(SystemExit): install.verify_release(root, expected)
    def test_upgrade_refuses_active_or_enabled_units(self):
        for output in ('ActiveState=active\nUnitFileState=disabled\n', 'ActiveState=inactive\nUnitFileState=enabled\n'):
            with patch.object(install.subprocess, 'run', return_value=Mock(stdout=output)):
                with self.assertRaises(SystemExit): install.stopped_units()
        with patch.object(install.subprocess, 'run', return_value=Mock(stdout='ActiveState=inactive\nUnitFileState=disabled\n')) as run:
            install.stopped_units(); self.assertEqual(run.call_count, 2)
    def test_upgrade_never_deletes_state_or_starts_services(self):
        source = Path(install.__file__).read_text()
        for forbidden in ("'start'", "'enable'", 'rmtree', 'STATE.unlink', 'CREDENTIAL.read'):
            self.assertNotIn(forbidden, source)
        self.assertIn("if not upgrading:\n            STATE.mkdir", source)
        self.assertIn('verify_release(previous, a.from_bundle)', source)

class FileTests(unittest.TestCase):
    def test_root_file_security_dummy_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'fixture.json'; path.write_text('{"fixture": true}'); path.chmod(0o600)
            actual = path.stat()
            root_stat = Mock(st_mode=actual.st_mode, st_uid=0)
            with patch.object(sender.os, 'fstat', return_value=root_stat): self.assertEqual(sender.secure_json(path), {'fixture': True})
            with patch.object(sender.os, 'fstat', return_value=Mock(st_mode=0o100666, st_uid=0)):
                with self.assertRaises(sender.Refused): sender.secure_json(path)
            with patch.object(sender.os, 'fstat', return_value=Mock(st_mode=0o100600, st_uid=994)):
                with self.assertRaises(sender.Refused): sender.secure_json(path)
            link = Path(temp) / 'link'; link.symlink_to(path)
            with self.assertRaises(OSError): sender.secure_json(link)
    def test_state_requires_root_before_any_open(self):
        with patch.object(sender.os, 'geteuid', return_value=994), patch.object(sender.os, 'open') as op:
            with self.assertRaises(sender.Refused):
                with sender.state_lock(): pass
            op.assert_not_called()

class TelegramTests(unittest.TestCase):
    def run_api(self, data=None, status=200, headers=(), exception=None):
        conn = Mock(); response = Mock(); response.status = status
        response.read.return_value = json.dumps(data).encode(); response.getheaders.return_value = headers
        conn.getresponse.return_value = response
        if exception: conn.request.side_effect = exception
        with contextlib.redirect_stdout(io.StringIO()) as output, contextlib.redirect_stderr(output):
            result = sender.Telegram(lambda: conn).send(TOKEN, CHANNEL, 'test')
        self.assertNotIn(TOKEN, repr(result) + output.getvalue()); conn.close.assert_called_once()
        return result
    def test_real_receipt_whitelist(self):
        result = self.run_api({'ok': True, 'result': {'message_id': 3, 'date': 7, 'chat': {'id': int(CHANNEL), 'title': TOKEN}, 'text': TOKEN}})
        self.assertEqual(result, ('sent', {'chat_id': CHANNEL, 'message_id': 3, 'date': 7}, 0))
    def test_wrong_chat_or_missing_receipt_ambiguous(self):
        for result in ({}, {'message_id': 2, 'date': 3, 'chat': {'id': int(SCANNER)}}, {'message_id': True, 'date': 3, 'chat': {'id': int(CHANNEL)}}):
            self.assertEqual(self.run_api({'ok': True, 'result': result})[0], 'ambiguous')
    def test_retry_after_maximum_header_and_parameters(self):
        self.assertEqual(self.run_api({'ok': False, 'parameters': {'retry_after': 12}, 'description': TOKEN}, 429, [('Retry-After', '30')]), ('retry', None, 30))
    def test_retry_after_on_api_error_even_http200(self):
        self.assertEqual(self.run_api({'ok': False, 'error_code': 429, 'parameters': {'retry_after': 12}}), ('retry', None, 12))
    def test_retry_after_http_date(self):
        self.assertEqual(sender.retry_delay({'retry-after': 'Thu, 01 Jan 1970 00:02:00 GMT'}, {}, 100), 20)
    def test_retry_after_invalid_is_safe(self):
        self.assertEqual(sender.retry_delay({'retry-after': 'nan'}, {'parameters': {'retry_after': 'inf'}}, 100), 1)
    def test_http_exception_secret_redacted(self):
        self.assertEqual(self.run_api(exception=RuntimeError(TOKEN))[0], 'ambiguous')
    def test_api_errors_secret_redacted_and_no_redirect(self):
        self.assertEqual(self.run_api({'ok': False, 'error_code': 400, 'description': TOKEN, 'parameters': {'migrate_to_chat_id': int(SCANNER)}}, 400), ('retry', None, 60))
        self.assertEqual(self.run_api({}, 302, [('Location', 'https://bad.example/' + TOKEN)])[0], 'ambiguous')
    def test_server_error_is_ambiguous(self): self.assertEqual(self.run_api({'ok': False}, 500)[0], 'ambiguous')

class SocketTests(unittest.TestCase):
    def test_actual_unix_peer_and_newline_protocol(self):
        a, b = socket.socketpair()
        try:
            self.assertTrue(sender.peer_allowed(a, os.geteuid()))
            if os.geteuid() != 0: self.assertFalse(sender.peer_allowed(a, os.geteuid() + 1))
            b.sendall((json.dumps(request()) + '\n').encode()); self.assertEqual(sender.read_request(a), request())
        finally: a.close(); b.close()
    def test_unauthorized_peer_never_handles_request(self):
        conn = Mock(); conn.getsockopt.return_value = struct.pack('3i', 1, 12345, 12345); engine = Mock()
        sender.serve_connection(conn, engine, 994); engine.handle.assert_not_called()
        self.assertEqual(json.loads(conn.sendall.call_args.args[0])['status'], 403)
    def test_oversized_and_truncated_request(self):
        conn = Mock(); conn.recv.return_value = b'x' * 4096
        with self.assertRaises(sender.Refused): sender.read_request(conn)
        conn.recv.return_value = b''
        with self.assertRaises(sender.Refused): sender.read_request(conn)

    def test_complete_wire_request_returns_durable_receipt(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = sender.Journal(Path(temp) / 'wire.sqlite')
            api = API(); engine = sender.Engine(journal, api, lambda *a, **k: TOKEN)
            a, b = socket.socketpair()
            try:
                b.sendall((json.dumps(request()) + '\n').encode())
                sender.serve_connection(a, engine, os.geteuid())
                response = json.loads(b.recv(65536))
                self.assertEqual(response['status'], 200)
                self.assertEqual(response['receipt']['message_id'], 42)
                b.sendall((json.dumps(request(text='LATE 90s')) + '\n').encode())
                sender.serve_connection(a, engine, os.geteuid())
                self.assertEqual(json.loads(b.recv(65536)), response)
                self.assertEqual(len(api.calls), 1)
            finally:
                a.close(); b.close(); journal.close()

class CredentialOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.lookup = patch.object(sender.pwd, 'getpwnam', return_value=Mock(pw_uid=996))
        self.lookup.start(); self.addCleanup(self.lookup.stop)
    def test_existing_scanner_private_owner_is_accepted(self):
        self.assertTrue(sender.credential_metadata_valid(Mock(st_mode=0o100600, st_uid=996)))
        self.assertTrue(sender.credential_metadata_valid(Mock(st_mode=0o100400, st_uid=996)))
    def test_root_private_owner_remains_accepted(self):
        self.assertTrue(sender.credential_metadata_valid(Mock(st_mode=0o100600, st_uid=0)))
    def test_other_owner_group_read_or_write_and_symlinks_refused(self):
        for mode, uid in ((0o100600, 994), (0o100640, 996), (0o100620, 996), (0o100604, 996), (0o120777, 996)):
            self.assertFalse(sender.credential_metadata_valid(Mock(st_mode=mode, st_uid=uid)))
    def test_runtime_reads_scanner_owned_dummy_file_only(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'dummy.json'; path.write_text(json.dumps({'bot_token': TOKEN, 'chat_id': SCANNER})); path.chmod(0o600)
            with patch.object(sender.os, 'fstat', return_value=Mock(st_mode=0o100600, st_uid=996)):
                self.assertEqual(sender.secure_json(path, private=True)['bot_token'], TOKEN)
                with self.assertRaises(sender.Refused): sender.secure_json(path)
    def test_installer_metadata_check_never_opens_credential(self):
        source = Path(install.__file__).read_text()
        self.assertIn('credential_metadata_valid(st)', source)
        self.assertIn('st = CREDENTIAL.lstat()', source)
        self.assertNotIn('CREDENTIAL.open', source); self.assertNotIn('CREDENTIAL.read', source)
    def test_root_service_can_read_existing_scanner_private_file(self):
        unit = install.unit_text(Path('/opt/vivameda-early-lane-sender/' + 'a' * 64))
        self.assertIn('CapabilityBoundingSet=CAP_DAC_READ_SEARCH', unit)
        self.assertIn('InaccessiblePaths=-/opt/vivameda-crypto-early-scout/data', unit)

class SnapshotBootstrapTests(unittest.TestCase):
    def test_isolated_child_imports_only_reviewed_snapshot_helper(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'reviewed_helper.py').write_text('VALUE = 42\n')
            (root / 'entry.py').write_text('import reviewed_helper, sys\nprint(reviewed_helper.VALUE, sys.argv[1])\n')
            argv = owner.snapshot_command(root, [str(root / 'entry.py'), 'fixture'])
            result = subprocess.run(argv, capture_output=True, text=True, cwd='/')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '42 fixture')
            self.assertIn('-I', argv)

class InstallerTests(unittest.TestCase):
    def test_unit_is_isolated_and_never_enables_or_starts(self):
        unit = install.unit_text(Path('/opt/vivameda-early-lane-sender/' + 'a' * 64))
        for expected in ('User=root', 'Group=vivameda-early-lane', 'ProtectSystem=strict', 'CapabilityBoundingSet=CAP_DAC_READ_SEARCH', 'RuntimeDirectoryMode=0750', 'StateDirectoryMode=0700'):
            self.assertIn(expected, unit)
        source = Path(install.__file__).read_text()
        self.assertNotIn("'start'", source); self.assertNotIn("'enable'", source)
        self.assertNotIn('CREDENTIAL.read', source); self.assertNotIn('delivery.json\').write', source)
    def test_bad_bundle_bootstrap_does_not_execute_imports(self):
        import subprocess
        result = subprocess.run([sys.executable, str(Path(sender.__file__).parent / 'owner.py'), '--expected-bundle', '0' * 64, 'test-channel', '--', '--expected-channel', CHANNEL], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0); self.assertIn('sender_bundle_mismatch', result.stderr)
        self.assertNotIn(TOKEN, result.stdout + result.stderr)

if __name__ == '__main__': unittest.main()
