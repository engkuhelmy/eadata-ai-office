<?php

namespace App\Console\Commands;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\NormalizedEvent;
use DateTimeImmutable;
use Illuminate\Console\Command;

/**
 * Simulasi kerja 5 staff demo (Claude x2, Codex, Hermes, Antigravity) yang jalan berjam-jam.
 * Setiap kitaran: mesyuarat ramai-ramai, ambil tugas di papan kanban, kerja di meja masing-masing,
 * kemudian chill (sweep hantar ke bilik bermain selepas idle 2 minit).
 * Sesi demo (session_id 'demo-*') TIDAK PERNAH ditamatkan: tiada session_end dan sweep skip mereka.
 */
class OfficeDemo extends Command
{
    protected $signature = 'office:demo
        {--hours=24 : Berapa jam demo berjalan}
        {--speed=1 : Pecutan masa (2 = dua kali ganda laju)}
        {--once : Satu kitaran sahaja}';

    protected $description = 'Demo 24 jam: 5 staff mesyuarat, kerja di meja, chill. Sesi tak ditamatkan.';

    private float $speed = 1.0;

    /** @var array<int, array<string, mixed>> */
    private array $team = [];

    /** @var array<string, array{input:int,output:int,cache_read:int,cache_create:int}> */
    private array $usage = [];

    public function handle(): int
    {
        $this->speed = max(0.1, (float) $this->option('speed'));
        $this->team = $this->buildTeam();
        $this->registerTeam();

        $endAt = microtime(true) + ((float) $this->option('hours') * 3600) / $this->speed;
        $cycle = 0;

        $this->info('Demo mula: '.count($this->team).' staff, '.$this->option('hours').' jam. Ctrl+C untuk henti.');

        do {
            $cycle++;
            $this->line(sprintf('[%s] Kitaran %d: mesyuarat', now()->format('H:i:s'), $cycle));
            $this->standup();
            $this->line(sprintf('[%s] Kitaran %d: ambil tugas dan kerja', now()->format('H:i:s'), $cycle));
            $this->takeTasks();
            $this->work(180);
            $this->line(sprintf('[%s] Kitaran %d: chill', now()->format('H:i:s'), $cycle));
            $this->chill(150);
            gc_collect_cycles();
        } while (! $this->option('once') && microtime(true) < $endAt);

        $this->info('Demo selesai. Sesi staff dibiar hidup (tiada session_end).');

        return self::SUCCESS;
    }

    /** @return array<int, array<string, mixed>> */
    private function buildTeam(): array
    {
        $claude = 'Claude Code';

        return [
            ['vendor' => 'claude', 'sid' => 'demo-aiman', 'auto' => 'Claude demo1', 'label' => $claude, 'name' => 'Aiman', 'steps' => [
                ['Edit', 'resources/js/components/Navbar.vue', 'frontend'],
                ['Edit', 'resources/css/app.css', 'frontend'],
                ['Edit', 'resources/views/landing.blade.php', 'frontend'],
                ['Read', 'resources/js/app.js', 'research'],
                ['Bash', 'npm run build', 'ops'],
                ['Bash', 'npx vitest run', 'qa'],
            ]],
            ['vendor' => 'claude', 'sid' => 'demo-balqis', 'auto' => 'Claude demo2', 'label' => $claude, 'name' => 'Balqis', 'steps' => [
                ['Edit', 'app/Http/Controllers/UserController.php', 'backend'],
                ['Edit', 'routes/web.php', 'backend'],
                ['Edit', 'app/Models/Invoice.php', 'backend'],
                ['Read', 'database/migrations/2026_11_01_create_invoices.php', 'research'],
                ['Bash', 'php artisan migrate', 'ops'],
                ['Bash', 'php artisan test', 'qa'],
            ]],
            ['vendor' => 'codex', 'sid' => 'demo-chandra', 'auto' => 'Codex demo', 'label' => 'Codex', 'name' => 'Chandra', 'steps' => [
                ['Read', 'docs/api-spec.md', 'research'],
                ['WebSearch', 'laravel queue retry strategy', 'research'],
                ['Edit', 'app/Services/BillingService.php', 'backend'],
                ['Bash', 'rg TODO app/', 'ops'],
                ['Bash', 'pytest -q', 'qa'],
            ]],
            ['vendor' => 'hermes', 'sid' => 'demo-dewi', 'auto' => 'Hermes demo', 'label' => 'Hermes', 'name' => 'Dewi', 'steps' => [
                ['Bash', 'git push origin main', 'deploy'],
                ['Bash', 'docker compose up -d --build', 'deploy'],
                ['Bash', 'ssh eadata.my pm2 restart api', 'deploy'],
                ['Bash', 'kubectl get pods', 'deploy'],
                ['WebSearch', 'harga VPS Malaysia', 'research'],
            ]],
            ['vendor' => 'antigravity', 'sid' => 'demo-evan', 'auto' => 'Antigravity demo', 'label' => 'Antigravity', 'name' => 'Evan', 'steps' => [
                ['Bash', 'pytest tests/ -q', 'qa'],
                ['Edit', 'tests/test_api.py', 'qa'],
                ['Read', 'tests/fixtures/users.json', 'research'],
                ['Bash', 'npm run lint', 'ops'],
                ['Edit', 'app/Http/Middleware/Auth.php', 'backend'],
            ]],
        ];
    }

