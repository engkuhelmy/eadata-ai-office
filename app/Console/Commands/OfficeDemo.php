<?php

namespace App\Console\Commands;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\NormalizedEvent;
use DateTimeImmutable;
use Illuminate\Console\Command;

/**
 * Simulasi 13 staff demo yang jalan berjam-jam.
 * 5 staff "team" ikut kitaran: board briefing ramai-ramai, ambil tugas di papan kanban, kerja di meja,
 * kemudian chill (sweep hantar ke chill room selepas idle 2 minit).
 * 8 staff "rotator" pusing tanpa henti: kerja -> tandas -> pantri -> chill room -> kerja, dalam semua fasa,
 * kecuali awal setiap kitaran bila semua 13 orang berkumpul di boardroom.
 * Sesi demo (session_id 'demo-*') TIDAK PERNAH ditamatkan: tiada session_end dan sweep skip mereka.
 */
class OfficeDemo extends Command
{
    protected $signature = 'office:demo
        {--hours=24 : Berapa jam demo berjalan}
        {--speed=1 : Pecutan masa (2 = dua kali ganda laju)}
        {--once : Satu kitaran sahaja}';

    protected $description = 'Demo 24 jam: 13 staff (briefing, kerja, tandas, pantri, chill room). Sesi tak ditamatkan.';

    /** Peringkat rotator: [nama, min saat, max saat, department (null = kerja di meja)]. */
    private const STAGE_WORK = 0;

    private const STAGES = [
        ['work', 70, 100, null],
        ['toilet', 25, 40, 'toilet'],
        ['pantry', 40, 60, 'pantry'],
        ['chill', 60, 90, 'playroom'],
    ];

    private float $speed = 1.0;

    /** @var array<int, array<string, mixed>> */
    private array $team = [];

    /** @var array<int, array<string, mixed>> */
    private array $rotators = [];

    /** @var array<int, array<string, mixed>> keadaan semasa setiap rotator (ikut indeks $rotators) */
    private array $rot = [];

    /** True semasa semua orang tahan di boardroom (rotator berhenti pusing). */
    private bool $rotHold = false;

    /** @var array<string, array{input:int,output:int,cache_read:int,cache_create:int}> */
    private array $usage = [];

    public function handle(): int
    {
        $this->speed = max(0.1, (float) $this->option('speed'));
        $this->team = $this->buildTeam();
        $this->rotators = $this->buildRotators();
        $this->registerTeam();
        $this->initRotators();

        $endAt = microtime(true) + ((float) $this->option('hours') * 3600) / $this->speed;
        $cycle = 0;

        $this->info('Demo mula: '.(count($this->team) + count($this->rotators)).' staff, '.$this->option('hours').' jam. Ctrl+C untuk henti.');

        do {
            $cycle++;
            $this->line(sprintf('[%s] Kitaran %d: board briefing', now()->format('H:i:s'), $cycle));
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
            ['vendor' => 'claude', 'sid' => 'demo-aiman', 'auto' => 'Claude demo1', 'label' => $claude, 'name' => 'Aiman', 'avatar' => 'default', 'steps' => [
                ['Edit', 'resources/js/components/Navbar.vue', 'frontend'],
                ['Edit', 'resources/css/app.css', 'frontend'],
                ['Edit', 'resources/views/landing.blade.php', 'frontend'],
                ['Read', 'resources/js/app.js', 'research'],
                ['Bash', 'npm run build', 'ops'],
                ['Bash', 'npx vitest run', 'qa'],
            ]],
            ['vendor' => 'claude', 'sid' => 'demo-balqis', 'auto' => 'Claude demo2', 'label' => $claude, 'name' => 'Balqis', 'avatar' => 'woman', 'steps' => [
                ['Edit', 'app/Http/Controllers/UserController.php', 'backend'],
                ['Edit', 'routes/web.php', 'backend'],
                ['Edit', 'app/Models/Invoice.php', 'backend'],
                ['Read', 'database/migrations/2026_11_01_create_invoices.php', 'research'],
                ['Bash', 'php artisan migrate', 'ops'],
                ['Bash', 'php artisan test', 'qa'],
            ]],
            ['vendor' => 'codex', 'sid' => 'demo-chandra', 'auto' => 'Codex demo', 'label' => 'Codex', 'name' => 'Chandra', 'avatar' => 'default', 'steps' => [
                ['Read', 'docs/api-spec.md', 'research'],
                ['WebSearch', 'laravel queue retry strategy', 'research'],
                ['Edit', 'app/Services/BillingService.php', 'backend'],
                ['Bash', 'rg TODO app/', 'ops'],
                ['Bash', 'pytest -q', 'qa'],
            ]],
            ['vendor' => 'hermes', 'sid' => 'demo-dewi', 'auto' => 'Hermes demo', 'label' => 'Hermes', 'name' => 'Dewi', 'avatar' => 'woman', 'steps' => [
                ['Bash', 'git push origin main', 'deploy'],
                ['Bash', 'docker compose up -d --build', 'deploy'],
                ['Bash', 'ssh eadata.my pm2 restart api', 'deploy'],
                ['Bash', 'kubectl get pods', 'deploy'],
                ['WebSearch', 'harga VPS Malaysia', 'research'],
            ]],
            ['vendor' => 'antigravity', 'sid' => 'demo-evan', 'auto' => 'Antigravity demo', 'label' => 'Antigravity', 'name' => 'Evan', 'avatar' => 'hiphop', 'steps' => [
                ['Bash', 'pytest tests/ -q', 'qa'],
                ['Edit', 'tests/test_api.py', 'qa'],
                ['Read', 'tests/fixtures/users.json', 'research'],
                ['Bash', 'npm run lint', 'ops'],
                ['Edit', 'app/Http/Middleware/Auth.php', 'backend'],
            ]],
        ];
    }

