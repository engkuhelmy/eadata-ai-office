#!/usr/bin/env python3
"""install-hooks: pasang / buang hook AI Office Hub untuk Claude Code, Codex dan Hermes.

Contoh:
  python install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes --dry-run
  python install-hooks.py --url http://127.0.0.1:8000 --token eod_xxx --tools claude,codex,hermes
  python install-hooks.py --uninstall --tools claude,codex,hermes

Sifat:
- Backup fail asal ke *.bak-office (sekali sahaja, tak overwrite backup sedia ada).
- Merge, bukan overwrite. Entry kita dikenal pasti dengan 'office-hook' dalam command.
- --dry-run tunjuk diff sahaja. Tak tulis apa-apa.
- Hermes (YAML): tiada PyYAML, jadi guna marker block '# office-hub:begin' / '# office-hub:end'.
"""
import argparse
import difflib
import json
import shutil
import sys
from pathlib import Path

MARK = 'office-hook'
HUB_BEGIN = '# office-hub:begin'
HUB_END = '# office-hub:end'
ALL_TOOLS = ['claude', 'codex', 'hermes', 'antigravity']
HUB_KEY = 'office-hub'  # nama entry hook dalam hooks.json Antigravity

CLAUDE_EVENTS = [
    'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Notification',
    'SubagentStop', 'Stop', 'SessionEnd',
]
CODEX_EVENTS = [
    'SessionStart', 'UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'PermissionRequest',
    'SubagentStart', 'SubagentStop', 'Stop', 'SessionEnd', 'PreCompact',
]
HERMES_EVENTS = [
    'on_session_start', 'pre_llm_call', 'pre_tool_call', 'post_tool_call',
    'subagent_start', 'subagent_stop', 'on_session_end',
]
# Antigravity: stdin tiada nama event, jadi setiap handler bawa --event. PreToolUse sengaja
# TIDAK dipasang: ia wajib pulangkan 'decision' dan boleh mengganggu kelulusan tool.
# True = event tool (bentuk [{matcher?, hooks:[...]}]), False = senarai handler terus.
ANTIGRAVITY_EVENTS = {'SessionStart': False, 'PreInvocation': False, 'PostToolUse': True, 'Stop': False}


class Plan:
    """Kumpul perubahan. Dry-run guna ini, bukan tulis terus."""

    def __init__(self, dry_run):
        self.dry_run = dry_run
        self.actions = []

    def write(self, path, new_text, backup=True):
        path = Path(path)
        old_text = path.read_text(encoding='utf-8') if path.exists() else ''
        if old_text == new_text:
            print(f'  tiada perubahan: {path}')
            return
        if self.dry_run:
            diff = difflib.unified_diff(
                old_text.splitlines(keepends=True), new_text.splitlines(keepends=True),
                fromfile=f'{path} (sekarang)', tofile=f'{path} (selepas)',
            )
            sys.stdout.writelines(diff)
            print()
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        bak = path.with_name(path.name + '.bak-office')
        if backup and path.exists() and not bak.exists():
            shutil.copy2(path, bak)
            print(f'  backup: {bak}')
        path.write_text(new_text, encoding='utf-8')
        print(f'  tulis: {path}')


def is_ours_group(group):
    return any(MARK in str(h.get('command', '')) for h in group.get('hooks', []) if isinstance(h, dict))


def load_json(path):
    if not path.exists():
        return {}
    text = path.read_text(encoding='utf-8').strip()
    return json.loads(text) if text else {}


def dump_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False) + '\n'


def hook_command(python, hook_path, src, event=None):
    command = f'"{python}" "{hook_path}" --src {src}'
    return f'{command} --event {event}' if event else command


def merge_antigravity(data, python, hook_path, uninstall):
    """hooks.json Antigravity: kunci peringkat atas = nama hook. Entry kita: HUB_KEY."""
    data.pop(HUB_KEY, None)
    if uninstall:
        return data

    entry = {'enabled': True}
    for event, is_tool_event in ANTIGRAVITY_EVENTS.items():
        handler = {'type': 'command', 'command': hook_command(python, hook_path, 'antigravity', event), 'timeout': 5}
        entry[event] = [{'hooks': [handler]}] if is_tool_event else [handler]
    data[HUB_KEY] = entry

    return data


