<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\NormalizedEvent;
use App\Office\OfficePresenter;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

/** Pusingan kerja (siap / pentas pelancaran) dan kiraan intern, ciri dari Agent Office Kit. */
class TurnTrackingTest extends TestCase
{
    use RefreshDatabase;

    private function send(string $event, string $at, ?string $tool = null): Agent
    {
        ProcessAgentEvent::dispatchSync(new NormalizedEvent(
            vendor: 'claude', agentKey: 'sess-1', name: 'Claude sess', label: 'Claude Code', pc: 'PC-1', project: 'demo',
            event: $event, tool: $tool, target: null, department: null, ts: new DateTimeImmutable($at),
        ));

        return Agent::query()->where('session_id', 'sess-1')->firstOrFail();
    }

    public function test_turn_done_records_duration_and_done_flag(): void
    {
        $a = $this->send('prompt', '2026-11-25T10:00:00+00:00');
        $this->assertNotNull($a->turn_started_at);
        $this->assertNull($a->done_at);

        $this->send('tool_start', '2026-11-25T10:01:00+00:00', 'Bash');
        $a = $this->send('turn_done', '2026-11-25T10:03:30+00:00');

        $this->assertSame(Agent::STATUS_IDLE, $a->status);
        $this->assertSame(210, $a->last_turn_seconds);
        $this->assertNotNull($a->done_at);
        $this->assertNull($a->turn_started_at);

        $json = OfficePresenter::agent($a);
        $this->assertSame(210, $json['last_turn_seconds']);
        $this->assertNotNull($json['done_at']);
    }

    public function test_new_prompt_clears_done_and_starts_new_turn(): void
    {
        $this->send('prompt', '2026-11-25T10:00:00+00:00');
        $this->send('turn_done', '2026-11-25T10:00:40+00:00');

        $a = $this->send('prompt', '2026-11-25T10:05:00+00:00');
        $this->assertNull($a->done_at);
        $this->assertSame('2026-11-25 10:05:00', $a->turn_started_at->format('Y-m-d H:i:s'));
        $this->assertSame(40, $a->last_turn_seconds);
    }

    public function test_subagents_count_up_down_and_reset(): void
    {
        $this->send('prompt', '2026-11-25T10:00:00+00:00');
        $this->send('subagent_start', '2026-11-25T10:00:05+00:00', 'Task');
        $a = $this->send('subagent_start', '2026-11-25T10:00:06+00:00', 'Task');
        $this->assertSame(2, $a->subagents);

        $a = $this->send('subagent_stop', '2026-11-25T10:01:00+00:00');
        $this->assertSame(1, $a->subagents);

        $a = $this->send('turn_done', '2026-11-25T10:02:00+00:00');
        $this->assertSame(0, $a->subagents);

        // Stop tanpa start tak jadi negatif
        $a = $this->send('subagent_stop', '2026-11-25T10:03:00+00:00');
        $this->assertSame(0, $a->subagents);
    }

    public function test_turn_done_without_start_has_no_duration(): void
    {
        $a = $this->send('turn_done', '2026-11-25T10:00:00+00:00');
        $this->assertNotNull($a->done_at);
        $this->assertNull($a->last_turn_seconds);
    }

    public function test_session_end_clears_turn_state(): void
    {
        $this->send('prompt', '2026-11-25T10:00:00+00:00');
        $this->send('turn_done', '2026-11-25T10:02:00+00:00');
        $a = $this->send('session_end', '2026-11-25T10:03:00+00:00');

        $this->assertNull($a->done_at);
        $this->assertNull($a->turn_started_at);
        $this->assertSame(Agent::STATUS_ENDED, $a->status);
    }
}
