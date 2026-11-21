<?php

use Illuminate\Foundation\Inspiring;
use Illuminate\Support\Facades\Artisan;
use Illuminate\Support\Facades\Schedule;

// Setiap minit: idle 10 min, tamat 60 min, dan chill ke bilik bermain selepas idle 2 min.
// Perlu `php artisan schedule:work` berjalan.
Schedule::command('office:sweep')->everyMinute()->withoutOverlapping();

Artisan::command('inspire', function () {
    $this->comment(Inspiring::quote());
})->purpose('Display an inspiring quote');