def merge_claude(data, command, uninstall):
    hooks = data.setdefault('hooks', {})
    for event in CLAUDE_EVENTS:
        groups = [g for g in hooks.get(event, []) if not is_ours_group(g)]
        if not uninstall:
            groups.append({'matcher': '*', 'hooks': [{'type': 'command', 'command': command, 'async': True}]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop('hooks', None)
    return data


def merge_codex(data, command, uninstall):
    hooks = data.setdefault('hooks', {})
    for event in CODEX_EVENTS:
        groups = [g for g in hooks.get(event, []) if not is_ours_group(g)]
        if not uninstall:
            handler = {'type': 'command', 'command': command, 'timeout': 3}
            # SessionEnd sentiasa sync (default 1s). Event lain jalan di background.
            if event != 'SessionEnd':
                handler['async'] = True
            groups.append({'hooks': [handler]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        data.pop('hooks', None)
    return data


def hermes_block(command):
    lines = [HUB_BEGIN, 'hooks:']
    for event in HERMES_EVENTS:
        lines.append(f'  {event}:')
        lines.append(f'    - command: \'{command}\'')
        lines.append('      timeout: 5')
    lines.append(HUB_END)
    return '\n'.join(lines) + '\n'


def strip_hub_block(text):
    out, skipping = [], False
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == HUB_BEGIN:
            skipping = True
            continue
        if stripped == HUB_END:
            skipping = False
            continue
        if not skipping:
            out.append(line)
    return ''.join(out)


def merge_hermes_text(text, command, uninstall):
    base = strip_hub_block(text)
    has_top_hooks = any(line.rstrip() == 'hooks:' for line in base.splitlines())
    if uninstall:
        return base
    if has_top_hooks:
        raise SystemExit(
            'config.yaml dah ada blok "hooks:" di luar marker. Tambah manual, '
            'atau tampal isi blok office-hub di bawah ke dalam blok hooks sedia ada:\n'
            + hermes_block(command)
        )
    if base and not base.endswith('\n'):
        base += '\n'
    return base + hermes_block(command)


def install_tool(tool, plan, args, home, python, hook_path, uninstall):
    command = hook_command(python, hook_path, tool)

    if tool == 'claude':
        path = home / '.claude' / 'settings.json'
        if not path.parent.exists() and not uninstall:
            print(f'  skip claude: {path.parent} tak wujud')
            return
        new = merge_claude(load_json(path), command, uninstall)
        plan.write(path, dump_json(new))

    elif tool == 'codex':
        path = home / '.codex' / 'hooks.json'
        if not path.parent.exists() and not uninstall:
            print(f'  skip codex: {path.parent} tak wujud')
            return
        new = merge_codex(load_json(path), command, uninstall)
        plan.write(path, dump_json(new))
        if not uninstall:
            print('  Codex: buka `codex`, jalankan `/hooks`, dan trust hook office-hub.')

    elif tool == 'antigravity':
        path = home / '.gemini' / 'config' / 'hooks.json'
        if not path.parent.exists() and not uninstall:
            print(f'  skip antigravity: {path.parent} tak wujud (Antigravity belum dipasang)')
            return
        new = merge_antigravity(load_json(path), python, hook_path, uninstall)
        plan.write(path, dump_json(new))
        if not uninstall:
            print('  Antigravity: mula sesi baru, jalankan `/hooks` dalam CLI untuk sahkan hook office-hub aktif.')

    elif tool == 'hermes':
        path = home / '.hermes' / 'config.yaml'
        if not path.exists():
            print(f'  skip hermes: {path} tak wujud (Hermes belum dipasang)')
            return
        text = path.read_text(encoding='utf-8')
        plan.write(path, merge_hermes_text(text, command, uninstall))
        if not uninstall:
            print('  Hermes: run `hermes hooks test pre_tool_call`. Kali pertama, approve hook')
            print('          atau guna --accept-hooks. Allowlist: ~/.hermes/shell-hooks-allowlist.json')


def install_hub_files(plan, home, url, token, hook_source):
    hub = home / '.office-hub'
    hook_dst = hub / 'office-hook.py'
    config_path = hub / 'config.json'
    config = {'url': url.rstrip('/'), 'token': token}

    if plan.dry_run:
        print(f'  akan salin {hook_source} -> {hook_dst}')
        print(f'  akan tulis config {config_path} (token disembunyikan)')
        return hook_dst

    hub.mkdir(parents=True, exist_ok=True)
    shutil.copy2(hook_source, hook_dst)
    config_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    print(f'  hook disalin: {hook_dst}')
    print(f'  config: {config_path}')
    return hook_dst


def main(argv=None):
    parser = argparse.ArgumentParser(description='Pasang hook AI Office Hub.')
    parser.add_argument('--url', help='URL server, cth. http://127.0.0.1:8000')
    parser.add_argument('--token', help='Device token (eod_...) dari `php artisan office:device`')
    parser.add_argument('--tools', default=','.join(ALL_TOOLS), help='claude,codex,hermes')
    parser.add_argument('--uninstall', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--home', help=argparse.SUPPRESS)  # untuk test
    args = parser.parse_args(argv)

    tools = [t.strip() for t in args.tools.split(',') if t.strip()]
    unknown = [t for t in tools if t not in ALL_TOOLS]
    if unknown:
        parser.error(f'tool tak dikenali: {unknown}')
    if not args.uninstall and (not args.url or not args.token):
        parser.error('--url dan --token diperlukan untuk pasang')

    home = Path(args.home) if args.home else Path.home()
    here = Path(__file__).resolve().parent
    hook_source = here / 'office-hook.py'
    python = sys.executable
    plan = Plan(args.dry_run)
    mode = 'DRY-RUN' if args.dry_run else ('UNINSTALL' if args.uninstall else 'INSTALL')
    print(f'== office-hub {mode} untuk: {", ".join(tools)}')

    hub = home / '.office-hub'
    hook_path = hub / 'office-hook.py'

    if not args.uninstall:
        hook_path = install_hub_files(plan, home, args.url, args.token, hook_source)

    for tool in tools:
        print(f'-- {tool}')
        install_tool(tool, plan, args, home, python, hook_path, args.uninstall)

    if args.uninstall:
        print('Config dan spool di ~/.office-hub dibiarkan. Buang manual kalau nak.')
    print('Selesai.' if not args.dry_run else 'Dry-run siap. Tiada fail ditulis.')


if __name__ == '__main__':
    main()
