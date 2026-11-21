<?php

namespace App\Console\Commands;

use App\Models\Device;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

class OfficeDevice extends Command
{
    protected $signature = 'office:device {name? : Nama device (cth. pc-helmy)} {--revoke= : ID device untuk revoke}';

    protected $description = 'Cipta device token untuk ingest (token dipaparkan sekali sahaja)';

    public function handle(): int
    {
        if ($id = $this->option('revoke')) {
            $device = Device::find($id);
            if ($device === null) {
                $this->error("Device {$id} tak wujud.");

                return self::FAILURE;
            }
            $device->forceFill(['revoked_at' => now()])->save();
            $this->info("Device {$device->name} (ID {$device->id}) telah direvoke.");

            return self::SUCCESS;
        }

        $name = (string) ($this->argument('name') ?: gethostname() ?: 'pc');
        $token = 'eod_'.Str::random(40);

        Device::create([
            'name' => $name,
            'token_hash' => hash('sha256', $token),
        ]);

        $this->info("Device '{$name}' dicipta. Simpan token ini (tak akan dipaparkan lagi):");
        $this->line($token);

        return self::SUCCESS;
    }
}
