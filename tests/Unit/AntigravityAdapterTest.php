<?php

namespace Tests\Unit;

use App\Office\AdapterRegistry;
use Illuminate\Support\Facades\Cache;
use Tests\TestCase;

class AntigravityAdapterTest extends TestCase
{
    protected function setUp(): void
    {
        parent::setUp();
        Cache::flush();
    }

    private function normalize(array $payload, ?string $hint)
    {
        return app(AdapterRegistry::class)->get('antigravity')->normalize($payload, $hint);
    }

    private function fixture(string $name): array
    {
        return json_decode(file_get_contents(__DIR__.'/../fixtures/antigravity/'.$name), true, flags: JSON_THROW_ON_ERROR);
    }

    public function test_antigravity_is_a_registered_source(): void
    {
        $this->assertTrue(app(AdapterRegistry::class)->has('antigravity'));
    }

    public function test_session_start_goes_to_door(): void
    {
        $e = $this->normalize($this->fixture('session_start.json'), 'SessionStart');

        $this->assertSame('session_start', $e->event);
        $this->assertSame('door', $e->department);
        $this->assertSame('antigravity', $e->vendor);
        $this->assertSame('Antigravity', $e->label);
        $this->assertSame('eadata-web', $e->project);
        $this->assertSame('0b6f1c1e-4d7a-4a0e-9a54-antigravity01', $e->agentKey);
    }

    public function test_run_command_pytest_goes_to_qa(): void
    {
        $e = $this->normalize($this->fixture('post_tool_use_run_command.json'), 'PostToolUse');

        $this->assertSame('tool_end', $e->event);
        $this->assertSame('Bash', $e->tool);
        $this->assertSame('qa', $e->department);
        $this->assertSame('pytest -q', $e->target);
    }

    public function test_post_tool_error_is_tool_error(): void
    {
        $e = $this->normalize($this->fixture('post_tool_use_edit_error.json'), 'PostToolUse');

        $this->assertSame('tool_error', $e->event);
        $this->assertSame('Edit', $e->tool);
        $this->assertSame('resources/js/components/Navbar.vue', $e->target);
    }

    public function test_stop_only_counts_when_fully_idle(): void
    {
        $base = ['conversationId' => 'conv-1', 'workspacePaths' => ['C:\\proj']];

        $this->assertNull($this->normalize($base + ['fullyIdle' => false], 'Stop'));
        $this->assertSame('turn_done', $this->normalize($base + ['fullyIdle' => true], 'Stop')->event);
    }

    public function test_pre_invocation_is_a_prompt_once_per_user_input(): void
    {
        $payload = ['conversationId' => 'conv-1', 'promptHash' => 'abc123'];

        $this->assertSame('prompt', $this->normalize($payload, 'PreInvocation')->event);
        $this->assertNull($this->normalize($payload, 'PreInvocation'));
        $this->assertSame('prompt', $this->normalize(['promptHash' => 'def456'] + $payload, 'PreInvocation')->event);
    }

    public function test_unknown_event_or_missing_conversation_is_ignored(): void
    {
        $this->assertNull($this->normalize(['conversationId' => 'conv-1'], 'SomethingNew'));
        $this->assertNull($this->normalize(['toolCall' => ['name' => 'run_command']], 'PostToolUse'));
        $this->assertNull($this->normalize(['conversationId' => 'conv-1'], null));
    }

    public function test_event_name_falls_back_to_hookEventName_in_payload(): void
    {
        $e = $this->normalize(['conversationId' => 'conv-1', 'hookEventName' => 'SessionStart', 'cwd' => 'C:\\proj\\eadata-web'], null);

        $this->assertSame('session_start', $e->event);
        $this->assertSame('eadata-web', $e->project);
    }
}
