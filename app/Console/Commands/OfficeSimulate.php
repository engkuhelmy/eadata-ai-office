<?php

namespace App\Console\Commands;

use App\Jobs\ProcessAgentEvent;
use App\Office\AdapterRegistry;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

class OfficeSimulate extends Command
{
    protected $signature = 'office:simulate
        {--ticks=40 : Bilangan event yang dihantar}
        {--delay=2 : Jeda (saat) antara event}
        {--sync : Proses terus tanpa queue worker}';

    protected $description = 'Hantar event palsu untuk team 5 agent (Claude x2, Codex, Hermes, Generic)';

    /** Team tetap: 5 agent dalam satu projek. */
    private array $team = [];

    public function handle(AdapterRegistry $registry): int
    {
        $project = 'eadata-web';
        $cwd = 'C:\\Users\\Helmi\\projek\\'.$project;
        $pc = gethostname() ?: 'pc-sim';

        $this->team = [
            ['vendor' => 'claude', 'sid' => 'sim-claude-a1', 'cwd' => $cwd],
            ['vendor' => 'claude', 'sid' => 'sim-claude-b2', 'cwd' => $cwd],
            ['vendor' => 'codex', 'sid' => 'sim-codex-c3', 'cwd' => $cwd],
            ['vendor' => 'hermes', 'sid' => 'sim-hermes-d4', 'cwd' => $cwd],
            ['vendor' => 'generic', 'sid' => 'researcher-1', 'cwd' => $cwd],
        ];

        $ticks = (int) $this->option('ticks');
        $delay = (int) $this->option('delay');

        // Mula semua staff (clock in di pintu)
        foreach ($this->team as $member) {
            $this->dispatchFor($registry, $member, $this->payloadFor($member, 'start'), $pc);
        }

        for ($i = 0; $i < $ticks; $i++) {
            $member = $this->team[array_rand($this->team)];
            $step = $this->randomStep($member['vendor']);
            $this->dispatchFor($registry, $member, $this->payloadFor($member, $step), $pc);

            if ($delay > 0 && $i < $ticks - 1) {
                sleep($delay);
            }
        }

        $this->info('Simulasi selesai. Pastikan `php artisan queue:work` jalan (atau guna --sync).');

        return self::SUCCESS;
    }

    private function dispatchFor(AdapterRegistry $registry, array $member, array $payload, string $pc): void
    {
        $payload['pc'] = $pc;
        $payload['ts'] = now()->toIso8601String();

        $event = $registry->get($member['vendor'])->normalize($payload);
        if ($event === null) {
            $this->warn("Payload {$member['vendor']} tak dikenali, skip.");

            return;
        }

        $this->line("[{$member['vendor']}] {$event->event} ".($event->tool ?? '').' '.($event->target ?? ''));

        $this->option('sync')
            ? ProcessAgentEvent::dispatchSync($event)
            : ProcessAgentEvent::dispatch($event);
    }

    private function randomStep(string $vendor): string
    {
        $steps = match ($vendor) {
            'claude' => ['prompt', 'edit_vue', 'edit_php', 'bash_test', 'bash_deploy', 'read', 'subagent', 'approval', 'stop', 'error'],
            'codex' => ['stop'],
            'hermes' => ['prompt', 'edit_php', 'bash_test', 'web', 'stop'],
            default => ['tool_start_web', 'tool_end_web'],
        };

        return $steps[array_rand($steps)];
    }

    /** Payload ikut bentuk mentah tiap vendor (sama macam hook sebenar). */
    private function payloadFor(array $member, string $step): array
    {
        $sid = $member['sid'];
        $cwd = $member['cwd'];

        return match ($member['vendor']) {
            'claude' => $this->claudePayload($sid, $cwd, $step),
            'codex' => ['type' => 'agent-turn-complete', 'thread-id' => $sid, 'cwd' => $cwd],
            'hermes' => $this->hermesPayload($sid, $cwd, $step),
            default => $this->genericPayload($sid, $step),
        };
    }

    private function claudePayload(string $sid, string $cwd, string $step): array
    {
        $base = ['session_id' => $sid, 'cwd' => $cwd];

        return $base + match ($step) {
            'start' => ['hook_event_name' => 'SessionStart'],
            'prompt' => ['hook_event_name' => 'UserPromptSubmit', 'prompt' => 'contoh prompt'],
            'edit_vue' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Edit', 'tool_input' => ['file_path' => 'resources/js/components/Navbar.vue']],
            'edit_php' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Write', 'tool_input' => ['file_path' => 'app/Http/Controllers/UserController.php']],
            'bash_test' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Bash', 'tool_input' => ['command' => 'php artisan test']],
            'bash_deploy' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Bash', 'tool_input' => ['command' => 'git push origin main']],
            'read' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Read', 'tool_input' => ['file_path' => 'routes/web.php']],
            'subagent' => ['hook_event_name' => 'PreToolUse', 'tool_name' => 'Task', 'tool_input' => ['description' => 'research']],
            'approval' => ['hook_event_name' => 'Notification', 'message' => 'Claude needs your permission to use Bash'],
            'error' => ['hook_event_name' => 'PostToolUse', 'tool_name' => 'Bash', 'tool_input' => ['command' => 'npm run build'], 'tool_response' => ['is_error' => true]],
            default => ['hook_event_name' => 'Stop'],
        };
    }

    private function hermesPayload(string $sid, string $cwd, string $step): array
    {
        $base = ['session_id' => $sid, 'cwd' => $cwd, 'profile' => 'default', 'extra' => ['task_id' => 'task-'.Str::random(6)]];

        return $base + match ($step) {
            'start' => ['hook_event_name' => 'on_session_start', 'extra' => []],
            'prompt' => ['hook_event_name' => 'pre_llm_call'],
            'edit_php' => ['hook_event_name' => 'pre_tool_call', 'tool_name' => 'patch', 'tool_input' => ['path' => 'app/Office/Redactor.php']],
            'bash_test' => ['hook_event_name' => 'pre_tool_call', 'tool_name' => 'terminal', 'tool_input' => ['command' => 'pytest -q']],
            'web' => ['hook_event_name' => 'pre_tool_call', 'tool_name' => 'web_search', 'tool_input' => ['query' => 'harga VPS']],
            default => ['hook_event_name' => 'on_session_end', 'extra' => ['interrupted' => false]],
        };
    }

    private function genericPayload(string $agent, string $step): array
    {
        $base = ['agent' => $agent, 'name' => 'Rafiq', 'label' => 'CrewAI', 'project' => 'eadata-web'];

        return $base + match ($step) {
            'start' => ['event' => 'session_start'],
            'tool_end_web' => ['event' => 'tool_end', 'tool' => 'web_search', 'target' => 'harga VPS Malaysia', 'department' => 'research'],
            default => ['event' => 'tool_start', 'tool' => 'web_search', 'target' => 'harga VPS Malaysia', 'department' => 'research'],
        };
    }
}
