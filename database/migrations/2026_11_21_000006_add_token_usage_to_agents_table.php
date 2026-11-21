<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            // Jumlah token sesi (diganti, bukan ditambah, setiap kali hook Stop hantar total baru).
            $table->unsignedBigInteger('tokens_in')->default(0);
            $table->unsignedBigInteger('tokens_out')->default(0);
            $table->unsignedBigInteger('tokens_cache_read')->default(0);
            $table->unsignedBigInteger('tokens_cache_create')->default(0);
        });
    }

    public function down(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            $table->dropColumn(['tokens_in', 'tokens_out', 'tokens_cache_read', 'tokens_cache_create']);
        });
    }
};