    /**
     * 8 staff rotator: meja di research/deploy/ops (Nurul/Sofea/Aina, Zack/Danish/Mika, Qila/Hakim),
     * lepas tu tandas, pantri, chill room, ulang.
     *
     * @return array<int, array<string, mixed>>
     */
    private function buildRotators(): array
    {
        return [
            ['vendor' => 'claude', 'sid' => 'demo-nurul', 'auto' => 'Claude demo6', 'label' => 'Claude Code', 'name' => 'Nurul', 'avatar' => 'woman', 'steps' => [
                ['Read', 'docs/competitor-analysis.md', 'research'],
                ['WebSearch', 'laravel 12 release notes', 'research'],
                ['Read', 'storage/app/reports/q3-metrics.csv', 'research'],
                ['Bash', 'rg "TODO|FIXME" app/', 'research'],
                ['Edit', 'docs/research-notes.md', 'research'],
            ]],
            ['vendor' => 'codex', 'sid' => 'demo-sofea', 'auto' => 'Codex demo2', 'label' => 'Codex', 'name' => 'Sofea', 'avatar' => 'woman', 'steps' => [
                ['WebSearch', 'phaser 3 tilemap performance tips', 'research'],
                ['Read', 'docs/architecture.md', 'research'],
                ['Read', 'composer.json', 'research'],
                ['Bash', 'git log --oneline -n 20', 'research'],
                ['WebSearch', 'reverb vs pusher scaling', 'research'],
            ]],
            ['vendor' => 'antigravity', 'sid' => 'demo-aina', 'auto' => 'Antigravity demo2', 'label' => 'Antigravity', 'name' => 'Aina', 'avatar' => 'woman', 'steps' => [
                ['Read', 'README.md', 'research'],
                ['WebSearch', 'best practice rate limiting api', 'research'],
                ['Read', 'config/queue.php', 'research'],
                ['Bash', 'curl -s https://api.eadata.my/health', 'research'],
                ['Edit', 'docs/api-notes.md', 'research'],
            ]],
            ['vendor' => 'claude', 'sid' => 'demo-zack', 'auto' => 'Claude demo7', 'label' => 'Claude Code', 'name' => 'Zack', 'avatar' => 'hiphop', 'steps' => [
                ['Bash', 'git push origin release/1.4', 'deploy'],
                ['Bash', 'docker compose build web', 'deploy'],
                ['Bash', 'ssh eadata.my sudo systemctl reload nginx', 'deploy'],
                ['Edit', 'docker-compose.yml', 'deploy'],
                ['Read', '.github/workflows/deploy.yml', 'deploy'],
            ]],
            ['vendor' => 'hermes', 'sid' => 'demo-danish', 'auto' => 'Hermes demo2', 'label' => 'Hermes', 'name' => 'Danish', 'avatar' => 'hiphop', 'steps' => [
                ['Bash', 'kubectl rollout status deploy/api', 'deploy'],
                ['Bash', 'rsync -az dist/ eadata.my:/var/www/app', 'deploy'],
                ['Bash', 'pm2 logs api --lines 50', 'deploy'],
                ['Read', 'deploy/k8s/api-deployment.yaml', 'deploy'],
                ['Bash', 'docker image prune -f', 'deploy'],
            ]],
            ['vendor' => 'claude', 'sid' => 'demo-mika', 'auto' => 'Claude demo8', 'label' => 'Claude Code', 'name' => 'Mika', 'avatar' => 'genz', 'steps' => [
                ['Bash', 'git push origin main', 'deploy'],
                ['Bash', 'ssh eadata.my pm2 restart web', 'deploy'],
                ['Edit', 'deploy/nginx.conf', 'deploy'],
                ['Read', 'storage/logs/laravel.log', 'deploy'],
                ['Bash', 'docker compose logs --tail=100 web', 'deploy'],
            ]],
            ['vendor' => 'antigravity', 'sid' => 'demo-qila', 'auto' => 'Antigravity demo3', 'label' => 'Antigravity', 'name' => 'Qila', 'avatar' => 'genz', 'steps' => [
                ['Bash', 'df -h', 'ops'],
                ['Bash', 'php artisan queue:failed', 'ops'],
                ['Read', 'config/logging.php', 'ops'],
                ['Edit', 'scripts/backup.sh', 'ops'],
                ['Bash', 'tail -n 100 storage/logs/laravel.log', 'ops'],
            ]],
            ['vendor' => 'codex', 'sid' => 'demo-hakim', 'auto' => 'Codex demo3', 'label' => 'Codex', 'name' => 'Hakim', 'avatar' => 'genz', 'steps' => [
                ['Bash', 'composer audit', 'ops'],
                ['Bash', 'php artisan schedule:list', 'ops'],
                ['Read', 'crontab.txt', 'ops'],
                ['Edit', '.env.example', 'ops'],
                ['Bash', 'npm outdated', 'ops'],
            ]],
        ];
    }

