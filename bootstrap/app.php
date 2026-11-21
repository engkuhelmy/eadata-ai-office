<?php

use App\Http\Middleware\AuthenticateDevice;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;
use Illuminate\Http\Request;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        channels: __DIR__.'/../routes/channels.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware): void {
        $middleware->alias([
            'device.token' => AuthenticateDevice::class,
        ]);

        // Di belakang Cloudflare Tunnel / reverse proxy: percaya header X-Forwarded-*
        // supaya URL, scheme (https) dan IP klien betul. Kalau TRUSTED_PROXIES tak
        // diset, tak buat apa-apa (default Laravel kekal).
        // Nilai: "*" (semua) atau senarai IP/CIDR dipisah koma, cth "127.0.0.1,10.0.0.0/8".
        $trusted = trim((string) env('TRUSTED_PROXIES', ''));
        if ($trusted !== '') {
            $middleware->trustProxies(
                at: $trusted === '*' ? '*' : array_values(array_filter(array_map('trim', explode(',', $trusted)))),
                headers: Request::HEADER_X_FORWARDED_FOR
                    | Request::HEADER_X_FORWARDED_HOST
                    | Request::HEADER_X_FORWARDED_PORT
                    | Request::HEADER_X_FORWARDED_PROTO,
            );
        }
    })
    ->withExceptions(function (Exceptions $exceptions): void {
        //
    })->create();
