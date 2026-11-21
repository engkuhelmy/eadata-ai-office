<?php

namespace App\Office;

use App\Models\Agent;
use App\Models\AgentEvent;

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
            'name' => $agent->name,
            'pc' => $agent->pc,
            'project' => $agent->project,
            'department' => $agent->department,
            'status' => $agent->status,
            'current_task' => $agent->current_task,
            'last_event_at' => $agent->last_event_at?->toIso8601String(),
            'ended_at' => $agent->ended_at?->toIso8601String(),
        ];
    }

    public static function event(AgentEvent $event): array
    {
        return [
            'id' => $event->id,
            'agent_id' => $event->agent_id,
            'agent' => $event->agent?->name,
            'event' => $event->event,
            'tool' => $event->tool,
            'target' => $event->target,
            'department' => $event->department,
            'ts' => $event->ts?->toIso8601String(),
        ];
    }
}
