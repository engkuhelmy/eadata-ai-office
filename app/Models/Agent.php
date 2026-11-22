<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Agent extends Model
{
    public const STATUS_ACTIVE = 'active';
    public const STATUS_IDLE = 'idle';
    public const STATUS_NEEDS_APPROVAL = 'needs_approval';
    public const STATUS_RATE_LIMITED = 'rate_limited';
    public const STATUS_ERROR = 'error';
    public const STATUS_ENDED = 'ended';

    /** Gaya avatar yang dibenarkan (default = rupa asal). recep = penyambut tetamu; grab/shopee/jnt/dhl = penghantar demo. */
    public const AVATARS = ['default', 'woman', 'hiphop', 'genz', 'recep', 'grab', 'shopee', 'jnt', 'dhl'];

    protected $fillable = [
        'vendor', 'session_id', 'label', 'name', 'custom_name', 'avatar', 'pc', 'project',
        'department', 'pinned_department', 'status', 'current_task', 'last_event_at', 'ended_at',
        'tokens_in', 'tokens_out', 'tokens_cache_read', 'tokens_cache_create',
    ];

    /** Nama yang dipaparkan: nama yang owner tetapkan, atau nama automatik. */
    public function displayName(): ?string
    {
        return $this->custom_name ?: $this->name;
    }

    /** Department yang dipaparkan: department yang di-pin, atau ikut event terakhir. */
    public function effectiveDepartment(): ?string
    {
        return $this->pinned_department ?: $this->department;
    }

    protected function casts(): array
    {
        return [
            'last_event_at' => 'datetime',
            'ended_at' => 'datetime',
        ];
    }

    public function events(): HasMany
    {
        return $this->hasMany(AgentEvent::class);
    }
}
