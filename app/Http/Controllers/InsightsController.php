<?php

namespace App\Http\Controllers;

use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\Device;
use App\Office\OfficePresenter;
use Illuminate\Contracts\View\View;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\DB;

class InsightsController extends Controller
{
    private const VENDORS = [
        'claude' => 'Claude Code',
        'codex' => 'Codex',
        'hermes' => 'Hermes',
        'antigravity' => 'Antigravity',
    ];

    private const HISTORY_PAGE_SIZE = 50;

    public function insights(): JsonResponse
    {
        $now = now();

        return response()->json([
            'health' => [
                'server_time' => $now->toIso8601String(),
                'vendors' => $this->vendors($now),
                'devices' => Device::query()->orderBy('name')->get()->map(fn (Device $d) => [
                    'id' => $d->id,
                    'name' => $d->name,
                    'last_used_at' => $d->last_used_at?->toIso8601String(),
                    'revoked' => $d->revoked_at !== null,
                ])->values(),
            ],
            'stats' => [
                'today' => $this->today($now),
                'hourly' => $this->hourly($now),
            ],
            'board' => $this->board($now),
        ]);
    }

    public function history(): View
    {
        return view('history');
    }

    public function historyJson(Request $request): JsonResponse
    {
        $data = $request->validate([
            'date' => ['nullable', 'date_format:Y-m-d'],
            'vendor' => ['nullable', 'string', 'max:20'],
            'project' => ['nullable', 'string', 'max:191'],
            'pc' => ['nullable', 'string', 'max:100'],
            'agent_id' => ['nullable', 'integer', 'min:1'],
            'page' => ['nullable', 'integer', 'min:1'],
        ]);

        $day = ! empty($data['date']) ? Carbon::createFromFormat('Y-m-d', $data['date']) : now();
        $page = (int) ($data['page'] ?? 1);

        $agentFilters = array_filter([
            'vendor' => $data['vendor'] ?? null,
            'project' => $data['project'] ?? null,
            'pc' => $data['pc'] ?? null,
        ], fn ($v) => $v !== null && $v !== '');

        $rows = AgentEvent::query()
            ->with('agent')
            ->whereBetween('ts', [$day->copy()->startOfDay(), $day->copy()->endOfDay()])
            ->when($data['agent_id'] ?? null, fn ($q, $id) => $q->where('agent_id', $id))
            ->when($agentFilters, fn ($q, array $filters) => $q->whereHas('agent', function ($agent) use ($filters) {
                foreach ($filters as $column => $value) {
                    $agent->where($column, $value);
                }
            }))
            ->orderByDesc('ts')
            ->orderByDesc('id')
            ->offset(($page - 1) * self::HISTORY_PAGE_SIZE)
            ->limit(self::HISTORY_PAGE_SIZE + 1)
            ->get();

        return response()->json([
            'data' => $rows->take(self::HISTORY_PAGE_SIZE)->map(fn (AgentEvent $e) => [
                'id' => $e->id,
                'agent_id' => $e->agent_id,
                'agent' => $e->agent?->displayName(),
                'vendor' => $e->agent?->vendor,
                'project' => $e->agent?->project,
                'pc' => $e->agent?->pc,
                'event' => $e->event,
                'tool' => $e->tool,
                'target' => $e->target,
                'department' => $e->department,
                'ts' => $e->ts?->toIso8601String(),
            ])->values(),
            'page' => $page,
            'has_more' => $rows->count() > self::HISTORY_PAGE_SIZE,
        ]);
    }

