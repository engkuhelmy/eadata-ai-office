<?php

namespace App\Office;

use App\Office\Adapters\AdapterInterface;
use App\Office\Adapters\ClaudeCodeAdapter;
use App\Office\Adapters\CodexAdapter;
use App\Office\Adapters\GenericAdapter;
use App\Office\Adapters\HermesAdapter;
use InvalidArgumentException;

class AdapterRegistry
{
    /** @var array<string, AdapterInterface> */
    private array $adapters;

    public function __construct(
        ClaudeCodeAdapter $claude,
        CodexAdapter $codex,
        HermesAdapter $hermes,
        GenericAdapter $generic,
    ) {
        $this->adapters = [
            $claude->vendor() => $claude,
            $codex->vendor() => $codex,
            $hermes->vendor() => $hermes,
            $generic->vendor() => $generic,
        ];
    }

    public function has(string $src): bool
    {
        return isset($this->adapters[$src]);
    }

    public function get(string $src): AdapterInterface
    {
        if (! $this->has($src)) {
            throw new InvalidArgumentException("Unknown src: {$src}");
        }

        return $this->adapters[$src];
    }

    /** @return list<string> */
    public function vendors(): array
    {
        return array_keys($this->adapters);
    }
}
