<?php

namespace App\Jobs;

use App\Events\AgentUpdated;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Office\NormalizedEvent;
use App\Office\OfficePresenter;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
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

        $attributes = [
            'label' => $e->label,
            'name' => $e->name,
            'status' => $this->statusFor($e->event),
            'last_event_at' => $e->ts,
            'ended_at' => $e->event === 'session_end' ? $e->ts : null,
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
        if ($e->event === 'session_end') {
            $attributes['current_task'] = null;
        }

        $agent = Agent::updateOrCreate(
            ['vendor' => $e->vendor, 'session_id' => $e->agentKey],
            $attributes,
        );

        $row = AgentEvent::create([
            'agent_id' => $agent->id,
            'event' => $e->event,
            'tool' => $e->tool,
            'target' => $e->target,
            'department' => $e->department,
            'ts' => $e->ts,
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
