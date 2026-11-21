<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Office\NormalizedEvent;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class TimezoneTest extends TestCase
{
    use RefreshDatabase;

    public function test_event_time_with_offset_is_stored_in_app_timezone(): void
    {
        // 10:00 di +08:00 = 02:00 UTC. App timezone = UTC.
        $ts = new DateTimeImmutable('2026-11-21T10:00:00+08:00');

        ProcessAgentEvent::dispatchSync(new NormalizedEvent(
            vendor: 'claude', agentKey: 's1', name: 'Claude s1', label: 'Claude Code', pc: 'PC', project: 'p',
            event: 'tool_start', tool: 'Bash', target: 'ls', department: 'ops', ts: $ts,
        ));

        $agent = Agent::firstOrFail();
        $this->assertSame('02:00:00', $agent->last_event_at->setTimezone('UTC')->format('H:i:s'));
        $this->assertSame('2026-11-21 02:00:00', $agent->getRawOriginal('last_event_at'));
        $this->assertSame('2026-11-21 02:00:00', AgentEvent::firstOrFail()->getRawOriginal('ts'));
    }

    public function test_sweep_treats_a_local_offset_event_as_recent_not_future(): void
    {
        $this->travelTo(new DateTimeImmutable('2026-11-21T02:10:00+00:00'));

        ProcessAgentEvent::dispatchSync(new NormalizedEvent(
            vendor: 'claude', agentKey: 's2', name: 'Claude s2', label: 'Claude Code', pc: 'PC', project: 'p',
            event: 'turn_done', tool: null, target: null, department: null,
            ts: new DateTimeImmutable('2026-11-21T10:00:00+08:00'), // 10 min lalu
        ));

        $this->artisan('office:sweep')->assertSuccessful();

        // 10 min senyap + status idle: chill ke playroom (bukan "masa depan" yang tak pernah tamat)
        $this->assertSame('playroom', Agent::firstOrFail()->department);
    }
}