    /** @return array<int, array<string, mixed>> */
    private function allStaff(): array
    {
        return array_merge($this->team, $this->rotators);
    }

    /** Cipta staff dengan nama paparan + avatar supaya nampak dalam senarai Team dari awal. */
    private function registerTeam(): void
    {
        foreach ($this->allStaff() as $m) {
            Agent::updateOrCreate(
                ['vendor' => $m['vendor'], 'session_id' => $m['sid']],
                [
                    'name' => $m['auto'], 'custom_name' => $m['name'], 'avatar' => $m['avatar'], 'label' => $m['label'],
                    'pc' => 'DEMO-PC', 'project' => 'eadata-web', 'department' => 'door',
                    'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now(), 'ended_at' => null,
                ],
            );
            $this->usage[$m['sid']] = ['input' => 0, 'output' => 0, 'cache_read' => 0, 'cache_create' => 0];
        }
    }

    /** Rotator ke-i mula di peringkat (i % 4) dengan baki masa rawak supaya tak serentak. Belum hantar event. */
    private function initRotators(): void
    {
        foreach (array_keys($this->rotators) as $i) {
            $stage = $i % count(self::STAGES);
            [, $min, $max] = self::STAGES[$stage];
            $this->startStage($i, $stage, ($min + lcg_value() * ($max - $min)) / $this->speed, false);
        }
    }

    // ---- fasa ----

    /** Semua 13 orang ke boardroom (ramai-ramai) dan kekal ~70 saat. Lepas tu rotator sambung di peringkat berbeza. */
    private function standup(): void
    {
        $this->rotHold = true;
        $until = microtime(true) + 70 / $this->speed;
        $first = true;

        while (microtime(true) < $until) {
            foreach ($this->allStaff() as $m) {
                $this->emit($m, 'subagent_start', 'Task', 'Board briefing', 'boardroom');
                if ($first) {
                    usleep((int) (700000 / $this->speed)); // masuk bergilir
                }
            }
            $first = false;
            $this->nap(22);
        }

        // Lepas briefing, setiap rotator sambung di peringkat berbeza (i % 4) dengan baki masa rawak,
        // supaya tak semua serbu toilet serentak (sebelum ini semua mula dari WORK dan tamat serentak).
        $this->rotHold = false;
        foreach (array_keys($this->rotators) as $i) {
            $stage = $i % count(self::STAGES);
            [, $min, $max] = self::STAGES[$stage];
            $this->startStage($i, $stage, ($min + lcg_value() * ($max - $min)) / $this->speed, true);
        }
    }

