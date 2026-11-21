<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\AgentEvent;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class OfficeDemoTest extends TestCase
{
    use RefreshDatabase;

    private function runDemo(): void
    {
        // speed besar: satu kitaran siap dalam beberapa saat. Queue = sync dalam test.
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1])->assertSuccessful();
    }

    public function test_demo_creates_five_staff_from_four_vendors_with_friendly_names(): void
    {
        $this->runDemo();

        $this->assertSame(5, Agent::count());
        $this->assertEqualsCanonicalizing(
            ['claude', 'claude', 'codex', 'hermes', 'antigravity'],
            Agent::pluck('vendor')->all(),
        );
        $this->assertEqualsCanonicalizing(
            ['Aiman', 'Balqis', 'Chandra', 'Dewi', 'Evan'],
            Agent::pluck('custom_name')->all(),
        );
        $this->assertSame(['DEMO-PC'], Agent::pluck('pc')->unique()->values()->all());
    }

    public function test_everyone_goes_to_the_meeting_room_before_working(): void
    {
        $this->runDemo();

        foreach (Agent::all() as $agent) {
            $events = $agent->events()->orderBy('id')->get();
            $firstMeeting = $events->search(fn ($e) => $e->department === 'meeting');
            $firstWork = $events->search(fn ($e) => in_array($e->event, ['tool_start', 'tool_end'], true));

            $this->assertNotFalse($firstMeeting, "{$agent->custom_name} tak masuk mesyuarat");
            $this->assertNotFalse($firstWork, "{$agent->custom_name} tak kerja");
            $this->assertLessThan($firstWork, $firstMeeting, "{$agent->custom_name} kerja sebelum mesyuarat");
        }
    }

    public function test_demo_sessions_are_never_terminated(): void
    {
        $this->runDemo();

        $this->assertSame(0, AgentEvent::where('event', 'session_end')->count());
        $this->assertSame(0, Agent::whereNotNull('ended_at')->count());
        $this->assertNotContains('ended', Agent::pluck('status')->all());
    }

    public function test_sweep_never_ends_a_demo_agent_even_after_hours_of_silence(): void
    {
        $demo = Agent::create([
            'vendor' => 'claude', 'session_id' => 'demo-aiman', 'name' => 'Claude demo1', 'label' => 'Claude Code',
            'status' => 'idle', 'department' => 'backend', 'last_event_at' => now()->subHours(5),
        ]);
        $real = Agent::create([
            'vendor' => 'claude', 'session_id' => 'real-1', 'name' => 'Claude real', 'label' => 'Claude Code',
            'status' => 'idle', 'department' => 'backend', 'last_event_at' => now()->subHours(5),
        ]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertNull($demo->fresh()->ended_at);
        $this->assertNotSame('ended', $demo->fresh()->status);
        $this->assertSame('playroom', $demo->fresh()->department); // tetap boleh chill
        $this->assertNotNull($real->fresh()->ended_at); // sesi sebenar masih ditamatkan
    }

    public function test_demo_alerts_do_not_notify_telegram(): void
    {
        config(['services.telegram.token' => 'abc', 'services.telegram.chat_id' => '1']);
        Http::fake();

        $this->runDemo(); // ada needs_approval/error rawak, dan rate_limited pasti (mesin kopi)

        Http::assertNothingSent();
    }
}
