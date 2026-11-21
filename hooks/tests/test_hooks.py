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

    def test_server_5xx_and_429_are_retried_via_spool(self):
        for status in (500, 503, 429):
            stub = StubServer(status=status)
            try:
                self.write_config(stub.url)
                self.assertFalse(hook.post(hook.load_config(), 'claude', None, {'a': 1}), status)
            finally:
                stub.close()

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


class ClaudeUsageTests(HookTestCase):
    def transcript(self, lines):
        path = self.tmp / 'transcript.jsonl'
        path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return str(path)

    @staticmethod
    def entry(inp, out, cread, ccreate, msg_id=None):
        message = {'role': 'assistant', 'content': 'RAHSIA-TRANSKRIP',
                   'usage': {'input_tokens': inp, 'output_tokens': out,
                             'cache_read_input_tokens': cread, 'cache_creation_input_tokens': ccreate}}
        if msg_id:
            message['id'] = msg_id
        return json.dumps({'type': 'assistant', 'message': message})

    def test_sums_usage_and_tolerates_bad_lines(self):
        path = self.transcript([
            self.entry(1, 2, 3, 4),
            'bukan json {{{',
            json.dumps({'type': 'user', 'message': {'role': 'user', 'content': 'hai'}}),
            json.dumps({'message': {'usage': {'input_tokens': 'x', 'output_tokens': 5}}}),
            '',
            self.entry(10, 20, 30, 40),
        ])
        self.assertEqual(hook.read_claude_usage({'transcript_path': path}),
                         {'input': 11, 'output': 27, 'cache_read': 33, 'cache_create': 44})

    def test_duplicate_message_ids_counted_once(self):
        path = self.transcript([self.entry(1, 2, 3, 4, 'msg_1'), self.entry(1, 2, 3, 4, 'msg_1'), self.entry(5, 5, 5, 5, 'msg_2')])
        self.assertEqual(hook.read_claude_usage({'transcript_path': path}),
                         {'input': 6, 'output': 7, 'cache_read': 8, 'cache_create': 9})

    def test_missing_or_invalid_path_returns_none(self):
        self.assertIsNone(hook.read_claude_usage({}))
        self.assertIsNone(hook.read_claude_usage({'transcript_path': 123}))
        self.assertIsNone(hook.read_claude_usage({'transcript_path': str(self.tmp / 'tiada.jsonl')}))
        self.assertIsNone(hook.read_claude_usage({'transcript_path': self.transcript(['x'])}))

    def test_read_is_capped(self):
        path = self.transcript([self.entry(1, 1, 1, 1), self.entry(1, 1, 1, 1)])
        with mock.patch.object(hook, 'MAX_TRANSCRIPT_BYTES', len(self.entry(1, 1, 1, 1)) + 5):
            self.assertEqual(hook.read_claude_usage({'transcript_path': path}),
                             {'input': 1, 'output': 1, 'cache_read': 1, 'cache_create': 1})

    def run_main(self, src, hook_event, path):
        captured = {}
        stdin = io.TextIOWrapper(io.BytesIO(json.dumps({
            'hook_event_name': hook_event, 'session_id': 's1', 'transcript_path': path,
        }).encode('utf-8')), encoding='utf-8')
        with mock.patch.object(hook, 'spawn_background', captured.update), \
                mock.patch.object(sys, 'stdin', stdin), redirect_stdout(io.StringIO()):
            hook.main(['--src', src])
        return captured

    def test_stop_adds_only_totals_never_transcript(self):
        path = self.transcript([self.entry(1, 2, 3, 4)])
        data = self.run_main('claude', 'Stop', path)
        self.assertEqual(data['body']['usage'], {'input': 1, 'output': 2, 'cache_read': 3, 'cache_create': 4})
        self.assertNotIn('transcript_path', data['body'])
        self.assertNotIn('RAHSIA-TRANSKRIP', json.dumps(data))
        self.assertNotIn(path, json.dumps(data))

    def test_usage_only_for_claude_stop(self):
        path = self.transcript([self.entry(1, 2, 3, 4)])
        self.assertNotIn('usage', self.run_main('claude', 'PreToolUse', path)['body'])
        self.assertNotIn('usage', self.run_main('codex', 'Stop', path)['body'])

    def test_stop_without_readable_transcript_has_no_usage(self):
        data = self.run_main('claude', 'Stop', str(self.tmp / 'tiada.jsonl'))
        self.assertNotIn('usage', data['body'])


