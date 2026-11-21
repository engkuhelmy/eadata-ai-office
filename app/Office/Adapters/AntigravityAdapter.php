<?php

namespace App\Office\Adapters;

use App\Office\NormalizedEvent;
use Illuminate\Support\Facades\Cache;

/**
 * Google Antigravity (CLI `agy`, IDE, app). Schema dari docs rasmi antigravity.google/docs/hooks:
 * stdin camelCase (conversationId, workspacePaths, toolCall{name,args}, error, fullyIdle, ...).
 * Stdin TIADA nama event, jadi office-hook dipasang dengan `--event <Nama>` dan dihantar sebagai ?event=.
 * Nama tool dan nama argumen belum disahkan dengan payload sebenar: dipetakan secara heuristik.
 * Gemini CLI (BeforeTool/AfterTool) sudah diganti Antigravity CLI, jadi tidak disokong di sini.
 */
class AntigravityAdapter extends BaseAdapter
{
    private const COMMAND_ARGS = ['commandline', 'command'];

    private const PATH_ARGS = ['targetfile', 'absolutepath', 'path', 'filepath', 'file_path', 'directorypath', 'searchpath'];

    public function vendor(): string
    {
        return 'antigravity';
    }

    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent
    {
        $sid = $this->str($payload, 'conversationId');
        if ($sid === null) {
            return null;
        }

        $event = match ($eventHint) {
            'SessionStart' => 'session_start',
            'PreInvocation' => $this->isNewPrompt($sid, $payload) ? 'prompt' : null,
            'PostToolUse' => $this->str($payload, 'error') !== null ? 'tool_error' : 'tool_end',
            'Stop' => ($payload['fullyIdle'] ?? false) === true ? 'turn_done' : null,
            default => null,
        };

        if ($event === null) {
            return null;
        }

        $call = is_array($payload['toolCall'] ?? null) ? $payload['toolCall'] : [];
        $args = is_array($call['args'] ?? null) ? $call['args'] : [];
        $rawTool = $this->str($call, 'name');
        $tool = $rawTool !== null ? $this->canonicalTool($rawTool) : null;
        $command = $this->firstArg($args, self::COMMAND_ARGS);
        $path = $this->firstArg($args, self::PATH_ARGS);

        $workspace = is_array($payload['workspacePaths'] ?? null) ? ($payload['workspacePaths'][0] ?? null) : null;

        return new NormalizedEvent(
            vendor: $this->vendor(),
            agentKey: $sid,
            name: 'Antigravity '.substr($sid, 0, 4),
            label: 'Antigravity',
            pc: $this->pc($payload),
            project: $this->projectFromCwd($workspace),
            event: $event,
            tool: $tool,
            target: $this->redactor->target($command ?? $path),
            department: $this->router->route($event, $tool, $path, $command),
            ts: $this->ts($payload),
        );
    }

    /** PreInvocation datang untuk setiap panggilan model. Accept sekali setiap input pengguna baru. */
    private function isNewPrompt(string $sid, array $payload): bool
    {
        $key = "office:antigravity:prompt:{$sid}";
        $state = Cache::get($key, []);
        $hash = $this->str($payload, 'promptHash');

        if ($hash !== null) {
            if (($state['hash'] ?? null) === $hash) {
                return false;
            }
        } elseif (time() - (int) ($state['at'] ?? 0) < 30) {
            return false;
        }

        Cache::put($key, ['hash' => $hash, 'at' => time()], now()->addDay());

        return true;
    }

    private function firstArg(array $args, array $names): ?string
    {
        foreach ($args as $key => $value) {
            if (in_array(strtolower((string) $key), $names, true) && is_scalar($value) && (string) $value !== '') {
                return (string) $value;
            }
        }

        return null;
    }

    /** Nama tool Antigravity -> nama kanonik untuk DepartmentRouter (heuristik, belum disahkan). */
    private function canonicalTool(string $tool): string
    {
        $t = strtolower($tool);

        return match (true) {
            str_contains($t, 'run_command'), str_contains($t, 'command'), $t === 'bash', $t === 'shell' => 'Bash',
            str_contains($t, 'write'), str_contains($t, 'replace'), str_contains($t, 'edit') => 'Edit',
            str_contains($t, 'url'), str_contains($t, 'web'), str_contains($t, 'browser') => 'WebSearch',
            str_contains($t, 'view'), str_contains($t, 'read'), str_contains($t, 'list'),
            str_contains($t, 'grep'), str_contains($t, 'find'), str_contains($t, 'search') => 'Read',
            default => $tool,
        };
    }
}
