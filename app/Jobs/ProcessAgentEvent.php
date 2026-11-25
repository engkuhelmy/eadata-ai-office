<?php

namespace App\Jobs;

use App\Events\AgentUpdated;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\StaffMember;
use App\Office\NormalizedEvent;
use App\Office\Notifier;
use App\Office\OfficePresenter;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;
use Throwable;

class ProcessAgentEvent implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public function __construct(public NormalizedEvent $event) {}

    public function handle(): void
    {
        $e = $this->event;

        // Hook hantar waktu tempatan dengan ofset (cth. +08:00). Eloquent simpan jam tanpa tukar zon,
        // jadi tukar ke zon app (UTC) dulu supaya sweep dan perbandingan masa betul.
        $ts = Carbon::instance($e->ts)->setTimezone(config('app.timezone'));

        // Staf sebenar tak pernah "tamat": session_end = Off, kekal dalam senarai Team
        $isStaff = StaffMember::forAgent($e->vendor, $e->agentKey) !== null;
        $status = $this->statusFor($e->event);
        if ($isStaff && $status === Agent::STATUS_ENDED) {
            $status = Agent::STATUS_OFF;
        }

        $attributes = [
            'label' => $e->label,
            'name' => $e->name,
            'status' => $status,
            'last_event_at' => $ts,
            'ended_at' => $e->event === 'session_end' && ! $isStaff ? $ts : null,
        ];

        if ($e->pc !== null) {
            $attributes['pc'] = $e->pc;
        }
        if ($e->project !== null) {
            $attributes['project'] = $e->project;
        }
        if ($e->department !== null) {
            $attributes['department'] = $e->department;
        }
        if (in_array($e->event, ['tool_start', 'tool_end'], true)) {
            $attributes['current_task'] = $this->taskFor($e);
        }
        // Bubble approval tunjuk perkara yang perlu diluluskan, bukan tugas lama
        if ($e->event === 'needs_approval') {
            $item = $e->tool ?? $e->target;
            $attributes['current_task'] = $item !== null ? Str::limit('Approval: '.$item, 60) : 'Perlu approval';
        }
        // Rehat/chill: buang bubble tugas lama supaya tak tinggal "Editing X" yang basi.
        if (in_array($e->event, ['session_end', 'idle', 'turn_done'], true)) {
            $attributes['current_task'] = null;
        }

        if ($e->usage !== null) {
            // Ganti (bukan tambah): hook hantar jumlah keseluruhan transkrip setiap Stop.
            $attributes['tokens_in'] = $e->usage['input'];
            $attributes['tokens_out'] = $e->usage['output'];
            $attributes['tokens_cache_read'] = $e->usage['cache_read'];
            $attributes['tokens_cache_create'] = $e->usage['cache_create'];
        }

        $old = Agent::query()
            ->where('vendor', $e->vendor)
            ->where('session_id', $e->agentKey)
            ->first(['status', 'turn_started_at', 'subagents']);
        $oldStatus = $old?->status;

        $attributes += $this->turnAttributes($e->event, $ts, $old);

        $agent = Agent::updateOrCreate(
            ['vendor' => $e->vendor, 'session_id' => $e->agentKey],
            $attributes,
        );

        Notifier::statusChanged($agent, $oldStatus);

        $row = AgentEvent::create([
            'agent_id' => $agent->id,
            'event' => $e->event,
            'tool' => $e->tool,
            'target' => $e->target,
            'department' => $e->department,
            'ts' => $ts,
        ]);

        try {
            AgentUpdated::dispatch(
                OfficePresenter::agent($agent->refresh()),
                OfficePresenter::event($row->load('agent')),
            );
        } catch (Throwable $exception) {
            // Reverb down: frontend fallback polling /office/state akan pulihkan
            Log::warning('AgentUpdated broadcast failed', ['message' => $exception->getMessage()]);
        }
    }

    /**
     * Pusingan kerja + intern. Event kerja pertama selepas rehat mula pusingan; turn_done tutup pusingan
     * (done_at = "Siap, tunggu arahan", last_turn_seconds untuk pentas pelancaran). Arahan baru buang tanda siap.
     */
    private function turnAttributes(string $event, Carbon $ts, ?Agent $old): array
    {
        $started = $old?->turn_started_at;
        $subagents = (int) ($old?->subagents ?? 0);

        return match ($event) {
            'turn_done' => [
                'done_at' => $ts,
                'last_turn_seconds' => $started !== null ? (int) round(abs($started->diffInSeconds($ts))) : null,
                'turn_started_at' => null,
                'subagents' => 0,
            ],
            'session_end' => ['turn_started_at' => null, 'done_at' => null, 'subagents' => 0],
            'idle' => ['turn_started_at' => null],
            'session_start' => [],
            default => array_filter([
                'turn_started_at' => $started ?? $ts,
                'subagents' => match ($event) {
                    'subagent_start' => min(Agent::MAX_SUBAGENTS, $subagents + 1),
                    'subagent_stop' => max(0, $subagents - 1),
                    default => null,
                },
            ], fn ($v) => $v !== null) + ['done_at' => null],
        };
    }

    private function statusFor(string $event): string
    {
        return match ($event) {
            'tool_error', 'error' => Agent::STATUS_ERROR,
            'needs_approval' => Agent::STATUS_NEEDS_APPROVAL,
            'rate_limited' => Agent::STATUS_RATE_LIMITED,
            'idle', 'turn_done' => Agent::STATUS_IDLE,
            'session_end' => Agent::STATUS_ENDED,
            default => Agent::STATUS_ACTIVE,
        };
    }

    /** Label bubble, contoh: "Editing navbar.vue", "Running pytest". */
    private function taskFor(NormalizedEvent $e): ?string
    {
        $file = $e->target !== null ? basename(str_replace('\\', '/', $e->target)) : null;

        return match (true) {
            in_array($e->tool, ['Edit', 'Write', 'MultiEdit', 'NotebookEdit'], true) => $file ? "Editing {$file}" : 'Editing',
            $e->tool === 'Read' => $file ? "Reading {$file}" : 'Reading',
            in_array($e->tool, ['Bash', 'PowerShell'], true) => 'Running '.Str::limit((string) $e->target, 40),
            $e->tool !== null => (string) $e->tool,
            default => null,
        };
    }
}
