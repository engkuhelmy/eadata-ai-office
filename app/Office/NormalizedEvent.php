<?php

namespace App\Office;

use DateTimeImmutable;
use InvalidArgumentException;

final readonly class NormalizedEvent
{
    public const EVENTS = [
        'session_start', 'prompt', 'tool_start', 'tool_end', 'tool_error',
        'needs_approval', 'subagent_start', 'subagent_stop', 'turn_done',
        'idle', 'rate_limited', 'error', 'compact', 'session_end',
    ];

    public function __construct(
        public string $vendor,
        public string $agentKey,
        public string $name,
        public string $label,
        public ?string $pc,
        public ?string $project,
        public string $event,
        public ?string $tool,
        public ?string $target,
        public ?string $department,
        public DateTimeImmutable $ts,
        /** @var array{input:int,output:int,cache_read:int,cache_create:int}|null Jumlah token sesi (Claude Stop). */
        public ?array $usage = null,
    ) {
        if (! in_array($event, self::EVENTS, true)) {
            throw new InvalidArgumentException("Unknown event: {$event}");
        }
    }
}
