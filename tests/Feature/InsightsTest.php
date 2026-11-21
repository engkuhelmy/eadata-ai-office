<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\Device;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class InsightsTest extends TestCase
{
    use RefreshDatabase;

    private function user(string $role = 'viewer'): User
    {
        $user = new User([
            'name' => $role,
            'email' => "{$role}@example.test",
            'password' => Hash::make('rahsia-kuat-123'),
        ]);
        $user->forceFill(['role' => $role])->save();

        return $user;
    }

    private function agent(string $session, array $extra = []): Agent
    {
        return Agent::create($extra + [
            'vendor' => 'claude',
            'session_id' => $session,
            'label' => 'Claude Code',
            'name' => "Claude {$session}",
            'pc' => 'PC-A',
            'project' => 'webapp',
            'department' => 'frontend',
            'status' => 'active',
            'last_event_at' => now(),
        ]);
    }

    private function event(Agent $agent, string $event, $ts = null, ?string $department = 'frontend'): AgentEvent
    {
        return AgentEvent::create([
            'agent_id' => $agent->id,
            'event' => $event,
            'tool' => 'Edit',
            'target' => 'a.vue',
            'department' => $department,
            'ts' => $ts ?? now(),
        ]);
    }

    public function test_guest_cannot_see_insights(): void
    {
        $this->getJson('/office/insights')->assertUnauthorized();
    }

    public function test_insights_shape_with_empty_database(): void
    {
        $this->actingAs($this->user())
            ->getJson('/office/insights')
            ->assertOk()
            ->assertJsonStructure([
                'health' => ['server_time', 'vendors', 'devices'],
                'stats' => ['today' => ['events', 'errors', 'active_agents', 'by_department', 'by_vendor'], 'hourly'],
                'board' => ['doing', 'attention', 'done'],
            ])
            ->assertJsonCount(24, 'stats.hourly')
            ->assertJsonPath('stats.today.events', 0)
            ->assertJsonPath('board.doing', []);
    }

    public function test_health_vendors_and_devices_do_not_leak_tokens(): void
    {
        $a = $this->agent('s1');
        $this->agent('s2', ['ended_at' => now(), 'status' => 'ended']);
        $this->agent('s3', ['vendor' => 'codex', 'session_id' => 'c1']);
        $this->event($a, 'tool_start');
        $this->event($a, 'tool_end', now()->subHours(30));
        Device::create(['name' => 'HELMY-PC', 'token_hash' => hash('sha256', 'x'), 'last_used_at' => now()]);
        Device::create(['name' => 'OLD', 'token_hash' => hash('sha256', 'y'), 'revoked_at' => now()]);

        $response = $this->actingAs($this->user())->getJson('/office/insights')->assertOk();

        $vendors = collect($response->json('health.vendors'))->keyBy('vendor');
        $this->assertSame(1, $vendors['claude']['agents']);
        $this->assertSame(1, $vendors['claude']['events_24h']);
        $this->assertNotNull($vendors['claude']['last_event_at']);
        $this->assertSame(1, $vendors['codex']['agents']);
        $this->assertSame(0, $vendors['hermes']['agents']);
        $this->assertNull($vendors['hermes']['last_event_at']);
        $this->assertSame('Claude Code', $vendors['claude']['label']);

        $devices = collect($response->json('health.devices'));
        $this->assertCount(2, $devices);
        $this->assertTrue($devices->firstWhere('name', 'OLD')['revoked']);
        $this->assertFalse($devices->firstWhere('name', 'HELMY-PC')['revoked']);
        $this->assertStringNotContainsString('token', json_encode($response->json('health.devices')));
        $this->assertStringNotContainsString(hash('sha256', 'x'), $response->getContent());
    }

    public function test_today_stats_and_hourly_buckets(): void
    {
        $this->travelTo(now()->setTime(15, 30));

        $a = $this->agent('s1');
        $b = $this->agent('s2', ['vendor' => 'codex', 'session_id' => 'c1']);
        $this->event($a, 'tool_start');
        $this->event($a, 'tool_error');
        $this->event($b, 'error', now(), 'backend');
        $this->event($a, 'tool_end', now()->subDays(2)); // bukan hari ini

        $response = $this->actingAs($this->user())->getJson('/office/insights')->assertOk();

        $response->assertJsonPath('stats.today.events', 3)
            ->assertJsonPath('stats.today.errors', 2)
            ->assertJsonPath('stats.today.active_agents', 2)
            ->assertJsonPath('stats.today.by_department.frontend', 2)
            ->assertJsonPath('stats.today.by_department.backend', 1)
            ->assertJsonPath('stats.today.by_vendor.claude', 2)
            ->assertJsonPath('stats.today.by_vendor.codex', 1);

        $hourly = $response->json('stats.hourly');
        $this->assertCount(24, $hourly);
        $this->assertSame('16', $hourly[0]['hour']); // 15:30 - 23 jam = 16:xx semalam
        $this->assertSame('15', $hourly[23]['hour']);
        $this->assertSame(3, $hourly[23]['events']);
        $this->assertSame(3, array_sum(array_column($hourly, 'events')));
    }

    public function test_board_columns(): void
    {
        $this->agent('doing', ['status' => 'active']);
        $this->agent('appr', ['status' => 'needs_approval']);
        $this->agent('err', ['status' => 'error']);
        $this->agent('rate', ['status' => 'rate_limited']);
        $this->agent('ended', ['status' => 'ended', 'ended_at' => now()]);
        $this->agent('old-idle', ['status' => 'idle', 'last_event_at' => now()->subMinutes(45)]);
        for ($i = 0; $i < 12; $i++) {
            $this->agent("idle{$i}", ['status' => 'idle', 'last_event_at' => now()->subMinutes($i + 1)]);
        }

        $response = $this->actingAs($this->user())->getJson('/office/insights')->assertOk();

        $this->assertCount(1, $response->json('board.doing'));
        $this->assertEqualsCanonicalizing(
            ['needs_approval', 'error', 'rate_limited'],
            array_column($response->json('board.attention'), 'status'),
        );
        $done = $response->json('board.done');
        $this->assertCount(10, $done);
        $this->assertSame('Claude idle0', $done[0]['name']);
        $this->assertArrayHasKey('usage', $done[0]);
    }
}
