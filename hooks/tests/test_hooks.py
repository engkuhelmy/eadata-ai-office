"""Test untuk office-hook dan install-hooks. Jalankan: python -m unittest discover -s hooks/tests -v"""
import importlib.util
import io
import json
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

HOOKS_DIR = Path(__file__).resolve().parents[1]


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HOOKS_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


hook = load('office_hook', 'office-hook.py')
installer = load('install_hooks', 'install-hooks.py')


class StubServer:
    """HTTP server kecil. Rekod request dan balas status tetap."""

    def __init__(self, status=202):
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', 0))
                outer.requests.append({
                    'path': self.path,
                    'auth': self.headers.get('Authorization'),
                    'body': json.loads(self.rfile.read(length) or b'{}'),
                })
                self.send_response(status)
                self.end_headers()

            def log_message(self, *args):
                pass

        self.httpd = HTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class HookTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        hub = self.tmp / '.office-hub'
        hub.mkdir()
        hook.HOME_DIR = hub
        hook.CONFIG_FILE = hub / 'config.json'
        hook.SPOOL_FILE = hub / 'spool.jsonl'
        hook.SPOOL_LOCK = hub / 'spool.lock'
        hook.LOG_FILE = hub / 'hook.log'

    def write_config(self, url, token='eod_test'):
        hook.CONFIG_FILE.write_text(json.dumps({'url': url, 'token': token}), encoding='utf-8')


class RedactionTests(HookTestCase):
    def test_secrets_are_masked(self):
        text = redact = hook.redact_text('key sk-abcdefghijklmnopqrstu dan password=hunter2 Bearer abc.def')
        self.assertIn('sk-***', text)
        self.assertIn('password=***', text)
        self.assertIn('Bearer ***', text)
        self.assertNotIn('hunter2', redact)

    def test_env_lines_are_masked(self):
        self.assertEqual(hook.redact_text('DB_PASSWORD=abc\nAPP_KEY=xyz'), 'DB_PASSWORD=***\nAPP_KEY=***')

    def test_content_fields_are_dropped_and_only_path_kept(self):
        payload = {
            'hook_event_name': 'PreToolUse',
            'session_id': 's1',
            'cwd': 'C:\\proj',
            'tool_name': 'Edit',
            'tool_input': {
                'file_path': 'resources/js/Navbar.vue',
                'old_string': 'rahsia lama',
                'new_string': 'rahsia baru',
            },
            'tool_response': {'is_error': False, 'output': 'isi fail panjang'},
            'prompt': 'tolong buat sesuatu',
        }
        body = hook.sanitize(payload)

        self.assertEqual(body['tool_input'], {'file_path': 'resources/js/Navbar.vue'})
        self.assertEqual(body['tool_response'], {'is_error': False})
        self.assertNotIn('prompt', body)
        self.assertNotIn('rahsia', json.dumps(body))
        self.assertIn('pc', body)
        self.assertIn('ts', body)

    def test_command_secret_is_masked_in_body(self):
        body = hook.sanitize({
            'hook_event_name': 'PreToolUse',
            'tool_name': 'Bash',
            'tool_input': {'command': 'curl -H "Authorization: Bearer abc123" https://x'},
        })
        self.assertNotIn('abc123', body['tool_input']['command'])


