<?php

namespace App\Http\Middleware;

use App\Models\Device;
use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

class AuthenticateDevice
{
    public function handle(Request $request, Closure $next): Response
    {
        $token = $request->bearerToken();

        if (! is_string($token) || ! str_starts_with($token, 'eod_')) {
            return $this->unauthorized();
        }

        $device = Device::query()
            ->where('token_hash', hash('sha256', $token))
            ->whereNull('revoked_at')
            ->first();

        if ($device === null) {
            return $this->unauthorized();
        }

        if ($device->last_used_at === null || $device->last_used_at->lt(now()->subMinute())) {
            $device->forceFill(['last_used_at' => now()])->saveQuietly();
        }

        $request->attributes->set('device', $device);

        return $next($request);
    }

    private function unauthorized(): Response
    {
        return response()->json(['message' => 'Unauthenticated.'], 401);
    }
}
