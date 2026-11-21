<?php

namespace App\Office;

class Redactor
{
    public const MAX_TARGET_LENGTH = 200;

    /** @var array<string, string> pattern => replacement */
    private const PATTERNS = [
        '/sk-[A-Za-z0-9_\-]{16,}/' => 'sk-***',
        '/gh[pousr]_[A-Za-z0-9]{20,}/' => 'gh_***',
        '/AKIA[0-9A-Z]{16}/' => 'AKIA***',
        '/\bBearer\s+\S+/i' => 'Bearer ***',
        '/\b(password|passwd|secret|token|api[_-]?key)(\s*[=:]\s*)\S+/i' => '$1$2***',
    ];

    /**
     * Mask secret dalam teks, buang baris ".env" (KEY=value), dan potong ke 200 aksara.
     * Null dikembalikan kalau input kosong.
     */
    public function target(?string $value): ?string
    {
        if ($value === null || $value === '') {
            return null;
        }

        $clean = $this->scrub($value);

        return mb_substr($clean, 0, self::MAX_TARGET_LENGTH);
    }

    public function scrub(string $text): string
    {
        // Baris berbentuk KEY=value sahaja (contoh isi .env): mask nilai
        $text = preg_replace('/^([A-Za-z_][A-Za-z0-9_]*)=\S*$/m', '$1=***', $text) ?? $text;

        foreach (self::PATTERNS as $pattern => $replacement) {
            $text = preg_replace($pattern, $replacement, $text) ?? $text;
        }

        return preg_replace('/\r?\n+/', ' ', $text) ?? $text;
    }
}
