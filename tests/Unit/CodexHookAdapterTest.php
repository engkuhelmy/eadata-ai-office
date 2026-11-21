<?php

namespace Tests\Unit;

use App\Office\AdapterRegistry;
use Tests\TestCase;

class CodexHookAdapterTest extends TestCase
{
    private function fixture(string $path): array
    {
        return json_decode(file_get_contents(__DIR__.'/../fixtures/'.$path), true, flags: JSON_THROW_ON_ERROR);
    }

    public function test_pre_tool_use_bash_pytest_goes_to_qa(): void
    {
        $e = app(AdapterRegistry::class)->get('codex')->normalize($this->fixture('codex/pre_tool_use_bash.json'));

        $this->assertSame('tool_start', $e->event);
        $this->assertSame('Bash', $e->tool);
        $this->assertSame('qa', $e->department);
        $this->assertSame('pytest -q', $e->target);
        $this->assertSame('eadata-web', $e->project);
    }

    public function test_post_tool_use_error_is_tool_error(): void
    {
        $e = app(AdapterRegistry::class)->get('codex')->normalize($this->fixture('codex/post_tool_use_error.json'));

        $this->assertSame('tool_error', $e->event);
        $this->assertNull($e->department);
    }

    public function test_hook_stop_maps_to_turn_done(): void
    {
        $e = app(AdapterRegistry::class)->get('codex')->normalize([
            'hook_event_name' => 'Stop',
            'session_id' => 'codex-session-01',
            'cwd' => 'C:\\Users\\Helmi\\projek\\eadata-web',
        ]);

        $this->assertSame('turn_done', $e->event);
        $this->assertNull($e->department); // kekal di meja; sweep hantar ke playroom lepas 2 minit
    }

    public function test_unknown_hook_event_is_ignored(): void
    {
        $e = app(AdapterRegistry::class)->get('codex')->normalize([
            'hook_event_name' => 'SomethingNew',
            'session_id' => 'codex-session-01',
        ]);

        $this->assertNull($e);
    }
}
