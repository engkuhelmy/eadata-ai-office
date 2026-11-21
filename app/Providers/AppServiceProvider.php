<?php

namespace App\Providers;

use Illuminate\Cache\RateLimiting\Limit;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\RateLimiter;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Ingest: satu PC boleh ada banyak agent serentak (setiap tool = 2 event), jadi 120/min terlalu ketat.
        // Boleh ditukar dengan INGEST_RATE_PER_MINUTE. Per device (fallback IP kalau token tak sah).
        RateLimiter::for('ingest', function (Request $request) {
            $device = $request->attributes->get('device');

            return Limit::perMinute((int) env('INGEST_RATE_PER_MINUTE', 600))->by($device?->id ? 'device:'.$device->id : 'ip:'.$request->ip());
        });

        // Login: 5 cubaan setiap 5 minit ikut email + IP
        RateLimiter::for('login', function (Request $request) {
            $email = strtolower((string) $request->input('email'));

            return Limit::perMinutes(5, 5)->by($email.'|'.$request->ip());
        });
    }
}
