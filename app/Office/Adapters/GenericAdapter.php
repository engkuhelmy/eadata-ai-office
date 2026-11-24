<?php

namespace App\Office\Adapters;

use App\Models\StaffMember;
use App\Office\DepartmentRouter;
use App\Office\NormalizedEvent;
use App\Office\Staff\StaffRouter;

class GenericAdapter extends BaseAdapter
{
    public function vendor(): string
    {
        return 'generic';
    }

    /** Format: {"agent","name","label","event","tool","target","project","department","pc","ts"} */
    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent
    {
        $agent = $this->str($payload, 'agent');
        $event = $this->str($payload, 'event') ?? $eventHint;

        if ($agent === null || $event === null || ! in_array($event, NormalizedEvent::EVENTS, true)) {
            return null;
        }

        $tool = $this->str($payload, 'tool');
        $target = $this->str($payload, 'target');
        $explicit = $this->str($payload, 'department');

        if ($explicit !== null && ! in_array($explicit, DepartmentRouter::DEPARTMENTS, true)) {
            $explicit = null;
        }

        $department = $this->router->route($event, $tool, $target, $target, $explicit);

        // Staf sebenar (Staff OS): kerja di meja tetap kalau department tak dihantar
        $staff = StaffMember::forAgent($this->vendor(), $agent);
        if ($staff !== null && $explicit === null) {
            $department = app(StaffRouter::class)->route($staff, $event, $tool, $department);
        }

        return new NormalizedEvent(
            vendor: $this->vendor(),
            agentKey: $agent,
            name: $this->str($payload, 'name') ?? $staff?->name ?? $agent,
            label: $this->str($payload, 'label') ?? ($staff !== null ? (string) config('staff.label') : 'Generic'),
            pc: $this->pc($payload),
            project: $this->str($payload, 'project') ?? $staff?->project,
            event: $event,
            tool: $tool,
            target: $this->redactor->target($target),
            department: $department,
            ts: $this->ts($payload),
        );
    }
}
