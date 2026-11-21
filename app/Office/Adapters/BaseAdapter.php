<?php

namespace App\Office\Adapters;

use App\Office\DepartmentRouter;
use App\Office\Redactor;
use DateTimeImmutable;
use Exception;

abstract class BaseAdapter implements AdapterInterface
{
    public function __construct(
        protected Redactor $redactor,
        protected DepartmentRouter $router,
    ) {}

    protected function ts(array $payload): DateTimeImmutable
    {
        $ts = $payload['ts'] ?? null;

        try {
            if (is_numeric($ts)) {
                return (new DateTimeImmutable)->setTimestamp((int) $ts);
            }
            if (is_string($ts) && $ts !== '') {
                return new DateTimeImmutable($ts);
            }
        } catch (Exception) {
            // jatuh ke "now"
        }

        return new DateTimeImmutable;
    }

    protected function pc(array $payload): ?string
    {
        return isset($payload['pc']) && $payload['pc'] !== '' ? (string) $payload['pc'] : null;
    }

    /** basename(cwd) untuk Windows dan POSIX path. */
    protected function projectFromCwd(mixed $cwd): ?string
    {
        if (! is_string($cwd) || $cwd === '') {
            return null;
        }

        $parts = preg_split('#[\\\\/]+#', rtrim($cwd, '/\\'));
        $last = is_array($parts) ? end($parts) : false;

        return $last !== false && $last !== '' ? $last : null;
    }

    protected function str(array $data, string $key): ?string
    {
        return isset($data[$key]) && is_scalar($data[$key]) && (string) $data[$key] !== ''
            ? (string) $data[$key]
            : null;
    }
}
