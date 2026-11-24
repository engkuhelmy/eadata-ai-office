<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\QueryException;

/** Staf AI sebenar dari Staff OS (fail MD). Agent office mereka: vendor 'generic', session_id = key. */
class StaffMember extends Model
{
    public const VENDOR = 'generic';

    protected $fillable = [
        'key', 'name', 'role', 'unit', 'project', 'reports_to', 'team', 'fasa', 'home_department', 'room',
        'avatar', 'scope', 'limits', 'handoffs', 'brief', 'source_file', 'is_active', 'checked_in_at',
    ];

    protected function casts(): array
    {
        return [
            'team' => 'array',
            'scope' => 'array',
            'limits' => 'array',
            'handoffs' => 'array',
            'fasa' => 'integer',
            'is_active' => 'boolean',
            'checked_in_at' => 'datetime',
        ];
    }

    /** Staf untuk agent (vendor + session_id), atau null. Sesi demo tak pernah dikira staf sebenar. */
    public static function forAgent(?string $vendor, ?string $sessionId): ?self
    {
        if ($vendor !== self::VENDOR || $sessionId === null || $sessionId === '' || str_starts_with($sessionId, 'demo-')) {
            return null;
        }

        try {
            return self::query()->where('key', $sessionId)->first();
        } catch (QueryException) {
            // Jadual staff_members belum di-migrate: ingest agent biasa tetap jalan
            return null;
        }
    }

    public function agent(): ?Agent
    {
        return Agent::query()->where('vendor', self::VENDOR)->where('session_id', $this->key)->first();
    }
}