class AntigravityHookTests(HookTestCase):
    def test_tool_args_are_whitelisted_and_prompt_is_hashed(self):
        body = hook.sanitize({
            'conversationId': 'c1',
            'workspacePaths': ['C:\\proj'],
            'lastUserInput': 'tolong buat rahsia',
            'transcriptPath': 'C:\\x\\t.json',
            'toolCall': {'name': 'write_to_file', 'args': {
                'TargetFile': 'app/a.php', 'CodeContent': 'ISI-RAHSIA', 'CommandLine': 'echo Bearer abc123',
            }},
            'error': 'panjang output error yang mungkin ada rahsia',
        })

        self.assertEqual(set(body['toolCall']['args']), {'TargetFile', 'CommandLine'})
        self.assertNotIn('rahsia', json.dumps(body).lower())
        self.assertNotIn('abc123', json.dumps(body))
        self.assertNotIn('lastUserInput', body)
        self.assertEqual(len(body['promptHash']), 12)
        self.assertEqual(body['error'], 'error')
        self.assertEqual(body['workspacePaths'], ['C:\\proj'])

    def test_only_antigravity_prints_json_reply(self):
        self.assertEqual(hook.stdout_reply('antigravity'), '{}')
        for src in ('claude', 'codex', 'hermes', 'generic', None):
            self.assertEqual(hook.stdout_reply(src), '')


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


class AntigravityInstallerTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        (self.home / '.gemini' / 'config').mkdir(parents=True)
        self.path = self.home / '.gemini' / 'config' / 'hooks.json'

    def run_installer(self, *extra):
        args = ['--home', str(self.home), '--tools', 'antigravity', *extra]
        if '--uninstall' not in extra:
            args += ['--url', 'http://127.0.0.1:8000', '--token', 'eod_test']
        with redirect_stdout(io.StringIO()):
            installer.main(args)

    def test_install_adds_event_handlers_without_pre_tool_use(self):
        self.path.write_text(json.dumps({'my-linter': {'enabled': True}}), encoding='utf-8')
        self.run_installer()

        data = json.loads(self.path.read_text(encoding='utf-8'))
        self.assertIn('my-linter', data)
        entry = data['office-hub']
        self.assertTrue(entry['enabled'])
        self.assertEqual(set(entry) - {'enabled'}, {'SessionStart', 'PreInvocation', 'PostToolUse', 'Stop'})
        self.assertNotIn('PreToolUse', entry)

        handler = entry['SessionStart'][0]
        self.assertIn('--src antigravity --event SessionStart', handler['command'])
        self.assertEqual(handler['type'], 'command')
        # Event tool dibungkus dalam kumpulan, event lain senarai handler terus
        self.assertIn('hooks', entry['PostToolUse'][0])
        self.assertIn('--event PostToolUse', entry['PostToolUse'][0]['hooks'][0]['command'])

    def test_command_has_no_quotes_when_paths_have_no_spaces(self):
        # cmd /c rosak dengan "python.exe" "hook.py": mesti tanpa petikan bila boleh
        cmd = installer.cmd_safe_command('C:\\Py\\python.exe', 'C:\\Users\\Helmi\\.office-hub\\office-hook.py', 'antigravity', 'Stop')
        self.assertEqual(cmd, 'C:\\Py\\python.exe C:\\Users\\Helmi\\.office-hub\\office-hook.py --src antigravity --event Stop')
        self.assertNotIn('"', cmd)

    def test_command_with_spaces_is_wrapped_for_cmd(self):
        cmd = installer.cmd_safe_command('C:\\Program Files\\Py\\python.exe', 'C:\\Users\\Ali Baba\\office-hook.py', 'antigravity', 'Stop')
        self.assertIn('"C:\\Program Files\\Py\\python.exe"', cmd)
        if sys.platform == 'win32':
            self.assertTrue(cmd.startswith('""') and cmd.endswith('"'))

    def test_install_is_idempotent_and_uninstall_keeps_other_hooks(self):
        self.path.write_text(json.dumps({'my-linter': {'enabled': True}}), encoding='utf-8')
        self.run_installer()
        first = self.path.read_text(encoding='utf-8')
        self.run_installer()
        self.assertEqual(first, self.path.read_text(encoding='utf-8'))

        self.run_installer('--uninstall')
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8')), {'my-linter': {'enabled': True}})

    def test_dry_run_writes_nothing(self):
        self.run_installer('--dry-run')
        self.assertFalse(self.path.exists())
        self.assertFalse((self.home / '.office-hub').exists())

    def test_skipped_when_antigravity_not_installed(self):
        empty = Path(tempfile.mkdtemp())
        with redirect_stdout(io.StringIO()):
            installer.main(['--home', str(empty), '--tools', 'antigravity', '--url', 'http://x', '--token', 'eod_t'])
        self.assertFalse((empty / '.gemini').exists())


if __name__ == '__main__':
    unittest.main()
