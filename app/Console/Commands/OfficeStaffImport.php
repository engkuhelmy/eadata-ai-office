<?php

namespace App\Console\Commands;

use App\Events\AgentUpdated;
use App\Models\Agent;
use App\Models\StaffMember;
use App\Office\DepartmentRouter;
use App\Office\OfficePresenter;
use App\Office\Staff\StaffFileParser;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;
use Throwable;

class OfficeStaffImport extends Command
{
    protected $signature = 'office:staff-import
        {path? : Folder fail MD Staff OS (default config staff.path)}
        {--deactivate-missing : Nyahaktif staf yang tiada lagi dalam folder}';

    protected $description = 'Import staf AI sebenar (Staff OS) dari fail MD: profil, skop, handoff dan meja tetap';

    public function handle(StaffFileParser $parser): int
    {
        $dir = rtrim((string) ($this->argument('path') ?? config('staff.path')), '/\\');
        $files = glob($dir.DIRECTORY_SEPARATOR.'*.md') ?: [];
        $files = array_values(array_filter($files, fn ($f) => strcasecmp(basename($f), 'README.md') !== 0));

        if ($files === []) {
            $this->error("Tiada fail MD staf dalam {$dir}");

            return self::FAILURE;
        }

        $placements = (array) config('staff.placements', []);
        $seen = [];
        $rows = [];

        foreach ($files as $file) {
            $data = $parser->parse((string) file_get_contents($file));
            $key = $data['key'];

            if ($key === null || $data['name'] === null) {
                $this->warn(basename($file).': tiada office_hub.agent atau name, dilangkau.');

                continue;
            }

            $place = $placements[$key] ?? [];
            $home = $place['home'] ?? null;
            if (! in_array($home, DepartmentRouter::DEPARTMENTS, true)) {
                $home = in_array($data['department'], DepartmentRouter::DEPARTMENTS, true) ? $data['department'] : 'head_office';
            }

            $staff = StaffMember::updateOrCreate(['key' => $key], [
                'name' => $data['name'],
                'role' => $data['role'],
                'unit' => $data['unit'],
                'project' => $place['project'] ?? null,
                'reports_to' => $data['reports_to'],
                'team' => $data['team'],
                'fasa' => $data['fasa'],
                'home_department' => $home,
                'room' => $place['room'] ?? null,
                'avatar' => $place['avatar'] ?? null,
                'scope' => $data['scope'],
                'limits' => $data['limits'],
                'handoffs' => $data['handoffs'],
                'brief' => (string) file_get_contents($file),
                'source_file' => basename($file),
                'is_active' => true,
            ]);

            $this->syncAgent($staff);
            $seen[] = $key;
            $rows[] = [$key, $staff->name, $staff->role, $staff->room ?? $home, count($data['scope']), count($data['handoffs'])];
        }

        if ($this->option('deactivate-missing')) {
            StaffMember::query()->whereNotIn('key', $seen)->update(['is_active' => false]);
        }

        $this->table(['agent', 'Nama', 'Jawatan', 'Meja', 'Skop', 'Handoff'], $rows);
        $this->info(count($rows).' staf diimport.');

        return self::SUCCESS;
    }

    /** Pastikan staf ada dalam senarai Team sebagai Off, tanpa ganggu sesi yang sedang aktif. */
    private function syncAgent(StaffMember $staff): void
    {
        $agent = Agent::firstOrNew(['vendor' => StaffMember::VENDOR, 'session_id' => $staff->key]);
        $agent->name = $staff->name;
        $agent->label = (string) config('staff.label');
        $agent->project = $staff->project;

        if (! $agent->exists || $agent->ended_at !== null) {
            $agent->fill([
                'status' => Agent::STATUS_OFF,
                'department' => $staff->home_department,
                'ended_at' => null,
                'current_task' => null,
            ]);
        }
        if (! $agent->exists && $agent->avatar === null && $staff->avatar !== null && $staff->avatar !== 'default') {
            $agent->avatar = $staff->avatar;
        }

        if (! $agent->isDirty()) {
            return;
        }

        $agent->save();

        try {
            AgentUpdated::dispatch(OfficePresenter::agent($agent->refresh()));
        } catch (Throwable $exception) {
            Log::warning('AgentUpdated broadcast failed (staff import)', ['message' => $exception->getMessage()]);
        }
    }
}
