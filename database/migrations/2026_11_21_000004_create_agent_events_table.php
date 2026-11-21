<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('agent_events', function (Blueprint $table) {
            $table->id();
            $table->foreignId('agent_id')->constrained('agents')->cascadeOnDelete();
            $table->string('event', 30);
            $table->string('tool', 100)->nullable();
            $table->string('target', 200)->nullable();
            $table->string('department', 30)->nullable();
            $table->timestamp('ts');
            $table->timestamps();

            $table->index(['agent_id', 'ts']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('agent_events');
    }
};
