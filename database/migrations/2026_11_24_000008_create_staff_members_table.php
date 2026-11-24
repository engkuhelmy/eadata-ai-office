<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Staf AI sebenar (Staff OS). Diimport dari fail MD: php artisan office:staff-import
        Schema::create('staff_members', function (Blueprint $table) {
            $table->id();
            $table->string('key', 64)->unique(); // = "agent" dalam payload generic
            $table->string('name', 100);
            $table->string('role', 200)->nullable();
            $table->string('unit', 200)->nullable();
            $table->string('project', 64)->nullable();
            $table->string('reports_to', 100)->nullable();
            $table->json('team')->nullable();
            $table->unsignedTinyInteger('fasa')->nullable();
            $table->string('home_department', 40);
            $table->string('room', 100)->nullable();
            $table->string('avatar', 20)->nullable();
            $table->json('scope')->nullable();    // "Buat"
            $table->json('limits')->nullable();   // "Tak boleh buat"
            $table->json('handoffs')->nullable();
            $table->longText('brief');            // fail MD penuh, dihantar balik semasa check-in
            $table->string('source_file', 100)->nullable();
            $table->boolean('is_active')->default(true);
            $table->timestamp('checked_in_at')->nullable();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('staff_members');
    }
};
