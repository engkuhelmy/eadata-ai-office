<?php

namespace App\Office;

use App\Models\Agent;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Throwable;

/** Hantar satu mesej Telegram bila status agent bertukar ke keadaan yang perlukan perhatian. */
class Notifier
{
    private const THROTTLE_SECONDS = 300;

    private const MESSAGES = [
        Agent::STATUS_NEEDS_APPROVAL => 'perlu approval',
        Agent::STATUS_ERROR => 'kena error',
        Agent::STATUS_RATE_LIMITED => 'kena rate limit',
    ];

    public static function statusChanged(Agent $agent, ?string $oldStatus): void
    {
        try {
            $status = $agent->status;
            if (! isset(self::MESSAGES[$status]) || $oldStatus === $status) {
                return;
            }

            // Staff demo (office:demo) sengaja hantar approval/error: jangan spam Telegram.
            if (str_starts_with((string) $agent->session_id, 'demo-')) {
                return;
            }

            $token = config('services.telegram.token');
            $chatId = config('services.telegram.chat_id');
            if (! $token || ! $chatId) {
                return;
            }

            // Satu mesej setiap agent+status dalam 5 minit
            if (! Cache::add("notify:{$agent->id}:{$status}", 1, self::THROTTLE_SECONDS)) {
                return;
            }

            // Nama, vendor, projek sahaja. Tiada target/isi fail.
            $text = sprintf(
                '⚠️ %s (%s, %s) %s',
                $agent->displayName() ?: 'Agent',
                $agent->vendor,
                $agent->project ?: 'tiada projek',
                self::MESSAGES[$status],
            );

            Http::timeout(5)->post("https://api.telegram.org/bot{$token}/sendMessage", [
                'chat_id' => $chatId,
                'text' => $text,
            ]);
        } catch (Throwable $exception) {
            // Jangan log mesej exception: boleh mengandungi URL yang ada token bot.
            Log::warning('Telegram notify failed', ['exception' => $exception::class]);
        }
    }
}
