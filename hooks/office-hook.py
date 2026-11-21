#!/usr/bin/env python3
"""office-hook: tangkap event agent, redact, hantar ke AI Office Hub.

- Stdlib sahaja. Tiada stdout. Sentiasa exit 0.
- Parent proses: baca stdin, redact, spawn child di background, return segera.
- Child (--send): POST ke server, timeout 3s. Gagal -> spool. Berjaya -> flush spool (max 100).
- Log ke ~/.office-hub/hook.log (rotate 1MB), bukan stdout/stderr.
"""
import datetime
import hashlib
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOME_DIR = Path(os.environ.get('OFFICE_HUB_HOME') or (Path.home() / '.office-hub'))
CONFIG_FILE = HOME_DIR / 'config.json'
SPOOL_FILE = HOME_DIR / 'spool.jsonl'
SPOOL_LOCK = HOME_DIR / 'spool.lock'
LOG_FILE = HOME_DIR / 'hook.log'

LOG_MAX_BYTES = 1024 * 1024
MAX_STDIN_BYTES = 1024 * 1024
SEND_TIMEOUT = 3
SPOOL_FLUSH_MAX = 100
MAX_TARGET_CHARS = 200

# Field yang TAK PERNAH dihantar (isi fail, prompt, transkrip)
DROP_KEYS = {
    'content', 'new_string', 'old_string', 'patch', 'file_text', 'body',
    'prompt', 'transcript_path', 'last-assistant-message', 'input-messages',
    # Antigravity (camelCase)
    'transcriptPath', 'lastUserInput', 'artifactDirectoryPath',
}
# Argumen toolCall Antigravity yang dibenarkan (huruf kecil). Selebihnya (isi fail, replacement) dibuang.
TOOL_ARG_KEYS = {
    'commandline', 'command', 'cwd', 'targetfile', 'absolutepath', 'path', 'filepath', 'file_path',
    'directorypath', 'searchpath', 'url', 'query', 'pattern',
}
# Field tool_input yang dibenarkan
TOOL_INPUT_KEYS = {'file_path', 'path', 'command', 'pattern', 'query', 'url', 'subagent_type', 'description'}

SECRET_PATTERNS = [
    (re.compile(r'sk-[A-Za-z0-9_\-]{16,}'), 'sk-***'),
    (re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'), 'gh_***'),
    (re.compile(r'AKIA[0-9A-Z]{16}'), 'AKIA***'),
    (re.compile(r'\bBearer\s+\S+', re.I), 'Bearer ***'),
    (re.compile(r'\b(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)\S+', re.I), r'\1\2***'),
]
ENV_LINE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)=\S*$', re.M)

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def log(message):
    try:
        HOME_DIR.mkdir(parents=True, exist_ok=True)
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > LOG_MAX_BYTES:
            LOG_FILE.replace(LOG_FILE.with_name('hook.log.1'))
        stamp = datetime.datetime.now().isoformat(timespec='seconds')
        with LOG_FILE.open('a', encoding='utf-8') as fh:
            fh.write(f'{stamp} {message}\n')
    except Exception:
        pass


def redact_text(text):
    text = ENV_LINE.sub(r'\1=***', text)
    for pattern, replacement in SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(value):
    """Buang field sensitif, mask secret dalam semua string, rekursif."""
    if isinstance(value, dict):
        return {k: redact(v) for k, v in value.items() if k not in DROP_KEYS}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def sanitize(payload):
    """Bentuk payload selamat: tool_input ditapis, tool_response hanya status."""
    body = redact(payload)

    tool_input = payload.get('tool_input')
    if isinstance(tool_input, dict):
        body['tool_input'] = {
            k: redact_text(str(v))[:MAX_TARGET_CHARS * 5] if k == 'command' else redact_text(str(v))
            for k, v in tool_input.items()
            if k in TOOL_INPUT_KEYS
        }

    tool_response = payload.get('tool_response')
    if 'tool_response' in payload:
        status = {}
        if isinstance(tool_response, dict):
            for key in ('is_error', 'success'):
                if key in tool_response:
                    status[key] = tool_response[key]
        body['tool_response'] = status

    # Antigravity: toolCall.args ditapis, input pengguna jadi hash sahaja, error jadi penanda
    tool_call = payload.get('toolCall')
    if isinstance(tool_call, dict):
        args = tool_call.get('args')
        body['toolCall'] = {
            'name': str(tool_call.get('name', '')),
            'args': {
                k: redact_text(str(v))
                for k, v in (args.items() if isinstance(args, dict) else [])
                if str(k).lower() in TOOL_ARG_KEYS
            },
        }
    if 'lastUserInput' in payload:
        body['promptHash'] = hashlib.sha1(str(payload['lastUserInput']).encode('utf-8', 'replace')).hexdigest()[:12]
    if 'error' in payload:
        body['error'] = 'error' if payload.get('error') else ''

    body['pc'] = socket.gethostname()
    body['ts'] = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
    return body


