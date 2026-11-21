<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            // Ditetapkan oleh owner dari UI. Null = ikut nilai automatik dari event.
            $table->string('custom_name', 100)->nullable()->after('name');
            $table->string('pinned_department', 30)->nullable()->after('department');
        });
    }

    public function down(): void
    {
        Schema::table('agents', function (Blueprint $table) {
            $table->dropColumn(['custom_name', 'pinned_department']);
        });
    }
};
