<?php

namespace App\Office\Staff;

use App\Models\StaffMember;

/**
 * Laluan staf sebenar bila payload tak hantar department: kerja di meja tetap, mesyuarat/handoff di
 * Big Meeting Room, approval/rehat ikut router biasa. Department eksplisit sentiasa dihormati (dikendalikan adapter).
 */
class StaffRouter
{
    public function route(StaffMember $staff, string $event, ?string $tool, ?string $default): ?string
    {
        $meeting = (string) config('staff.meeting_department', 'boardroom');
        $isMeetingTool = in_array(strtolower((string) $tool), (array) config('staff.meeting_tools', []), true);

        return match ($event) {
            'session_start', 'prompt' => $staff->home_department,
            'tool_start', 'tool_end' => $isMeetingTool ? $meeting : $staff->home_department,
            'subagent_start', 'subagent_stop' => $meeting,
            default => $default, // session_end (door), needs_approval, rate_limited, idle...
        };
    }
}
