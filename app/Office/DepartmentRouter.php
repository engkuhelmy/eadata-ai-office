<?php

namespace App\Office;

class DepartmentRouter
{
    public const DEPARTMENTS = [
        'door', 'kanban', 'frontend', 'backend', 'qa', 'deploy', 'research',
        'ops', 'meeting', 'approval', 'coffee', 'water_cooler',
    ];

    private const FRONTEND_EXT = ['vue', 'tsx', 'jsx', 'css', 'scss', 'html'];
    private const BACKEND_EXT = ['php', 'py', 'go', 'rs'];
    private const JS_EXT = ['js', 'ts'];
    private const BACKEND_DIRS = ['routes/', 'api/', 'app/'];
    private const EDIT_TOOLS = ['edit', 'write', 'multiedit', 'notebookedit', 'patch', 'write_file'];
    private const READ_TOOLS = ['read', 'grep', 'glob', 'websearch', 'webfetch', 'web_search', 'web_fetch', 'browser'];
    private const MEETING_TOOLS = ['task', 'agent', 'delegate_task'];
    private const SHELL_TOOLS = ['bash', 'terminal', 'shell', 'run_command'];
    private const TEST_CMD = '/\b(phpunit|pest|jest|vitest|pytest)\b|\bartisan\s+test\b/i';
    private const DEPLOY_CMD = '/\b(git\s+push|docker|ssh|pm2|deploy|rsync|kubectl)\b/i';

    /**
     * Teka department dari event + tool + target. Null = kekal di meja sekarang.
     * $explicit: department yang dihantar terus oleh payload (generic).
     */
    public function route(
        string $event,
        ?string $tool = null,
        ?string $target = null,
        ?string $command = null,
        ?string $explicit = null,
    ): ?string {
        if ($explicit !== null && in_array($explicit, self::DEPARTMENTS, true)) {
            return $explicit;
        }

        return match ($event) {
            'session_start', 'session_end' => 'door',
            'prompt' => 'kanban',
            'needs_approval' => 'approval',
            'rate_limited' => 'coffee',
            'idle', 'turn_done' => 'water_cooler',
            'subagent_start', 'subagent_stop' => 'meeting',
            'tool_error' => $this->isTestPath($target) ? 'qa' : null,
            'tool_start', 'tool_end' => $this->forTool($tool, $target, $command),
            default => null,
        };
    }

    private function forTool(?string $tool, ?string $target, ?string $command): string
    {
        $t = strtolower((string) $tool);

        if ($t === '') {
            return 'ops';
        }
        if (str_starts_with($t, 'mcp__')) {
            return 'ops';
        }
        if (in_array($t, self::MEETING_TOOLS, true)) {
            return 'meeting';
        }
        if (in_array($t, self::EDIT_TOOLS, true)) {
            return $this->codeDepartment($target);
        }
        if (in_array($t, self::READ_TOOLS, true)) {
            return 'research';
        }
        if (in_array($t, self::SHELL_TOOLS, true)) {
            return $this->commandDepartment($command ?? $target);
        }

        return 'ops';
    }

    private function codeDepartment(?string $path): string
    {
        $p = strtolower(str_replace('\\', '/', (string) $path));

        if ($this->isTestPath($p)) {
            return 'qa';
        }

        $ext = pathinfo($p, PATHINFO_EXTENSION);

        if (str_ends_with($p, '.blade.php') || in_array($ext, self::FRONTEND_EXT, true)) {
            return 'frontend';
        }
        if (in_array($ext, self::BACKEND_EXT, true)) {
            return 'backend';
        }
        foreach (self::BACKEND_DIRS as $dir) {
            if (str_contains($p, $dir)) {
                return 'backend';
            }
        }
        if (in_array($ext, self::JS_EXT, true)) {
            return 'frontend';
        }

        return 'ops';
    }

    private function commandDepartment(?string $command): string
    {
        $c = (string) $command;

        if (preg_match(self::TEST_CMD, $c)) {
            return 'qa';
        }
        if (preg_match(self::DEPLOY_CMD, $c)) {
            return 'deploy';
        }

        return 'ops';
    }

    private function isTestPath(?string $path): bool
    {
        if ($path === null || $path === '') {
            return false;
        }

        $p = strtolower(str_replace('\\', '/', $path));

        return str_starts_with($p, 'tests/') || str_contains($p, '/tests/');
    }
}
