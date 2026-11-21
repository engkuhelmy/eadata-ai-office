<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class HistoryTest extends TestCase
{
    use RefreshDatabase;

    private function user(): User
    {
        $user = new User([
            'name' => 'viewer',
            'email' => 'viewer@example.test',
            'password' => Hash::make('rahsia-kuat-123'),
        ]);
        $user->forceFill(['role' => 'viewer'])->save();

        return $user;
    }

    private function agent(string $session, array $extra = []): Agent
    {
        return Agent::create($extra + [
            'vendor' => 'claude',
            'session_id' => $session,
            'name' => "Claude {$session}",
            'pc' => 'PC-A',
            'project' => 'webapp',
            'status' => 'active',
        ]);
    }

    private function event(Agent $agent, $ts, string $event = 'tool_start'): AgentEvent
    {
        return AgentEvent::create([
            'agent_id' => $agent->id,
            'event' => $event,
            'tool' => 'Edit',
            'target' => 'a.vue',
            'department' => 'frontend',
            'ts' => $ts,
        ]);
    }

    public function test_guests_are_blocked(): void
    {
        $this->get('/history')->assertRedirect('/login');
        $this->getJson('/office/history.json')->assertUnauthorized();
        $this->assertSame(url('/history'), route('office.history'));
        $this->assertSame(url('/office/history.json'), route('office.history.json'));
    }

    public function test_default_is_today_newest_first_with_shape(): void
    {
        $a = $this->agent('s1', ['custom_name' => 'Aiman']);
        $old = $this->event($a, now()->subDays(3));
        $first = $this->event($a, now()->subMinutes(10));
        $second = $this->event($a, now()->subMinutes(1), 'tool_end');

        $response = $this->actingAs($this->user())->getJson('/office/history.json')->assertOk();

        $response->assertJsonPath('page', 1)->assertJsonPath('has_more', false);
        $ids = array_column($response->json('data'), 'id');
        $this->assertSame([$second->id, $first->id], $ids);
        $this->assertNotContains($old->id, $ids);
        $this->assertSame([
            'id' => $second->id, 'agent_id' => $a->id, 'agent' => 'Aiman', 'vendor' => 'claude',
            'project' => 'webapp', 'pc' => 'PC-A', 'event' => 'tool_end', 'tool' => 'Edit',
            'target' => 'a.vue', 'department' => 'frontend', 'ts' => $second->ts->toIso8601String(),
        ], $response->json('data.0'));
    }

    public function test_date_filter_and_validation(): void
    {
        $a = $this->agent('s1');
        $e = $this->event($a, '2026-01-05 10:00:00');
        $this->event($a, '2026-01-06 10:00:00');

        $this->actingAs($this->user())
            ->getJson('/office/history.json?date=2026-01-05')
            ->assertOk()
            ->assertJsonCount(1, 'data')
            ->assertJsonPath('data.0.id', $e->id);

        foreach (['bukan-tarikh', '2026-13-45', '05/01/2026'] as $bad) {
            $this->getJson('/office/history.json?date='.urlencode($bad))->assertStatus(422);
        }
        $this->getJson('/office/history.json?page=0')->assertStatus(422);
        $this->getJson('/office/history.json?agent_id=abc')->assertStatus(422);
    }

    public function test_filters_by_vendor_project_pc_and_agent(): void
    {
        $a = $this->agent('s1');
        $b = $this->agent('s2', ['vendor' => 'codex', 'project' => 'api', 'pc' => 'PC-B']);
        $ea = $this->event($a, now());
        $eb = $this->event($b, now());
        $this->actingAs($this->user());

        $this->getJson('/office/history.json?vendor=codex')->assertJsonPath('data.0.id', $eb->id)->assertJsonCount(1, 'data');
        $this->getJson('/office/history.json?project=webapp')->assertJsonPath('data.0.id', $ea->id)->assertJsonCount(1, 'data');
        $this->getJson('/office/history.json?pc=PC-B')->assertJsonPath('data.0.id', $eb->id)->assertJsonCount(1, 'data');
        $this->getJson("/office/history.json?agent_id={$a->id}")->assertJsonPath('data.0.id', $ea->id)->assertJsonCount(1, 'data');
        $this->getJson('/office/history.json?vendor=codex&project=webapp')->assertJsonCount(0, 'data');
    }

    public function test_pagination_of_50_and_no_n_plus_one(): void
    {
        $a = $this->agent('s1');
        $b = $this->agent('s2');
        $base = now()->startOfDay();
        for ($i = 0; $i < 120; $i++) {
            $this->event($i % 2 ? $a : $b, $base->copy()->addSeconds($i));
        }
        $this->actingAs($this->user());

        $p1 = $this->getJson('/office/history.json')->assertOk()->assertJsonCount(50, 'data')->assertJsonPath('has_more', true);
        $p2 = $this->getJson('/office/history.json?page=2')->assertJsonCount(50, 'data')->assertJsonPath('has_more', true)->assertJsonPath('page', 2);
        $p3 = $this->getJson('/office/history.json?page=3')->assertJsonCount(20, 'data')->assertJsonPath('has_more', false);

        $all = array_merge(array_column($p1->json('data'), 'ts'), array_column($p2->json('data'), 'ts'), array_column($p3->json('data'), 'ts'));
        $this->assertSame($all, collect($all)->sortDesc()->values()->all());
        $this->assertCount(120, array_unique(array_merge(
            array_column($p1->json('data'), 'id'), array_column($p2->json('data'), 'id'), array_column($p3->json('data'), 'id'),
        )));

        DB::enableQueryLog();
        $this->getJson('/office/history.json')->assertOk();
        $this->assertLessThanOrEqual(6, count(DB::getQueryLog()));
    }
}
