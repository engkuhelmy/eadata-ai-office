<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('agents', function (Blueprint $table) {
            $table->id();
            $table->string('vendor', 20);
            $table->string('session_id', 191);
            $table->string('label', 100)->nullable();
            $table->string('name', 100)->nullable();
            $table->string('pc', 100)->nullable();
            $table->string('project', 191)->nullable();
            $table->string('department', 30)->nullable();
            $table->string('status', 20)->default('idle');
            $table->string('current_task', 200)->nullable();
            $table->timestamp('last_event_at')->nullable();
            $table->timestamp('ended_at')->nullable();
            $table->timestamps();

            $table->unique(['vendor', 'session_id']);
            $table->index('project');
            $table->index('status');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agents');
    }
};
