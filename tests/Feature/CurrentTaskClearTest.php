<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\NormalizedEvent;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class CurrentTaskClearTest extends TestCase
{
    use RefreshDatabase;

    private function send(string $event, ?string $tool = null, ?string $target = null, ?string $department = null): void
    {
        ProcessAgentEvent::dispatchSync(new NormalizedEvent(
            vendor: 'claude',
            agentKey: 'sess-task',
            name: 'Claude task',
            label: 'Claude Code',
            pc: 'PC',
            project: 'proj',
            event: $event,
            tool: $tool,
            target: $target,
            department: $department,
            ts: new DateTimeImmutable('now'),
        ));
    }

    public function test_idle_event_clears_current_task(): void
    {
        $this->send('tool_start', 'Edit', 'resources/js/Navbar.vue');
        $this->assertSame('Editing Navbar.vue', Agent::first()->current_task);

        $this->send('idle', department: 'pantry');

        $this->assertNull(Agent::first()->current_task);
        $this->assertSame('pantry', Agent::first()->department);
        $this->assertSame('idle', Agent::first()->status);
    }

    public function test_turn_done_clears_current_task(): void
    {
        $this->send('tool_end', 'Bash', 'npm run build');
        $this->assertSame('Running npm run build', Agent::first()->current_task);

        $this->send('turn_done');

        $this->assertNull(Agent::first()->current_task);
    }

    public function test_other_events_keep_current_task(): void
    {
        $this->send('tool_start', 'Edit', 'app/Models/Invoice.php');
        $this->send('tool_error', 'Edit', 'app/Models/Invoice.php');

        $this->assertSame('Editing Invoice.php', Agent::first()->current_task);
    }
}
