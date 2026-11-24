<?php

use App\Http\Controllers\IngestController;
use App\Http\Controllers\StaffCheckinController;
use Illuminate\Support\Facades\Route;

Route::post('/ingest', IngestController::class)
    ->middleware(['device.token', 'throttle:ingest'])
    ->name('api.ingest');

// Staf sebenar (Staff OS) check in dan terima brief
Route::post('/staff/checkin', StaffCheckinController::class)
    ->middleware(['device.token', 'throttle:ingest'])
    ->name('api.staff.checkin');
