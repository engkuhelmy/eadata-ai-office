<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            // Pusingan kerja: bila mula (event kerja pertama selepas rehat), bila siap (turn_done), tempoh pusingan terakhir.
            $table->timestamp('turn_started_at')->nullable()->after('ended_at');
            $table->timestamp('done_at')->nullable()->after('turn_started_at');
            $table->unsignedInteger('last_turn_seconds')->nullable()->after('done_at');
            // Subagent (intern) yang sedang berjalan untuk sesi ini
            $table->unsignedTinyInteger('subagents')->default(0)->after('last_turn_seconds');
        });
    }

    public function down(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            $table->dropColumn(['turn_started_at', 'done_at', 'last_turn_seconds', 'subagents']);
        });
    }
};