class SendTests(HookTestCase):
    def test_send_failure_returns_false_so_event_is_spooled(self):
        self.write_config('http://127.0.0.1:9')  # port tertutup
        self.assertFalse(hook.post(hook.load_config(), 'claude', None, {'a': 1}))

    def test_server_4xx_is_not_retried(self):
        stub = StubServer(status=401)
        try:
            self.write_config(stub.url)
            self.assertTrue(hook.post(hook.load_config(), 'claude', None, {'a': 1}))
        finally:
            stub.close()

    def test_spool_is_flushed_when_server_is_back(self):
        for i in range(3):
            hook.spool_append('claude', 'tool_start', {'n': i})
        stub = StubServer(status=202)
        try:
            self.write_config(stub.url)
            hook.flush_spool(hook.load_config())
        finally:
            stub.close()

        self.assertEqual([r['body']['n'] for r in stub.requests], [0, 1, 2])
        self.assertTrue(all(r['auth'] == 'Bearer eod_test' for r in stub.requests))
        self.assertFalse(hook.SPOOL_FILE.exists())

    def test_flush_stops_at_first_failure_and_keeps_rest(self):
        for i in range(3):
            hook.spool_append('claude', 'tool_start', {'n': i})
        self.write_config('http://127.0.0.1:9')
        hook.flush_spool(hook.load_config())
        lines = hook.SPOOL_FILE.read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(lines), 3)

    def test_main_never_writes_stdout_and_hands_sanitized_body_to_child(self):
        captured = {}

        def fake_spawn(data):
            captured.update(data)

        stdin = io.TextIOWrapper(io.BytesIO(json.dumps({
            'hook_event_name': 'PreToolUse', 'session_id': 's1',
            'tool_name': 'Write', 'tool_input': {'file_path': 'a.php', 'content': 'SECRET-ISI'},
        }).encode('utf-8')), encoding='utf-8')
        out = io.StringIO()
        with mock.patch.object(hook, 'spawn_background', fake_spawn), \
                mock.patch.object(sys, 'stdin', stdin), redirect_stdout(out):
            hook.main(['--src', 'claude'])

        self.assertEqual(out.getvalue(), '')
        self.assertEqual(captured['src'], 'claude')
        self.assertNotIn('SECRET-ISI', json.dumps(captured))
        self.assertEqual(captured['body']['tool_input'], {'file_path': 'a.php'})


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        (self.home / '.claude').mkdir()
        (self.home / '.codex').mkdir()
        (self.home / '.hermes').mkdir()
        self.settings = self.home / '.claude' / 'settings.json'
        self.settings.write_text(json.dumps({'outputStyle': 'Concise'}, indent=2), encoding='utf-8')
        self.hermes = self.home / '.hermes' / 'config.yaml'
        self.hermes.write_text('model: gpt-x\nplatform: cli\n', encoding='utf-8')

    def run_installer(self, *extra):
        args = ['--home', str(self.home), '--tools', 'claude,codex,hermes', *extra]
        if '--uninstall' not in extra:
            args += ['--url', 'http://127.0.0.1:8000', '--token', 'eod_test']
        with redirect_stdout(io.StringIO()):
            installer.main(args)

    def test_install_merges_and_keeps_existing_keys(self):
        self.run_installer()
        data = json.loads(self.settings.read_text(encoding='utf-8'))
        self.assertEqual(data['outputStyle'], 'Concise')
        self.assertIn('PreToolUse', data['hooks'])
        cmd = data['hooks']['PreToolUse'][0]['hooks'][0]
        self.assertIn('office-hook', cmd['command'])
        self.assertTrue(cmd['async'])

        codex = json.loads((self.home / '.codex' / 'hooks.json').read_text(encoding='utf-8'))
        self.assertIn('SessionStart', codex['hooks'])

        text = self.hermes.read_text(encoding='utf-8')
        self.assertIn(installer.HUB_BEGIN, text)
        self.assertIn('pre_tool_call:', text)
        self.assertIn('model: gpt-x', text)

    def test_install_is_idempotent(self):
        self.run_installer()
        first = (self.settings.read_text(encoding='utf-8'), self.hermes.read_text(encoding='utf-8'))
        self.run_installer()
        second = (self.settings.read_text(encoding='utf-8'), self.hermes.read_text(encoding='utf-8'))
        self.assertEqual(first, second)

    def test_backup_is_created_once_with_original_content(self):
        original = self.settings.read_text(encoding='utf-8')
        self.run_installer()
        bak = self.settings.with_name('settings.json.bak-office')
        self.assertEqual(bak.read_text(encoding='utf-8'), original)

    def test_uninstall_restores_original_claude_and_hermes(self):
        original_settings = self.settings.read_text(encoding='utf-8')
        original_hermes = self.hermes.read_text(encoding='utf-8')
        self.run_installer()
        self.run_installer('--uninstall')

        self.assertEqual(json.loads(self.settings.read_text(encoding='utf-8')), json.loads(original_settings))
        self.assertEqual(self.hermes.read_text(encoding='utf-8'), original_hermes)
        codex = json.loads((self.home / '.codex' / 'hooks.json').read_text(encoding='utf-8'))
        self.assertNotIn('hooks', codex)

    def test_dry_run_writes_nothing(self):
        before = self.settings.read_text(encoding='utf-8')
        self.run_installer('--dry-run')
        self.assertEqual(self.settings.read_text(encoding='utf-8'), before)
        self.assertFalse((self.home / '.office-hub').exists())
        self.assertFalse((self.home / '.codex' / 'hooks.json').exists())
        self.assertNotIn(installer.HUB_BEGIN, self.hermes.read_text(encoding='utf-8'))

    def test_hermes_with_existing_top_level_hooks_refuses_to_merge(self):
        self.hermes.write_text('hooks:\n  pre_tool_call: []\n', encoding='utf-8')
        with self.assertRaises(SystemExit):
            self.run_installer()
        self.assertNotIn(installer.HUB_BEGIN, self.hermes.read_text(encoding='utf-8'))

    def test_codex_session_end_is_not_async(self):
        self.run_installer()
        codex = json.loads((self.home / '.codex' / 'hooks.json').read_text(encoding='utf-8'))
        handler = codex['hooks']['SessionEnd'][0]['hooks'][0]
        self.assertNotIn('async', handler)
        self.assertLessEqual(handler['timeout'], 3)


if __name__ == '__main__':
    unittest.main()
