<?php

namespace Tests\Unit;

use App\Office\AdapterRegistry;
use App\Office\NormalizedEvent;
use App\Office\Redactor;
use Illuminate\Support\Facades\Cache;
use Tests\TestCase;

class OfficeAdaptersTest extends TestCase
{
    private function fixture(string $path): array
    {
        $json = file_get_contents(__DIR__.'/../fixtures/'.$path);

        return json_decode($json, true, flags: JSON_THROW_ON_ERROR);
    }

    private function normalize(string $vendor, string $path, ?string $hint = null): ?NormalizedEvent
    {
        return app(AdapterRegistry::class)->get($vendor)->normalize($this->fixture($path), $hint);
    }

    protected function setUp(): void
    {
        parent::setUp();
        Cache::flush();
    }

    public function test_claude_session_start_goes_to_door(): void
    {
        $e = $this->normalize('claude', 'claude/session_start.json');

        $this->assertSame('session_start', $e->event);
        $this->assertSame('door', $e->department);
        $this->assertSame('eadata-web', $e->project);
        $this->assertSame('HELMY-PC', $e->pc);
        $this->assertSame('Claude Code', $e->label);
    }

    public function test_claude_edit_vue_goes_to_frontend_and_target_is_path_only(): void
    {
        $e = $this->normalize('claude', 'claude/pre_tool_use_edit_vue.json');

        $this->assertSame('tool_start', $e->event);
        $this->assertSame('Edit', $e->tool);
        $this->assertSame('frontend', $e->department);
        $this->assertSame('resources/js/components/Navbar.vue', $e->target);
    }

    public function test_claude_write_php_goes_to_backend(): void
    {
        $e = $this->normalize('claude', 'claude/pre_tool_use_edit_php.json');

        $this->assertSame('backend', $e->department);
        $this->assertSame('app/Http/Controllers/UserController.php', $e->target);
    }

    public function test_claude_bash_phpunit_goes_to_qa(): void
    {
        $e = $this->normalize('claude', 'claude/pre_tool_use_bash_phpunit.json');

        $this->assertSame('qa', $e->department);
        $this->assertSame('php artisan test --filter=OfficeAdaptersTest', $e->target);
    }

    public function test_claude_git_push_goes_to_deploy_and_token_is_masked(): void
    {
        $e = $this->normalize('claude', 'claude/pre_tool_use_bash_deploy.json');

        $this->assertSame('deploy', $e->department);
        $this->assertStringNotContainsString('ghp_abcdefghijklmnopqrstuvwxyz', (string) $e->target);
        $this->assertStringContainsString('gh_***', (string) $e->target);
    }

    public function test_claude_task_tool_becomes_subagent_meeting(): void
    {
        $e = $this->normalize('claude', 'claude/pre_tool_use_task.json');

        $this->assertSame('subagent_start', $e->event);
        $this->assertSame('meeting', $e->department);
    }

    public function test_claude_post_tool_error_is_tool_error_and_keeps_desk(): void
    {
        $e = $this->normalize('claude', 'claude/post_tool_use_error.json');

        $this->assertSame('tool_error', $e->event);
        $this->assertNull($e->department);
    }

    public function test_hermes_pre_llm_call_is_accepted_once_per_turn(): void
    {
        $first = $this->normalize('hermes', 'hermes/pre_llm_call.json');
        $second = $this->normalize('hermes', 'hermes/pre_llm_call.json');

        $this->assertSame('prompt', $first->event);
        $this->assertSame('kanban', $first->department);
        $this->assertNull($second);
    }

    public function test_hermes_terminal_pytest_goes_to_qa_and_label_is_hermes(): void
    {
        $e = $this->normalize('hermes', 'hermes/pre_tool_call_terminal.json');

        $this->assertSame('Bash', $e->tool);
        $this->assertSame('qa', $e->department);
        $this->assertSame('Hermes', $e->label);
        $this->assertSame('sess_abc123', $e->agentKey);
    }

    public function test_hermes_post_tool_error_status_is_tool_error(): void
    {
        $e = $this->normalize('hermes', 'hermes/post_tool_call_error.json');

        $this->assertSame('tool_error', $e->event);
        $this->assertNull($e->department);
    }

    public function test_codex_legacy_notify_is_turn_done_and_stays_at_desk(): void
    {
        $e = $this->normalize('codex', 'codex/legacy_notify.json');

        $this->assertSame('turn_done', $e->event);
        $this->assertNull($e->department);
        $this->assertSame('codex-thread-7b21', $e->agentKey);
    }

    public function test_generic_explicit_department_is_used_directly(): void
    {
        $e = app(AdapterRegistry::class)->get('generic')->normalize([
            'agent' => 'researcher-1',
            'name' => 'Rafiq',
            'label' => 'CrewAI',
            'event' => 'tool_start',
            'tool' => 'web_search',
            'target' => 'harga VPS Malaysia',
            'project' => 'eadata-web',
            'department' => 'research',
        ]);

        $this->assertSame('research', $e->department);
        $this->assertSame('Rafiq', $e->name);
        $this->assertSame('CrewAI', $e->label);
    }

    public function test_unknown_generic_event_is_rejected(): void
    {
        $e = app(AdapterRegistry::class)->get('generic')->normalize([
            'agent' => 'x', 'event' => 'hack_the_planet',
        ]);

        $this->assertNull($e);
    }

    public function test_redactor_masks_secrets_env_lines_and_truncates(): void
    {
        $redactor = new Redactor;

        $this->assertStringContainsString('sk-***', $redactor->scrub('key sk-abcdefghijklmnopqrstu'));
        $this->assertStringContainsString('password=***', $redactor->scrub('password=hunter2'));
        $this->assertStringContainsString('Bearer ***', $redactor->scrub('Authorization: Bearer abc.def.ghi'));
        $this->assertSame('DB_PASSWORD=*** APP_KEY=***', $redactor->scrub("DB_PASSWORD=abc\nAPP_KEY=base64xyz"));
        $this->assertSame(200, mb_strlen($redactor->target(str_repeat('a', 500))));
    }
}
