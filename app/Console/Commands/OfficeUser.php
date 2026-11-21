<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Hash;
use Illuminate\Support\Str;

class OfficeUser extends Command
{
    protected $signature = 'office:user {email : Email user} {--role=viewer : owner atau viewer} {--name= : Nama paparan} {--password= : Kalau kosong, akan ditanya}';

    protected $description = 'Cipta atau kemas kini user office (owner/viewer)';

    public function handle(): int
    {
        $email = strtolower((string) $this->argument('email'));
        $role = (string) $this->option('role');

        if (! in_array($role, ['owner', 'viewer'], true)) {
            $this->error('Role mesti owner atau viewer.');

            return self::FAILURE;
        }

        $password = $this->option('password') ?: $this->secret('Password (min 8 aksara)');
        if (! is_string($password) || strlen($password) < 8) {
            $this->error('Password min 8 aksara.');

            return self::FAILURE;
        }

        $user = User::firstOrNew(['email' => $email]);
        $user->name = (string) ($this->option('name') ?: Str::before($email, '@'));
        $user->role = $role;
        $user->password = Hash::make($password);
        $user->save();

        $this->info("User {$email} disimpan sebagai {$role}.");

        return self::SUCCESS;
    }
}
