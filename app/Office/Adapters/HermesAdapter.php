<?php

namespace App\Office\Adapters;

use App\Office\NormalizedEvent;
use Illuminate\Support\Facades\Cache;

class HermesAdapter extends BaseAdapter
{
    public function vendor(): string
    {
        return 'hermes';
    }

    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent
    {
        $sid = $this->str($payload, 'session_id');
        if ($sid === null) {
            return null;
        }

        $hook = (string) ($payload['hook_event_name'] ?? '');
        $extra = is_array($payload['extra'] ?? null) ? $payload['extra'] : [];
        $input = is_array($payload['tool_input'] ?? null) ? $payload['tool_input'] : [];
        $rawTool = $this->str($payload, 'tool_name');

        $event = match ($hook) {
            'on_session_start' => 'session_start',
            'pre_llm_call' => $this->isNewTurn($sid, $extra) ? 'prompt' : null,
            'pre_tool_call' => 'tool_start',
            'post_tool_call' => $this->hasError($extra) ? 'tool_error' : 'tool_end',
            'subagent_start' => 'subagent_start',
            'subagent_stop' => 'subagent_stop',
            'on_session_end' => ($extra['interrupted'] ?? false) === true ? 'idle' : 'session_end',
            default => null,
        };

        if ($event === null) {
            return null;
        }

        $tool = $rawTool !== null ? $this->canonicalTool($rawTool) : null;
        $command = $this->str($input, 'command');
        $path = $this->str($input, 'file_path') ?? $this->str($input, 'path');

        $profile = (string) ($payload['profile'] ?? 'default');
        $label = 'Hermes'.($profile !== '' && $profile !== 'default' ? " ({$profile})" : '');

        return new NormalizedEvent(
            vendor: $this->vendor(),
            agentKey: $sid,
            name: $label,
            label: $label,
            pc: $this->pc($payload),
            project: $this->projectFromCwd($payload['cwd'] ?? null),
            event: $event,
            tool: $tool,
            target: $this->redactor->target($command ?? $path),
            department: $this->router->route($event, $tool, $path, $command),
            ts: $this->ts($payload),
        );
    }

    /**
     * pre_llm_call datang berkali-kali dalam satu turn. Accept sekali per turn.
     * Turn dikenal pasti guna extra.task_id. Kalau tiada, accept sekali setiap 30 saat.
     */
    private function isNewTurn(string $sid, array $extra): bool
    {
        $key = "office:hermes:turn:{$sid}";
        $state = Cache::get($key, []);
        $turn = isset($extra['task_id']) ? (string) $extra['task_id'] : null;

        if ($turn !== null) {
            if (($state['turn'] ?? null) === $turn) {
                return false;
            }
        } elseif (time() - (int) ($state['at'] ?? 0) < 30) {
            return false;
        }

        Cache::put($key, ['turn' => $turn, 'at' => time()], now()->addDay());

        return true;
    }

    private function hasError(array $extra): bool
    {
        return ! empty($extra['error'])
            || ($extra['status'] ?? null) === 'error'
            || ($extra['failed'] ?? false) === true;
    }

    /** Nama tool Hermes → nama kanonik untuk DepartmentRouter (sumber: brief 5.3). */
    private function canonicalTool(string $tool): string
    {
        $lower = strtolower($tool);

        return match (true) {
            // write_file, patch, read_file: department ikut extension path
            in_array($tool, ['write_file', 'patch', 'read_file'], true) => 'Edit',
            $tool === 'terminal' => 'Bash',
            $tool === 'delegate_task' => 'Task',
            str_contains($lower, 'web'), str_contains($lower, 'browser'), str_contains($lower, 'search') => 'WebSearch',
            default => $tool,
        };
    }
}
