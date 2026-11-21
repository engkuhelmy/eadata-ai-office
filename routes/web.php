<?php

use App\Http\Controllers\Auth\LoginController;
use App\Http\Controllers\InsightsController;
use App\Http\Controllers\OfficeController;
use Illuminate\Support\Facades\Route;

Route::middleware('guest')->group(function () {
    Route::get('/login', [LoginController::class, 'create'])->name('login');
    Route::post('/login', [LoginController::class, 'store'])->middleware('throttle:login');
});

Route::post('/logout', [LoginController::class, 'destroy'])->name('logout')->middleware('auth');

Route::middleware('auth')->group(function () {
    Route::get('/', [OfficeController::class, 'index'])->name('office');
    Route::get('/office/state', [OfficeController::class, 'state'])->name('office.state');
    Route::get('/office/insights', [InsightsController::class, 'insights'])->name('office.insights');
    Route::get('/history', [InsightsController::class, 'history'])->name('office.history');
    Route::get('/office/history.json', [InsightsController::class, 'historyJson'])->name('office.history.json');
    Route::patch('/office/agents/{agent}', [OfficeController::class, 'update'])->name('office.agents.update');
});
