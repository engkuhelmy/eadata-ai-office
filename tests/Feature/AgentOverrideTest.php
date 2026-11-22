<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\User;
use App\Office\DepartmentRouter;
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

    public function test_owner_can_set_avatar_and_state_exposes_it(): void
    {
        $agent = $this->agent();
        $this->actingAs($this->user('owner'));

        $this->getJson('/office/state')->assertJsonPath('agents.0.avatar', 'default');

        foreach (['woman', 'hiphop', 'genz', 'recep', 'grab', 'shopee', 'jnt', 'dhl'] as $avatar) {
            $this->patchJson("/office/agents/{$agent->id}", ['avatar' => $avatar])
                ->assertOk()
                ->assertJsonPath('agent.avatar', $avatar);
        }

        $this->getJson('/office/state')->assertJsonPath('agents.0.avatar', 'dhl');
    }

    public function test_empty_avatar_returns_to_default_and_missing_avatar_is_kept(): void
    {
        $agent = $this->agent();
        $agent->update(['avatar' => 'woman']);

        $this->actingAs($this->user('owner'))
            ->patchJson("/office/agents/{$agent->id}", ['name' => 'Aiman'])
            ->assertOk()
            ->assertJsonPath('agent.avatar', 'woman');

        $this->patchJson("/office/agents/{$agent->id}", ['avatar' => null])
            ->assertOk()
            ->assertJsonPath('agent.avatar', 'default');

        $this->assertNull($agent->fresh()->avatar);
    }

    public function test_unknown_avatar_is_rejected(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('owner'))
            ->patchJson("/office/agents/{$agent->id}", ['avatar' => 'robot'])
            ->assertStatus(422);

        $this->assertNull($agent->fresh()->avatar);
    }

    public function test_viewer_cannot_change_avatar(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('viewer'))
            ->patchJson("/office/agents/{$agent->id}", ['avatar' => 'woman'])
            ->assertForbidden();

        $this->assertNull($agent->fresh()->avatar);
    }

    public function test_new_room_departments_can_be_pinned_and_routed(): void
    {
        $agent = $this->agent();

        $this->actingAs($this->user('owner'));

        foreach (['boardroom', 'pantry', 'toilet', 'playroom', 'reception', 'frontdesk'] as $department) {
            $this->assertContains($department, DepartmentRouter::DEPARTMENTS);

            $this->patchJson("/office/agents/{$agent->id}", ['department' => $department])
                ->assertOk()
                ->assertJsonPath('agent.department', $department);

            $this->assertSame($department, (new DepartmentRouter)->route('idle', explicit: $department));
        }
    }
}
