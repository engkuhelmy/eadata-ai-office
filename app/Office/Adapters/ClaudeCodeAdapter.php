<?php

namespace App\Office\Adapters;

use App\Office\NormalizedEvent;

class ClaudeCodeAdapter extends BaseAdapter
{
    private const SUBAGENT_TOOLS = ['Task', 'Agent'];

    public function vendor(): string
    {
        return 'claude';
    }

    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent
    {
        $sid = $this->str($payload, 'session_id');
        if ($sid === null) {
            return null;
        }

        $hook = (string) ($payload['hook_event_name'] ?? '');
        $tool = $this->str($payload, 'tool_name');
        $input = is_array($payload['tool_input'] ?? null) ? $payload['tool_input'] : [];

        // Isi fail (content, old_string, new_string, patch) TIDAK diambil. Path/command sahaja.
        $command = $this->str($input, 'command');
        $path = $this->str($input, 'file_path') ?? $this->str($input, 'path');

        $event = match ($hook) {
            'SessionStart' => 'session_start',
            'UserPromptSubmit' => 'prompt',
            'PreToolUse' => in_array($tool, self::SUBAGENT_TOOLS, true) ? 'subagent_start' : 'tool_start',
            'PostToolUse' => $this->isToolError($payload) ? 'tool_error' : 'tool_end',
            'Notification' => $this->isPermission($payload) ? 'needs_approval' : null,
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

        $department = $this->router->route($event, $tool, $path, $command);

        return new NormalizedEvent(
            vendor: $this->vendor(),
            agentKey: $sid,
            name: 'Claude '.substr($sid, 0, 4),
            label: 'Claude Code',
            pc: $this->pc($payload),
            project: $this->projectFromCwd($payload['cwd'] ?? null),
            event: $event,
            tool: $tool,
            target: $this->redactor->target($command ?? $path),
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

    private function isPermission(array $payload): bool
    {
        $message = (string) ($payload['message'] ?? '');

        return str_contains(strtolower($message), 'permission');
    }
}
