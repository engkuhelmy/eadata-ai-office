<?php

namespace App\Office\Adapters;

use App\Office\NormalizedEvent;

/**
 * Codex CLI.
 * - hooks.json (~/.codex/hooks.json): stdin ada hook_event_name, session_id, cwd, tool_name, tool_input, tool_response.
 * - Legacy notify: payload type=agent-turn-complete, thread-id. Hanya turn_done.
 * Schema dari docs rasmi (learn.chatgpt.com/docs/hooks). Sahkan dengan payload sebenar bila Codex dipasang.
 */
class CodexAdapter extends BaseAdapter
{
    public function vendor(): string
    {
        return 'codex';
    }

    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent
    {
        if (isset($payload['hook_event_name'])) {
            return $this->fromHook($payload);
        }

        return $this->fromLegacyNotify($payload, $eventHint);
    }

    private function fromHook(array $payload): ?NormalizedEvent
    {
        $sid = $this->str($payload, 'session_id');
        if ($sid === null) {
            return null;
        }

        $hook = (string) $payload['hook_event_name'];
        $tool = $this->str($payload, 'tool_name');
        $input = is_array($payload['tool_input'] ?? null) ? $payload['tool_input'] : [];
        $command = $this->str($input, 'command');
        $path = $this->str($input, 'file_path') ?? $this->str($input, 'path');

        $event = match ($hook) {
            'SessionStart' => 'session_start',
            'UserPromptSubmit' => 'prompt',
            'PreToolUse' => 'tool_start',
            'PostToolUse' => $this->isToolError($payload) ? 'tool_error' : 'tool_end',
            'PermissionRequest' => 'needs_approval',
            'SubagentStart' => 'subagent_start',
            'SubagentStop' => 'subagent_stop',
            'Stop' => 'turn_done',
            'PreCompact' => 'compact',
            'SessionEnd' => 'session_end',
            default => null,
        };

        if ($event === null) {
            return null;
        }

        return $this->build($sid, $payload, $event, $tool, $command ?? $path, $this->router->route($event, $tool, $path, $command));
    }

    private function fromLegacyNotify(array $payload, ?string $eventHint): ?NormalizedEvent
    {
        $isLegacyTurnDone = ($payload['type'] ?? null) === 'agent-turn-complete' || $eventHint === 'turn_done';
        if (! $isLegacyTurnDone) {
            return null;
        }

        $sid = $this->str($payload, 'thread-id') ?? $this->str($payload, 'session_id');
        if ($sid === null) {
            return null;
        }

        return $this->build($sid, $payload, 'turn_done', null, null, $this->router->route('turn_done'));
    }

    private function build(string $sid, array $payload, string $event, ?string $tool, ?string $target, ?string $department): NormalizedEvent
    {
        return new NormalizedEvent(
            vendor: $this->vendor(),
            agentKey: $sid,
            name: 'Codex '.substr($sid, 0, 4),
            label: 'Codex',
            pc: $this->pc($payload),
            project: $this->projectFromCwd($payload['cwd'] ?? null),
            event: $event,
            tool: $tool,
            target: $this->redactor->target($target),
            department: $department,
            ts: $this->ts($payload),
        );
    }

    private function isToolError(array $payload): bool
    {
        $response = $payload['tool_response'] ?? null;

        return is_array($response)
            && (($response['is_error'] ?? false) === true || ($response['success'] ?? true) === false);
    }
}