    /** Ambil tugas di papan kanban sebelum ke meja. */
    private function takeTasks(): void
    {
        foreach ($this->team as $m) {
            $this->emit($m, 'prompt', null, null, 'kanban');
            $this->nap(1.5);
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
                $this->workStep($m, $state[$i], $now);
            }
            $this->tickRotators();
            usleep((int) (1000000 / $this->speed));
        }

        // Akhir fasa kerja: turn_done (+ token Claude bertambah). Staff kekal di meja sampai sweep hantar ke chill room.
        foreach ($this->team as $m) {
            $this->emit($m, 'turn_done', null, null, null, $this->bumpUsage($m));
        }
    }

    /** Sesiapa idle 2 minit akan dihantar sweep ke chill room. Seorang kena rate limit (mesin kopi). */
    private function chill(int $seconds): void
    {
        $coffee = $this->team[array_rand($this->team)];
        $this->emit($coffee, 'rate_limited', null, null, 'coffee');
        $this->nap($seconds);
    }

    // ---- langkah kerja (kongsi team + rotator) ----

    /**
     * Satu tick kerja: tool_end kalau dah sampai masa, atau mula langkah baru (kadang-kadang error / minta kelulusan).
     * $s: next, end, dept, step.
     */
    private function workStep(array $m, array &$s, float $now): void
    {
        if ($s['end'] !== null && $now >= $s['end']) {
            $this->emit($m, 'tool_end', $s['step'][0], $s['step'][1], $s['dept']);
            $s['end'] = null;
            $s['next'] = $now + random_int(5, 10) / $this->speed;

            return;
        }

        if ($s['end'] !== null || $now < $s['next']) {
            return;
        }

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

    // ---- rotator ----

    /** Dipanggil setiap tick (1 saat) dari semua fasa: kerja / tandas / pantri / chill room bergilir. */
    private function tickRotators(): void
    {
        if ($this->rotHold) {
            return;
        }

        $now = microtime(true);
        foreach ($this->rotators as $i => $m) {
            $r = $this->rot[$i];

            if ($now >= $r['until']) {
                if ($r['end'] !== null) {
                    $this->emit($m, 'tool_end', $r['step'][0], $r['step'][1], $r['dept']);
                }
                $this->startStage($i, ($r['stage'] + 1) % count(self::STAGES));
            } elseif ($r['stage'] === self::STAGE_WORK) {
                $this->workStep($m, $this->rot[$i], $now);
            } elseif ($now >= $r['ping']) {
                // Event baru tiap ~20s supaya last_event_at segar (tak pernah senyap 100s)
                $this->emit($m, 'idle', null, null, self::STAGES[$r['stage']][3]);
                $this->rot[$i]['ping'] = $now + 20 / $this->speed;
            }
        }
    }

    /** Masuk peringkat baru. Peringkat bukan kerja: terus hantar 'idle' dengan department peringkat tu. */
    private function startStage(int $i, int $stage, ?float $duration = null, bool $emit = true): void
    {
        $now = microtime(true);
        [, $min, $max, $dept] = self::STAGES[$stage];
        $m = $this->rotators[$i];

        $this->rot[$i] = [
            'stage' => $stage,
            'until' => $now + ($duration ?? random_int($min, $max) / $this->speed),
            'ping' => $now + 20 / $this->speed,
            'next' => $now + random_int(1, 4) / $this->speed,
            'end' => null,
            'dept' => null,
            'step' => null,
        ];

        if ($emit && $dept !== null) {
            // Habis kerja (masuk tandas): token Claude bertambah
            $this->emit($m, 'idle', null, null, $dept, $stage === 1 ? $this->bumpUsage($m) : null);
        }
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

    /** Tunggu (ikut speed), dipecah 1 saat supaya Ctrl+C responsif. Rotator berpusing setiap tick. */
    private function nap(float $seconds): void
    {
        $until = microtime(true) + $seconds / $this->speed;
        while (microtime(true) < $until) {
            usleep((int) min(1000000, max(0, ($until - microtime(true)) * 1000000)));
            $this->tickRotators();
        }
    }
}
