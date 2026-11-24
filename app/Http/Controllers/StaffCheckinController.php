<?php

namespace App\Http\Controllers;

use App\Jobs\ProcessAgentEvent;
use App\Models\StaffMember;
use App\Office\NormalizedEvent;
use App\Office\Staff\StaffFileParser;
use DateTimeImmutable;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

/**
 * Staf sebenar check in: office sahkan identiti, staf berjalan masuk ke meja tetap,
 * dan office balas brief penuh (jawatan, skop, SOP, handoff, peraturan wajib, workflow).
 */
class StaffCheckinController extends Controller
{
    public function __invoke(Request $request, StaffFileParser $parser): JsonResponse
    {
        $data = $request->validate([
            'agent' => ['required', 'string', 'max:64'],
            'pc' => ['nullable', 'string', 'max:100'],
        ]);

        $key = strtolower(trim($data['agent']));
        $staff = StaffMember::query()->where('key', $key)->first();

        if ($staff === null) {
            return response()->json([
                'status' => 'unknown_staff',
                'message' => "Staf '{$key}' tak berdaftar dalam Staff OS. Tanya Mira atau Pak Engku sebelum mula kerja.",
            ], 404);
        }
        if (! $staff->is_active) {
            return response()->json([
                'status' => 'inactive',
                'message' => "{$staff->name} tidak aktif dalam Staff OS. Jangan mula kerja; rujuk Mira.",
            ], 403);
        }

        $pc = $data['pc'] ?? $request->attributes->get('device')?->name;

        ProcessAgentEvent::dispatchSync(new NormalizedEvent(
            vendor: StaffMember::VENDOR,
            agentKey: $staff->key,
            name: $staff->name,
            label: (string) config('staff.label'),
            pc: $pc,
            project: $staff->project,
            event: 'session_start',
            tool: 'check_in',
            target: $staff->role,
            department: $staff->home_department,
            ts: new DateTimeImmutable,
        ));

        $staff->forceFill(['checked_in_at' => now()])->save();

        $readme = $this->readme();

        return response()->json([
            'status' => 'checked_in',
            'message' => "Selamat datang, {$staff->name}. Baca brief di bawah sebelum mula kerja. Lapor kepada {$staff->reports_to}.",
            'staff' => [
                'agent' => $staff->key,
                'name' => $staff->name,
                'role' => $staff->role,
                'unit' => $staff->unit,
                'project' => $staff->project,
                'reports_to' => $staff->reports_to,
                'team' => $staff->team ?? [],
                'fasa' => $staff->fasa,
                'desk' => ['department' => $staff->home_department, 'room' => $staff->room],
            ],
            'scope' => [
                'buat' => $staff->scope ?? [],
                'tak_boleh_buat' => $staff->limits ?? [],
            ],
            'handoffs' => $staff->handoffs ?? [],
            'rules' => $readme !== null ? $parser->bulletsUnder($readme, 'Peraturan wajib') : [],
            'handoff_format' => $readme !== null ? $parser->codeUnder($readme, 'Format handoff') : null,
            'workflow' => array_values((array) config('staff.workflow', [])),
            'ingest' => [
                'url' => url('/api/ingest?src=generic'),
                'example' => [
                    'agent' => $staff->key,
                    'event' => 'tool_start',
                    'tool' => 'nama_tugasan',
                    'target' => 'ringkasan tanpa PII',
                ],
                'events' => ['tool_start', 'tool_end', 'tool_error', 'needs_approval', 'idle', 'session_end'],
            ],
            'brief_markdown' => $staff->brief,
        ]);
    }

    private function readme(): ?string
    {
        $path = rtrim((string) config('staff.path'), '/\\').DIRECTORY_SEPARATOR.'README.md';

        return is_file($path) ? (string) file_get_contents($path) : null;
    }
}
