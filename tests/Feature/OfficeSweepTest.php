<?php

namespace Tests\Feature;

use App\Models\Agent;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class OfficeSweepTest extends TestCase
{
    use RefreshDatabase;

    private function agent(array $attributes = []): Agent
    {
        return Agent::create($attributes + [
            'vendor' => 'claude',
            'session_id' => 's-'.uniqid(),
            'name' => 'Claude x',
            'label' => 'Claude Code',
            'department' => 'backend',
            'status' => 'active',
            'last_event_at' => now(),
        ]);
    }

    public function test_idle_agent_goes_to_playroom_after_two_minutes(): void
    {
        $fresh = $this->agent(['status' => 'idle', 'last_event_at' => now()->subSeconds(60)]);
        $chill = $this->agent(['status' => 'idle', 'last_event_at' => now()->subSeconds(130)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertSame('backend', $fresh->fresh()->department);
        $this->assertSame('playroom', $chill->fresh()->department);
    }

    public function test_pinned_department_is_never_moved_to_playroom(): void
    {
        $agent = $this->agent(['status' => 'idle', 'pinned_department' => 'qa', 'last_event_at' => now()->subMinutes(30)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertSame('backend', $agent->fresh()->department);
        $this->assertSame('qa', $agent->fresh()->effectiveDepartment());
    }

    public function test_active_agent_without_events_becomes_idle_after_ten_minutes_then_playroom(): void
    {
        $agent = $this->agent(['status' => 'active', 'last_event_at' => now()->subMinutes(11)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $agent->refresh();
        $this->assertSame('idle', $agent->status);
        $this->assertSame('playroom', $agent->department);
    }

    public function test_agent_waiting_for_approval_is_left_alone_until_it_ends(): void
    {
        $agent = $this->agent(['status' => 'needs_approval', 'last_event_at' => now()->subMinutes(30)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertSame('needs_approval', $agent->fresh()->status);
        $this->assertSame('backend', $agent->fresh()->department);
    }

    public function test_agent_silent_for_an_hour_is_ended(): void
    {
        $agent = $this->agent(['status' => 'idle', 'last_event_at' => now()->subMinutes(61)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $agent->refresh();
        $this->assertSame('ended', $agent->status);
        $this->assertNotNull($agent->ended_at);
    }

    public function test_sweep_is_idempotent(): void
    {
        $agent = $this->agent(['status' => 'idle', 'last_event_at' => now()->subMinutes(5)]);

        $this->artisan('office:sweep')->assertSuccessful();
        $first = $agent->fresh()->updated_at;
        $this->travel(5)->seconds();
        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertEquals($first, $agent->fresh()->updated_at);
    }

    public function test_sweep_is_scheduled_every_minute(): void
    {
        $this->artisan('schedule:list')->expectsOutputToContain('office:sweep')->assertSuccessful();
    }
}
