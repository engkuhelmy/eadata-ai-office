<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('agent_events', function (Blueprint $table) {
            // Statistik /office/insights tapis ikut ts sahaja (hari ini, 24 jam). Tanpa index ini setiap query imbas semua baris.
            $table->index('ts');
        });
    }

    public function down(): void
    {
        Schema::table('agent_events', function (Blueprint $table) {
            $table->dropIndex(['ts']);
        });
    }
};
