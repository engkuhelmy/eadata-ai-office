<?php

namespace Tests\Unit;

use App\Office\AdapterRegistry;
use Tests\TestCase;

/** Fixture di sini ditangkap dari agy 1.5.5 sebenar (bukan dibina dari docs). */
class AntigravityRealPayloadTest extends TestCase
{
    private function fixture(string $name): array
    {
        $raw = file_get_contents(__DIR__.'/../fixtures/antigravity/'.$name);

        // PowerShell menulis fail dengan BOM
        return json_decode(ltrim($raw, "\xEF\xBB\xBF"), true, flags: JSON_THROW_ON_ERROR);
    }

    private function normalize(string $name): ?object
    {
        $payload = $this->fixture($name);

        return app(AdapterRegistry::class)->get('antigravity')->normalize($payload, $payload['_event']);
    }

    public function test_real_session_start(): void
    {
        $e = $this->normalize('real_session_start.json');

        $this->assertSame('session_start', $e->event);
        $this->assertSame('door', $e->department);
        $this->assertSame('ai office virtual 3D', $e->project);
    }

    public function test_real_run_command_is_a_shell_tool(): void
    {
        $e = $this->normalize('real_post_tool_use.json');

        $this->assertSame('tool_end', $e->event);
        $this->assertSame('Bash', $e->tool);
        $this->assertNotNull($e->target);
        $this->assertContains($e->department, ['ops', 'qa', 'deploy']);
    }

    public function test_real_stop_is_turn_done_only_when_fully_idle(): void
    {
        $payload = $this->fixture('real_stop.json');
        $e = $this->normalize('real_stop.json');

        if ($payload['fullyIdle'] === true) {
            $this->assertSame('turn_done', $e->event);
        } else {
            $this->assertNull($e);
        }
    }
}
