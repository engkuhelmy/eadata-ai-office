<?php

namespace App\Http\Controllers;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Office\OfficePresenter;
use Illuminate\Http\JsonResponse;
use Illuminate\Contracts\View\View;

class OfficeController extends Controller
{
    public function index(): View
    {
        return view('office');
    }

    /** Snapshot untuk reload page + fallback polling (setiap 3s). */
    public function state(): JsonResponse
    {
        $agents = Agent::query()
            ->whereNull('ended_at')
            ->orderByDesc('last_event_at')
            ->get()
            ->map(fn (Agent $agent) => OfficePresenter::agent($agent))
            ->values();

        $events = AgentEvent::query()
            ->with('agent')
            ->orderByDesc('ts')
            ->limit(50)
            ->get()
            ->map(fn (AgentEvent $event) => OfficePresenter::event($event))
            ->values();

        return response()->json([
            'agents' => $agents,
            'events' => $events,
            'generated_at' => now()->toIso8601String(),
        ]);
    }
}