    /** Cipta staff dengan nama paparan mesra supaya nampak dalam senarai Team dari awal. */
    private function registerTeam(): void
    {
        foreach ($this->team as $m) {
            Agent::updateOrCreate(
                ['vendor' => $m['vendor'], 'session_id' => $m['sid']],
                [
                    'name' => $m['auto'], 'custom_name' => $m['name'], 'label' => $m['label'],
                    'pc' => 'DEMO-PC', 'project' => 'eadata-web', 'department' => 'door',
                    'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now(), 'ended_at' => null,
                ],
            );
            $this->usage[$m['sid']] = ['input' => 0, 'output' => 0, 'cache_read' => 0, 'cache_create' => 0];
        }
    }

    // ---- fasa ----

    /** Semua orang ke bilik mesyuarat (ramai-ramai) dan kekal ~70 saat. */
    private function standup(): void
    {
        $until = microtime(true) + 70 / $this->speed;
        $first = true;

        while (microtime(true) < $until) {
            foreach ($this->team as $m) {
                $this->emit($m, 'subagent_start', 'Task', 'Daily standup', 'meeting');
                if ($first) {
                    usleep((int) (700000 / $this->speed)); // masuk bergilir
                }
            }
            $first = false;
            $this->nap(22);
        }
    }

    /** Ambil tugas di papan kanban sebelum ke meja. */
    private function takeTasks(): void
    {
        foreach ($this->team as $m) {
            $this->emit($m, 'prompt', null, null, 'kanban');
            usleep((int) (1500000 / $this->speed));
        }
        $this->nap(12);
    }

    /** Setiap staff buat langkah kerja sendiri: tool_start, lepas 2-4s tool_end, jeda 5-10s. */
    private function work(int $seconds): void
    {
        $now = microtime(true);
        $until = $now + $seconds / $this->speed;
        $state = [];
        foreach ($this->team as $i => $m) {
            $state[$i] = ['next' => $now + random_int(1, 6) / $this->speed, 'end' => null, 'dept' => null, 'step' => null];
        }

        while (microtime(true) < $until) {
            $now = microtime(true);
            foreach ($this->team as $i => $m) {
                $s = &$state[$i];

                if ($s['end'] !== null && $now >= $s['end']) {
                    $this->emit($m, 'tool_end', $s['step'][0], $s['step'][1], $s['dept']);
                    $s['end'] = null;
                    $s['next'] = $now + random_int(5, 10) / $this->speed;
                } elseif ($s['end'] === null && $now >= $s['next']) {
                    $roll = random_int(1, 100);

                    if ($roll <= 3) {
                        $this->emit($m, 'needs_approval', null, null, 'approval');
                        $s['next'] = $now + random_int(8, 12) / $this->speed;
                    } elseif ($roll <= 7) {
                        $step = $m['steps'][array_rand($m['steps'])];
                        $this->emit($m, 'tool_error', $step[0], $step[1], null);
                        $s['next'] = $now + random_int(5, 8) / $this->speed;
                    } else {
                        $step = $m['steps'][array_rand($m['steps'])];
                        $s['step'] = $step;
                        $s['dept'] = $step[2];
                        $this->emit($m, 'tool_start', $step[0], $step[1], $step[2]);
                        $s['end'] = $now + random_int(2, 4) / $this->speed;
                    }
                }
                unset($s);
            }
            usleep((int) (1000000 / $this->speed));
        }

        // Akhir fasa kerja: turn_done (+ token Claude bertambah). Staff kekal di meja sampai sweep hantar ke playroom.
        foreach ($this->team as $m) {
            $this->emit($m, 'turn_done', null, null, null, $this->bumpUsage($m));
        }
    }

    /** Sesiapa idle 2 minit akan dihantar sweep ke bilik bermain. Seorang kena rate limit (mesin kopi). */
    private function chill(int $seconds): void
    {
        $coffee = $this->team[array_rand($this->team)];
        $this->emit($coffee, 'rate_limited', null, null, 'coffee');
        $this->nap($seconds);
    }

    // ---- bantuan ----

    /** @return array{input:int,output:int,cache_read:int,cache_create:int}|null */
    private function bumpUsage(array $m): ?array
    {
        if ($m['vendor'] !== 'claude') {
            return null;
        }

        $u = &$this->usage[$m['sid']];
        $u['input'] += random_int(8000, 22000);
        $u['output'] += random_int(1500, 6000);
        $u['cache_read'] += random_int(60000, 160000);
        $u['cache_create'] += random_int(4000, 15000);

        return $u;
    }

    private function emit(array $m, string $event, ?string $tool, ?string $target, ?string $department, ?array $usage = null): void
    {
        ProcessAgentEvent::dispatch(new NormalizedEvent(
            vendor: $m['vendor'],
            agentKey: $m['sid'],
            name: $m['auto'],
            label: $m['label'],
            pc: 'DEMO-PC',
            project: 'eadata-web',
            event: $event,
            tool: $tool,
            target: $target,
            department: $department,
            ts: new DateTimeImmutable('now'),
            usage: $usage,
        ));
    }

    /** Tunggu (ikut speed), dipecah 1 saat supaya Ctrl+C responsif. */
    private function nap(float $seconds): void
    {
        $until = microtime(true) + $seconds / $this->speed;
        while (microtime(true) < $until) {
            usleep((int) min(1000000, max(0, ($until - microtime(true)) * 1000000)));
        }
    }
}
