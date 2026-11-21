<?php

namespace App\Http\Controllers;

use App\Events\AgentUpdated;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Office\DepartmentRouter;
use App\Office\OfficePresenter;
use Illuminate\Contracts\View\View;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Log;
use Illuminate\Validation\Rule;
use Throwable;

class OfficeController extends Controller
{
    public function index(Request $request): View
    {
        return view('office', [
            'canEdit' => $request->user()?->role === 'owner',
            'departments' => DepartmentRouter::DEPARTMENTS,
        ]);
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

    /** Owner tukar nama paparan dan pin department. Nilai kosong = kembali automatik. */
    public function update(Request $request, Agent $agent): JsonResponse
    {
        abort_unless($request->user()?->role === 'owner', 403, 'Hanya owner boleh ubah staff.');

        $data = $request->validate([
            'name' => ['nullable', 'string', 'max:100'],
            'department' => ['nullable', 'string', Rule::in(DepartmentRouter::DEPARTMENTS)],
        ]);

        $name = trim((string) ($data['name'] ?? ''));
        $agent->custom_name = $name !== '' ? $name : null;
        $agent->pinned_department = $data['department'] ?? null;
        $agent->save();

        $payload = OfficePresenter::agent($agent);

        try {
            AgentUpdated::dispatch($payload);
        } catch (Throwable $exception) {
            Log::warning('AgentUpdated broadcast failed', ['message' => $exception->getMessage()]);
        }

        return response()->json(['agent' => $payload]);
    }
}
