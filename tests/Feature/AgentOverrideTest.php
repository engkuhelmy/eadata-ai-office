<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class AgentOverrideTest extends TestCase
{
    use RefreshDatabase;

    private function user(string $role): User
    {
        $user = new User([
            'name' => $role,
            'email' => "{$role}@example.test",
            'password' => Hash::make('rahsia-kuat-123'),
        ]);
        $user->forceFill(['role' => $role])->save();

        return $user;
    }

    private function agent(): Agent
    {
        return Agent::create([
            'vendor' => 'claude',
            'session_id' => 'sess-1',
            'label' => 'Claude Code',
            'name' => 'Claude sess',
            'department' => 'backend',
            'status' => 'active',
        ]);
    }

    public function test_owner_can_rename_and_pin_department(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('owner'))
            ->patchJson("/office/agents/{$agent->id}", ['name' => 'Aiman', 'department' => 'qa'])
            ->assertOk()
            ->assertJsonPath('agent.name', 'Aiman')
            ->assertJsonPath('agent.department', 'qa')
            ->assertJsonPath('agent.auto_department', 'backend');

        $this->getJson('/office/state')
            ->assertJsonPath('agents.0.name', 'Aiman')
            ->assertJsonPath('agents.0.department', 'qa');
    }

    public function test_empty_values_return_to_automatic(): void
    {
        $agent = $this->agent();
        $agent->update(['custom_name' => 'Aiman', 'pinned_department' => 'qa']);

        $this->actingAs($this->user('owner'))
            ->patchJson("/office/agents/{$agent->id}", ['name' => '', 'department' => null])
            ->assertOk()
            ->assertJsonPath('agent.name', 'Claude sess')
            ->assertJsonPath('agent.department', 'backend');
    }

    public function test_viewer_cannot_edit(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('viewer'))
            ->patchJson("/office/agents/{$agent->id}", ['name' => 'Hack'])
            ->assertForbidden();

        $this->assertNull($agent->fresh()->custom_name);
    }

    public function test_unknown_department_is_rejected(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('owner'))
            ->patchJson("/office/agents/{$agent->id}", ['department' => 'rooftop'])
            ->assertStatus(422);
    }
}