def read_payload(argv):
    """Stdin JSON. Codex legacy notify hantar JSON sebagai argumen terakhir."""
    for arg in argv:
        if arg.startswith('{'):
            try:
                return json.loads(arg)
            except ValueError:
                pass
    if sys.stdin is None or sys.stdin.isatty():
        return {}
    # utf-8-sig: buang BOM kalau ada (PowerShell pipe selalu letak BOM)
    raw = sys.stdin.buffer.read(MAX_STDIN_BYTES).decode('utf-8-sig', errors='replace')
    return json.loads(raw) if raw.strip() else {}


def load_config():
    return json.loads(CONFIG_FILE.read_text(encoding='utf-8-sig'))


def ingest_url(config, src, event):
    query = {'src': src}
    if event:
        query['event'] = event
    return config['url'].rstrip('/') + '/api/ingest?' + urllib.parse.urlencode(query)


def post(config, src, event, body):
    request = urllib.request.Request(
        ingest_url(config, src, event),
        data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f"Bearer {config['token']}",
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=SEND_TIMEOUT) as resp:
            return 200 <= resp.status < 300
    except urllib.error.HTTPError as exc:
        # 4xx (token salah, payload tak dikenali) tak boleh diulang: buang, jangan spool
        log(f'server reject {exc.code} src={src} event={event}')
        return True
    except Exception as exc:
        log(f'send gagal src={src}: {exc.__class__.__name__}')
        return False


def spool_append(src, event, body):
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    with SPOOL_FILE.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps({'src': src, 'event': event, 'body': body}, ensure_ascii=False) + '\n')


def acquire_lock():
    try:
        fd = os.open(str(SPOOL_LOCK), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        try:
            if datetime.datetime.now().timestamp() - SPOOL_LOCK.stat().st_mtime > 60:
                SPOOL_LOCK.unlink()
        except OSError:
            pass
        return False


def release_lock():
    try:
        SPOOL_LOCK.unlink()
    except OSError:
        pass


def flush_spool(config):
    if not SPOOL_FILE.exists() or not acquire_lock():
        return
    try:
        lines = SPOOL_FILE.read_text(encoding='utf-8').splitlines()
        batch, rest = lines[:SPOOL_FLUSH_MAX], lines[SPOOL_FLUSH_MAX:]
        sent = 0
        for line in batch:
            try:
                item = json.loads(line)
            except ValueError:
                sent += 1
                continue
            if not post(config, item['src'], item.get('event'), item['body']):
                break
            sent += 1
        remaining = batch[sent:] + rest
        if remaining:
            SPOOL_FILE.write_text('\n'.join(remaining) + '\n', encoding='utf-8')
        else:
            SPOOL_FILE.unlink()
        if sent:
            log(f'spool flush {sent} event')
    finally:
        release_lock()


def send_mode():
    """Child: dipanggil dengan --send, data dibaca dari stdin."""
    data = json.loads(sys.stdin.buffer.read().decode('utf-8-sig') or '{}')
    config = load_config()
    src, event, body = data['src'], data.get('event'), data['body']

    if post(config, src, event, body):
        flush_spool(config)
    else:
        spool_append(src, event, body)


def spawn_background(data):
    kwargs = {'stdin': subprocess.PIPE, 'stdout': subprocess.DEVNULL, 'stderr': subprocess.DEVNULL, 'close_fds': True}
    if os.name == 'nt':
        kwargs['creationflags'] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW
    else:
        kwargs['start_new_session'] = True

    child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--send'], **kwargs)
    child.stdin.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    child.stdin.close()


def parse_args(argv):
    src, event = None, None
    it = iter(argv)
    for arg in it:
        if arg == '--src':
            src = next(it, None)
        elif arg == '--event':
            event = next(it, None)
    return src, event


def main(argv):
    if '--send' in argv:
        send_mode()
        return

    src, event = parse_args(argv)
    if not src:
        log('--src tiada, skip')
        return

    payload = read_payload(argv)
    body = sanitize(payload if isinstance(payload, dict) else {})
    data = {'src': src, 'event': event, 'body': body}

    # Tangkap payload (sudah ditapis) untuk dijadikan fixture: OFFICE_HOOK_CAPTURE=1
    if os.environ.get('OFFICE_HOOK_CAPTURE'):
        try:
            HOME_DIR.mkdir(parents=True, exist_ok=True)
            with (HOME_DIR / 'captured.jsonl').open('a', encoding='utf-8') as fh:
                fh.write(json.dumps(data, ensure_ascii=False) + '\n')
        except Exception:
            pass

    try:
        spawn_background(data)
    except Exception as exc:
        # Fallback: simpan dalam spool supaya tak hilang
        log(f'spawn gagal ({exc.__class__.__name__}), spool terus')
        spool_append(src, event, body)


def stdout_reply(src):
    """Hanya Antigravity mahu JSON pada stdout ({} = tiada keputusan). Vendor lain: kosong
    (Hermes baca stdout sebagai arahan, jadi MESTI kosong)."""
    return '{}' if src == 'antigravity' else ''


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as exc:
        log(f'hook error: {exc.__class__.__name__}: {exc}')
    try:
        reply = stdout_reply(parse_args(sys.argv[1:])[0])
        if reply:
            sys.stdout.write(reply)
            sys.stdout.flush()
    except Exception:
        pass
    sys.exit(0)
