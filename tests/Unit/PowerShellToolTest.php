<?php

namespace Tests\Unit;

use App\Office\AdapterRegistry;
use Tests\TestCase;

class PowerShellToolTest extends TestCase
{
    public function test_powershell_test_command_goes_to_qa(): void
    {
        $payload = json_decode(file_get_contents(__DIR__.'/../fixtures/claude/pre_tool_use_powershell_test.json'), true, flags: JSON_THROW_ON_ERROR);

        $e = app(AdapterRegistry::class)->get('claude')->normalize($payload);

        $this->assertSame('PowerShell', $e->tool);
        $this->assertSame('qa', $e->department);
        $this->assertSame('php artisan test', $e->target);
    }
}
