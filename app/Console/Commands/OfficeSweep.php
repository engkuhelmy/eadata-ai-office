<?php

namespace App\Console\Commands;

use App\Events\AgentUpdated;
use App\Models\Agent;
use App\Models\StaffMember;
use App\Office\OfficePresenter;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;
use Throwable;

class OfficeSweep extends Command
{
    protected $signature = 'office:sweep
        {--chill=120 : Saat idle sebelum staff pergi ke bilik bermain}
        {--idle=600 : Saat tanpa event sebelum agent aktif dianggap idle}
        {--end=3600 : Saat tanpa event sebelum agent dianggap tamat}';

    protected $description = 'Kemas kini keadaan staff: idle (10 min), tamat (60 min), dan chill ke bilik bermain (2 min idle)';

    public function handle(): int
    {
        $now = now();
        $chillAfter = $now->copy()->subSeconds((int) $this->option('chill'));
        $idleAfter = $now->copy()->subSeconds((int) $this->option('idle'));
        $endAfter = $now->copy()->subSeconds((int) $this->option('end'));

        $changed = 0;
        // Staf sebenar (Staff OS): senyap 60 min = Off di meja tetap, bukan tamat
        $staffHome = StaffMember::query()->pluck('home_department', 'key');

        Agent::query()->whereNull('ended_at')->each(function (Agent $agent) use ($now, $chillAfter, $idleAfter, $endAfter, $staffHome, &$changed) {
            $last = $agent->last_event_at ?? $agent->updated_at;

            // Sesi demo (office:demo) tak pernah ditamatkan oleh sweep, walaupun proses demo terhenti.
            $isDemo = str_starts_with((string) $agent->session_id, 'demo-');
            $home = $agent->vendor === StaffMember::VENDOR && ! $isDemo ? $staffHome->get($agent->session_id) : null;

            if ($home !== null) {
                if ($agent->status === Agent::STATUS_OFF) {
                    return;
                }
                if ($last < $endAfter) {
                    $agent->fill(['status' => Agent::STATUS_OFF, 'current_task' => null, 'department' => $home]);
                }
            }

            if ($agent->status === Agent::STATUS_OFF) {
                // ditandakan Off di atas: tiada idle/chill
            } elseif ($last < $endAfter && ! $isDemo) {
                $agent->fill(['status' => Agent::STATUS_ENDED, 'ended_at' => $now, 'current_task' => null]);
            } else {
                // needs_approval sengaja dibiar: agent tu memang tunggu manusia
                if ($last < $idleAfter && in_array($agent->status, [Agent::STATUS_ACTIVE, Agent::STATUS_ERROR, Agent::STATUS_RATE_LIMITED], true)) {
                    $agent->status = Agent::STATUS_IDLE;
                }

                $chill = $agent->status === Agent::STATUS_IDLE
                    && $last < $chillAfter
                    && $agent->pinned_department === null
                    && $agent->department !== 'playroom';

                if ($chill) {
                    $agent->department = 'playroom';
                    $agent->current_task = null;
                }
            }

            if (! $agent->isDirty()) {
                return;
            }

            $agent->save();
            $changed++;

            try {
                AgentUpdated::dispatch(OfficePresenter::agent($agent->refresh()));
            } catch (Throwable $exception) {
                Log::warning('AgentUpdated broadcast failed (sweep)', ['message' => $exception->getMessage()]);
            }
        });

        $this->info("Sweep selesai: {$changed} staff dikemas kini.");

        return self::SUCCESS;
    }
}
