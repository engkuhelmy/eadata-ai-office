<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AgentEvent extends Model
{
    protected $fillable = ['agent_id', 'event', 'tool', 'target', 'department', 'ts'];

    protected function casts(): array
    {
        return [
            'ts' => 'datetime',
        ];
    }

    public function agent(): BelongsTo
    {
        return $this->belongsTo(Agent::class);
    }
}
