<?php

namespace App\Office;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\StaffMember;

/** Bentuk JSON yang sama untuk /office/state dan broadcast AgentUpdated. */
class OfficePresenter
{
    public static function agent(Agent $agent): array
    {
        return [
            'id' => $agent->id,
            'vendor' => $agent->vendor,
            'session_id' => $agent->session_id,
            'label' => $agent->label,
            'name' => $agent->displayName(),
            'auto_name' => $agent->name,
            'custom_name' => $agent->custom_name,
            'avatar' => $agent->avatar ?? 'default',
            'pc' => $agent->pc,
            'project' => $agent->project,
            'department' => $agent->effectiveDepartment(),
            'auto_department' => $agent->department,
            'pinned_department' => $agent->pinned_department,
            'status' => $agent->status,
            'current_task' => $agent->current_task,
            'last_event_at' => $agent->last_event_at?->toIso8601String(),
            'ended_at' => $agent->ended_at?->toIso8601String(),
            'turn_started_at' => $agent->turn_started_at?->toIso8601String(),
            'done_at' => $agent->done_at?->toIso8601String(),
            'last_turn_seconds' => $agent->last_turn_seconds,
            'subagents' => (int) $agent->subagents,
            'usage' => [
                'input' => (int) $agent->tokens_in,
                'output' => (int) $agent->tokens_out,
                'cache_read' => (int) $agent->tokens_cache_read,
                'cache_create' => (int) $agent->tokens_cache_create,
            ],
            'staff' => self::staff($agent),
        ];
    }

    /** Profil Staff OS (jawatan, skop, handoff) untuk staf sebenar; null untuk agent biasa. Brief penuh tak dihantar ke browser. */
    private static function staff(Agent $agent): ?array
    {
        $staff = StaffMember::forAgent($agent->vendor, $agent->session_id);
        if ($staff === null) {
            return null;
        }

        return [
            'key' => $staff->key,
            'role' => $staff->role,
            'unit' => $staff->unit,
            'reports_to' => $staff->reports_to,
            'team' => $staff->team ?? [],
            'fasa' => $staff->fasa,
            'home' => $staff->home_department,
            'room' => $staff->room,
            'scope' => $staff->scope ?? [],
            'handoffs' => $staff->handoffs ?? [],
            'active' => $staff->is_active,
            'checked_in_at' => $staff->checked_in_at?->toIso8601String(),
        ];
    }

    public static function event(AgentEvent $event): array
    {
        return [
            'id' => $event->id,
            'agent_id' => $event->agent_id,
            'agent' => $event->agent?->displayName(),
            'event' => $event->event,
            'tool' => $event->tool,
            'target' => $event->target,
            'department' => $event->department,
            'ts' => $event->ts?->toIso8601String(),
        ];
    }
}
