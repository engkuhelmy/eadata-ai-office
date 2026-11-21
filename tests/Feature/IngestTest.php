<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\Device;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class IngestTest extends TestCase
{
    use RefreshDatabase;

    private const TOKEN = 'eod_testtoken0000000000000000000000000000000';

    private function device(): Device
    {
        return Device::create([
            'name' => 'HELMY-PC',
            'token_hash' => hash('sha256', self::TOKEN),
        ]);
    }

    private function fixture(string $path): array
    {
        return json_decode(file_get_contents(__DIR__.'/../fixtures/'.$path), true, flags: JSON_THROW_ON_ERROR);
    }

    public function test_ingest_without_token_is_401(): void
    {
        $this->postJson('/api/ingest?src=claude', $this->fixture('claude/session_start.json'))
            ->assertStatus(401);

        $this->assertSame(0, Agent::count());
    }

    public function test_ingest_with_wrong_token_is_401(): void
    {
        $this->device();

        $this->withToken('eod_wrong')
            ->postJson('/api/ingest?src=claude', $this->fixture('claude/session_start.json'))
            ->assertStatus(401);
    }

    public function test_ingest_with_revoked_token_is_401(): void
    {
        $device = $this->device();
        $device->update(['revoked_at' => now()]);

        $this->withToken(self::TOKEN)
            ->postJson('/api/ingest?src=claude', $this->fixture('claude/session_start.json'))
            ->assertStatus(401);
    }

    public function test_valid_token_and_payload_returns_202_and_creates_rows(): void
    {
        $device = $this->device();

        $this->withToken(self::TOKEN)
            ->postJson('/api/ingest?src=claude', $this->fixture('claude/pre_tool_use_edit_vue.json'))
            ->assertStatus(202);

        $agent = Agent::firstOrFail();
        $this->assertSame('claude', $agent->vendor);
        $this->assertSame('frontend', $agent->department);
        $this->assertSame('Editing Navbar.vue', $agent->current_task);
        $this->assertSame(1, AgentEvent::where('agent_id', $agent->id)->count());
        $this->assertNotNull($device->fresh()->last_used_at);
    }

    public function test_unknown_src_is_422(): void
    {
        $this->device();

        $this->withToken(self::TOKEN)
            ->postJson('/api/ingest?src=nope', $this->fixture('claude/session_start.json'))
            ->assertStatus(422);
    }

    public function test_unrecognised_payload_is_422(): void
    {
        $this->device();

        $this->withToken(self::TOKEN)
            ->postJson('/api/ingest?src=claude', ['hook_event_name' => 'SomethingElse', 'session_id' => 'x'])
            ->assertStatus(422);
    }
}
