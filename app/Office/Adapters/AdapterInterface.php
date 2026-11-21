<?php

namespace App\Office\Adapters;

use App\Office\NormalizedEvent;

interface AdapterInterface
{
    /** Nama vendor yang dipakai dalam ?src= (claude, codex, hermes, generic). */
    public function vendor(): string;

    /**
     * Tukar payload mentah (dah ditambah pc + ts oleh office-hook) jadi NormalizedEvent.
     * Null = event tak dikenali atau tak relevan (controller balas 422 untuk generic).
     */
    public function normalize(array $payload, ?string $eventHint = null): ?NormalizedEvent;
}
