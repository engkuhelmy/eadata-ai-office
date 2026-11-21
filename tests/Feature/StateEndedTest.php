<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class StateEndedTest extends TestCase
{
    use RefreshDatabase;

    private function login(): void
    {
        $user = new User(['name' => 'v', 'email' => 'v@example.test', 'password' => Hash::make('rahsia-kuat-123')]);
        $user->forceFill(['role' => 'viewer'])->save();
        $this->actingAs($user);
    }

    private function agent(string $session, array $attributes = []): Agent
    {
        return Agent::create($attributes + [
            'vendor' => 'claude', 'session_id' => $session, 'name' => $session, 'label' => 'Claude Code',
            'status' => 'ended', 'last_event_at' => now()->subHours(2), 'ended_at' => now()->subHour(),
        ]);
    }

    public function test_recently_ended_agents_are_listed_separately_from_active_ones(): void
    {
        $this->login();
        $this->agent('active-1', ['status' => 'active', 'ended_at' => null, 'last_event_at' => now()]);
        $this->agent('ended-recent');
        $this->agent('ended-old', ['ended_at' => now()->subDays(2), 'last_event_at' => now()->subDays(2)]);

        $json = $this->getJson('/office/state')->assertOk()->json();

        $this->assertSame(['active-1'], array_column($json['agents'], 'name'));
        $this->assertSame(['ended-recent'], array_column($json['ended'], 'name'));
    }

    public function test_ingest_rate_limit_allows_a_busy_pc(): void
    {
        // 120/min lama terlalu ketat: satu PC dengan beberapa agent hantar 2 event setiap tool.
        $limit = app(\Illuminate\Cache\RateLimiter::class)->limiter('ingest');
        $result = $limit(\Illuminate\Http\Request::create('/api/ingest', 'POST'));

        $this->assertGreaterThanOrEqual(600, $result->maxAttempts);
    }
}