    private function vendors(Carbon $now): array
    {
        $active = Agent::query()
            ->whereNull('ended_at')
            ->where('status', '!=', Agent::STATUS_OFF)
            ->select('vendor', DB::raw('COUNT(*) as total'))
            ->groupBy('vendor')
            ->pluck('total', 'vendor');

        $lastSeen = Agent::query()
            ->select('vendor', DB::raw('MAX(last_event_at) as last_at'))
            ->groupBy('vendor')
            ->pluck('last_at', 'vendor');

        $events = AgentEvent::query()
            ->join('agents', 'agents.id', '=', 'agent_events.agent_id')
            ->where('agent_events.ts', '>=', $now->copy()->subDay())
            ->select('agents.vendor', DB::raw('COUNT(*) as total'))
            ->groupBy('agents.vendor')
            ->pluck('total', 'vendor');

        return collect(array_keys(self::VENDORS))
            ->merge($lastSeen->keys())
            ->unique()
            ->map(fn (string $vendor) => [
                'vendor' => $vendor,
                'label' => self::VENDORS[$vendor] ?? ucfirst($vendor),
                'agents' => (int) ($active[$vendor] ?? 0),
                'last_event_at' => ($last = $lastSeen[$vendor] ?? null) ? Carbon::parse($last)->toIso8601String() : null,
                'events_24h' => (int) ($events[$vendor] ?? 0),
            ])
            ->values()
            ->all();
    }

    private function today(Carbon $now): array
    {
        $start = $now->copy()->startOfDay();

        $byDepartment = AgentEvent::query()
            ->where('ts', '>=', $start)
            ->whereNotNull('department')
            ->select('department', DB::raw('COUNT(*) as total'))
            ->groupBy('department')
            ->pluck('total', 'department')
            ->map(fn ($n) => (int) $n)
            ->all();

        $byVendor = AgentEvent::query()
            ->join('agents', 'agents.id', '=', 'agent_events.agent_id')
            ->where('agent_events.ts', '>=', $start)
            ->select('agents.vendor', DB::raw('COUNT(*) as total'))
            ->groupBy('agents.vendor')
            ->pluck('total', 'vendor')
            ->map(fn ($n) => (int) $n)
            ->all();

        return [
            'events' => AgentEvent::query()->where('ts', '>=', $start)->count(),
            'errors' => AgentEvent::query()->where('ts', '>=', $start)->whereIn('event', ['tool_error', 'error'])->count(),
            'active_agents' => Agent::query()->whereNull('ended_at')->where('status', '!=', Agent::STATUS_OFF)->count(),
            // Objek (bukan array) supaya kosong jadi {} dalam JSON
            'by_department' => (object) $byDepartment,
            'by_vendor' => (object) $byVendor,
        ];
    }

    private function hourly(Carbon $now): array
    {
        $first = $now->copy()->startOfHour()->subHours(23);

        $buckets = [];
        for ($i = 0; $i < 24; $i++) {
            $buckets[$first->copy()->addHours($i)->format('Y-m-d H')] = 0;
        }

        // Kira dalam SQL ikut jam ('Y-m-d H' = 13 aksara pertama ts). Dulu setiap ts 24 jam dimuat sebagai Carbon:
        // dengan demo 24 jam (~170k event sehari) PHP kehabisan memori dan /office/insights pulang 500.
        AgentEvent::query()
            ->where('ts', '>=', $first)
            ->selectRaw('substr(ts, 1, 13) as hour_key, COUNT(*) as total')
            ->groupBy('hour_key')
            ->pluck('total', 'hour_key')
            ->each(function ($total, $key) use (&$buckets) {
                if (isset($buckets[$key])) {
                    $buckets[$key] = (int) $total;
                }
            });

        $out = [];
        foreach ($buckets as $key => $count) {
            $out[] = ['hour' => substr($key, 11, 2), 'events' => $count];
        }

        return $out;
    }

    private function board(Carbon $now): array
    {
        $present = fn (Agent $a) => OfficePresenter::agent($a);

        $doing = Agent::query()->whereNull('ended_at')
            ->where('status', Agent::STATUS_ACTIVE)
            ->orderByDesc('last_event_at')->get();

        $attention = Agent::query()->whereNull('ended_at')
            ->whereIn('status', [Agent::STATUS_NEEDS_APPROVAL, Agent::STATUS_ERROR, Agent::STATUS_RATE_LIMITED])
            ->orderByDesc('last_event_at')->get();

        $done = Agent::query()->whereNull('ended_at')
            ->where('status', Agent::STATUS_IDLE)
            ->where('last_event_at', '>=', $now->copy()->subMinutes(30))
            ->orderByDesc('last_event_at')->limit(10)->get();

        return [
            'doing' => $doing->map($present)->values(),
            'attention' => $attention->map($present)->values(),
            'done' => $done->map($present)->values(),
        ];
    }
}
