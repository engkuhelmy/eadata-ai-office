<?php

namespace App\Console\Commands;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\Demo\FloorStaffModule;
use App\Office\Demo\ReceptionModule;
use App\Office\NormalizedEvent;
use DateTimeImmutable;
use Illuminate\Console\Command;

/**
 * Simulasi staff demo dalam bangunan 4 aras (docs/multifloor-spec.md) yang jalan berjam-jam:
 * 13 staff IT (L2) + 12 staff aras (L1-L3) + penyambut tetamu AI "Reni" (L1) = 26.
 * 5 staff "team" ikut kitaran: board briefing ramai-ramai, ambil tugas di papan kanban, kerja di meja,
 * kemudian chill (sweep hantar ke chill room selepas idle 2 minit).
 * 8 staff "rotator" pusing tanpa henti: kerja -> tandas L2 (toilet_2) -> pantri -> chill (playroom / gaming /
 * outdoor_chill / rooftop, rawak setiap kali) -> kerja, dalam semua fasa, kecuali masa briefing.
 * Modul staff aras (App\Office\Demo\FloorStaffModule, matikan dengan --no-floors): CEO/CFO/MD/HOD di L3, Head of
 * Department + Marketing di L2, Sales + Training di L1, setiap seorang pusing ikut rutin peribadi.
 * Briefing (awal setiap kitaran): team + rotator + staff aras berkumpul di boardroom (Big Meeting Room, L2).
 * Modul reception (App\Office\Demo\ReceptionModule, matikan dengan --no-reception): Reni duduk di kaunter reception,
 * penghantar Grab / ShopeeFood / J&T / DHL tekan loceng pintu, masuk ke kaunter sahaja, serah barang, lalu keluar
 * (sesi mereka ditamatkan dan dipadam ~25s kemudian). Lepas tiap penghantaran Reni pusing seluruh bangunan.
 * Pantri L1 ('pantry') had 2 orang serentak: semua modul guna pintu pantri yang sama.
 * Sesi staff demo (session_id 'demo-*') TIDAK PERNAH ditamatkan: tiada session_end dan sweep skip mereka.
 * Pengecualian: penghantar ('demo-visit-*') tamat sendiri selepas serahan.
 */
class OfficeDemo extends Command
{
    protected $signature = 'office:demo
        {--hours=24 : Berapa jam demo berjalan}
        {--speed=1 : Pecutan masa (2 = dua kali ganda laju)}
        {--once : Satu kitaran sahaja}
        {--no-reception : Matikan modul reception (penyambut tetamu + penghantar)}
        {--no-floors : Matikan modul staff aras (eksekutif L3, marketing L2, sales + training L1)}';

    protected $description = 'Demo 24 jam, bangunan 4 aras: 25 staff + penyambut tetamu (briefing, kerja, tandas, pantri, chill, rutin eksekutif, penghantaran). Sesi staff tak ditamatkan.';

    /** Peringkat rotator: [nama, min saat, max saat, department (null = kerja di meja)]. */
    private const STAGE_WORK = 0;

    private const STAGE_TOILET = 1;

    private const STAGE_PANTRY = 2;

    private const STAGE_CHILL = 3;

    private const STAGES = [
        ['work', 70, 100, null],
        ['toilet', 25, 40, 'toilet_2'], // rotator kerja di L2: guna tandas L2
        ['pantry', 25, 40, 'pantry'],
        ['chill', 60, 90, 'playroom'], // bilik sebenar dipilih rawak dari CHILL_ROOMS setiap kali
    ];

    /** Tempat chill rotator (dipilih rawak setiap lawatan). */
    public const CHILL_ROOMS = ['playroom', 'gaming', 'outdoor_chill', 'rooftop'];

    /** Had keras: paling ramai 2 orang dalam pantri serentak. */
    public const PANTRY_CAPACITY = 2;

    /** Staff team: masa minum (saat dalam fasa kerja) dan tempoh duduk di pantri. */
    private const DRINK_FROM = 20;

    private const DRINK_SPAN = 130; // 20..150 s

    private float $speed = 1.0;

    /** @var array<string, true> session id yang pegang slot pantri sekarang */
    private array $pantry = [];

    /** @var array<string, true> staff team yang dah sampai masa minum tapi pantri penuh (dapat keutamaan) */
    private array $pantryWaiting = [];

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

    private ?ReceptionModule $reception = null;

    private ?FloorStaffModule $floors = null;

    public function handle(): int
    {
        $this->speed = max(0.1, (float) $this->option('speed'));
        $this->pantryClear(); // instance command boleh dipakai semula (test)
        $this->team = $this->buildTeam();
        $this->rotators = $this->buildRotators();
        $this->registerTeam();
        $this->initRotators();

        $emit = fn (array $m, string $event, ?string $tool, ?string $target, ?string $department) => $this->emit($m, $event, $tool, $target, $department);
        $enter = fn (string $sid): bool => $this->pantryTryEnter($sid);
        $leave = fn (string $sid) => $this->pantryLeave($sid);

        $this->reception = null; // jangan bawa modul lama
        if (! $this->option('no-reception')) {
            $this->reception = new ReceptionModule($emit, speed: $this->speed, pantryEnter: $enter, pantryLeave: $leave);
            $this->reception->start();
        }

        $this->floors = null;
        if (! $this->option('no-floors')) {
            // Belum hantar event: briefing pertama terus tahan mereka, resume() lepas briefing
            $this->floors = new FloorStaffModule($emit, speed: $this->speed, pantryEnter: $enter, pantryLeave: $leave);
            $this->floors->start();
        }

        $endAt = microtime(true) + ((float) $this->option('hours') * 3600) / $this->speed;
        $cycle = 0;

        $total = count($this->briefingStaff()) + ($this->reception ? 1 : 0);
        $this->info('Demo mula: '.$total.' staff, '.$this->option('hours').' jam. Ctrl+C untuk henti.');

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

        $this->reception?->finish();
        $this->floors?->finish();
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
     * lepas tu tandas L2, pantri, chill (playroom / gaming / outdoor_chill / rooftop), ulang.
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

    /** Semua yang hadir briefing: team + rotator + staff aras (kalau modul hidup). Reni kekal di kaunter. */
    private function briefingStaff(): array
    {
        return array_merge($this->allStaff(), $this->floors ? FloorStaffModule::staff() : []);
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
            $this->resumeStage($i, false);
        }
    }

    /**
     * Rotator ke-i sambung di peringkat (i % 4) dengan baki masa rawak.
     * Kalau peringkat tu pantri dan slot penuh, jatuh ke tandas dulu (tak langgar had pantri).
     */
    private function resumeStage(int $i, bool $emit): void
    {
        $stage = $i % count(self::STAGES);
        if ($stage === self::STAGE_PANTRY && ! $this->pantryTryEnter($this->rotators[$i]['sid'])) {
            $stage = self::STAGE_TOILET;
        }
        [, $min, $max] = self::STAGES[$stage];
        $this->startStage($i, $stage, ($min + lcg_value() * ($max - $min)) / $this->speed, $emit);
    }

    // ---- pintu pantri (had 2 orang) ----

    /**
     * Cuba ambil slot pantri. Staff team ($priority) dapat keutamaan: kalau gagal dia masuk senarai tunggu,
     * dan rotator hanya boleh masuk kalau slot kosong lebih banyak daripada yang tengah tunggu.
     */
    public function pantryTryEnter(string $sid, bool $priority = false): bool
    {
        if (isset($this->pantry[$sid])) {
            return true;
        }

        $free = self::PANTRY_CAPACITY - count($this->pantry);
        $ok = $priority ? $free > 0 : $free - count($this->pantryWaiting) > 0;

        if ($ok) {
            $this->pantry[$sid] = true;
            unset($this->pantryWaiting[$sid]);

            return true;
        }

        if ($priority) {
            $this->pantryWaiting[$sid] = true;
        }

        return false;
    }

    /** Lepaskan slot. Panggil SELEPAS event keluar pantri dihantar (supaya bilangan dalam pantri tak pernah lebih 2). */
    public function pantryLeave(string $sid): void
    {
        unset($this->pantry[$sid], $this->pantryWaiting[$sid]);
    }

    public function pantryClear(): void
    {
        $this->pantry = [];
        $this->pantryWaiting = [];
    }

    public function pantryCount(): int
    {
        return count($this->pantry);
    }

    // ---- fasa ----

    /**
     * Semua staff (team + rotator + staff aras) ke boardroom (Big Meeting Room L2) dan kekal ~70 saat.
     * Lepas tu rotator sambung di peringkat berbeza dan staff aras sambung rutin di titik rawak.
     */
    private function standup(): void
    {
        $this->rotHold = true;
        $this->floors?->hold();
        // Semua ke boardroom: lepas slot pantri mereka (Reni, kalau tengah di pantri, kekal pegang slotnya)
        $briefing = $this->briefingStaff();
        foreach ($briefing as $m) {
            $this->pantryLeave($m['sid']);
        }
        $this->pantryWaiting = [];
        $until = microtime(true) + 70 / $this->speed;
        $first = true;

        while (microtime(true) < $until) {
            foreach ($briefing as $m) {
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
            $this->resumeStage($i, true);
        }
        $this->floors?->resume();
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

        // Setiap staff team minum sekali dalam fasa kerja (20-150s), bergilir (tetingkap masing-masing) supaya tak serbu pantri.
        $count = max(1, count($this->team));
        $width = intdiv(self::DRINK_SPAN, $count);
        $order = array_keys($this->team);
        shuffle($order);

        foreach ($this->team as $i => $m) {
            $slot = (int) array_search($i, $order, true);
            $drinkAt = self::DRINK_FROM + $slot * $width + random_int(0, max(0, $width - 6));
            $state[$i] = [
                'next' => $now + random_int(1, 6) / $this->speed, 'end' => null, 'dept' => null, 'step' => null,
                'drinkAt' => $now + $drinkAt / $this->speed, 'drunk' => false,
                'inPantry' => false, 'pantryUntil' => 0.0, 'pantryPing' => 0.0,
            ];
        }

        while (microtime(true) < $until) {
            $now = microtime(true);
            foreach ($this->team as $i => $m) {
                $this->teamStep($m, $state[$i], $now);
            }
            $this->tickRotators();
            $this->reception?->tick();
            $this->floors?->tick();
            usleep((int) (1000000 / $this->speed));
        }

        // Akhir fasa kerja: turn_done (+ token Claude bertambah). Staff kekal di meja sampai sweep hantar ke chill room.
        // turn_done (department null) pun tanda keluar pantri, lepas tu baru slot dilepas.
        foreach ($this->team as $i => $m) {
            $this->emit($m, 'turn_done', null, null, null, $this->bumpUsage($m));
            $this->pantryLeave($m['sid']);
        }
        $this->pantryWaiting = [];
    }

    /** Satu tick staff team: minum di pantri (kalau slot ada) atau langkah kerja biasa. */
    private function teamStep(array $m, array &$s, float $now): void
    {
        if ($s['inPantry']) {
            if ($now >= $s['pantryUntil']) {
                // Habis minum: terus mula tool (event keluar pantri), BARU lepas slot
                $this->startTool($m, $s, $now);
                $s['inPantry'] = false;
                $this->pantryLeave($m['sid']);

                return;
            }
            if ($now >= $s['pantryPing']) {
                $this->emit($m, 'idle', null, null, 'pantry'); // jaga last_event_at segar
                $s['pantryPing'] = $now + 20 / $this->speed;
            }

            return;
        }

        if (! $s['drunk'] && $s['end'] === null && $now >= $s['drinkAt']) {
            if ($this->pantryTryEnter($m['sid'], true)) {
                $this->emit($m, 'idle', null, null, 'pantry');
                $s['drunk'] = true;
                $s['inPantry'] = true;
                $s['pantryUntil'] = $now + random_int(25, 35) / $this->speed;
                $s['pantryPing'] = $now + 20 / $this->speed;

                return;
            }
            // Penuh: sambung kerja, cuba lagi beberapa saat lagi
            $s['drinkAt'] = $now + random_int(2, 4) / $this->speed;
        }

        $this->workStep($m, $s, $now);
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
            $this->startTool($m, $s, $now);
        }
    }

    /** Mula satu tool (hantar staff ke meja department langkah tu). */
    private function startTool(array $m, array &$s, float $now): void
    {
        $step = $m['steps'][array_rand($m['steps'])];
        $s['step'] = $step;
        $s['dept'] = $step[2];
        $this->emit($m, 'tool_start', $step[0], $step[1], $step[2]);
        $s['end'] = $now + random_int(2, 4) / $this->speed;
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
                $next = ($r['stage'] + 1) % count(self::STAGES);

                if ($next === self::STAGE_PANTRY && ! $this->pantryTryEnter($m['sid'])) {
                    // Pantri penuh: kekal di peringkat sekarang 6-10s lagi, tetap hantar event supaya last_event_at segar
                    $this->rot[$i]['until'] = $now + random_int(6, 10) / $this->speed;
                    $this->rot[$i]['ping'] = $now + 20 / $this->speed;
                    $this->emit($m, 'idle', null, null, $r['room']);

                    continue;
                }

                $this->startStage($i, $next);
                if ($r['stage'] === self::STAGE_PANTRY) {
                    $this->pantryLeave($m['sid']); // event keluar pantri dah dihantar
                }
            } elseif ($r['stage'] === self::STAGE_WORK) {
                $this->workStep($m, $this->rot[$i], $now);
            } elseif ($now >= $r['ping']) {
                // Event baru tiap ~20s supaya last_event_at segar (tak pernah senyap 100s)
                $this->emit($m, 'idle', null, null, $r['room']);
                $this->rot[$i]['ping'] = $now + 20 / $this->speed;
            }
        }
    }

    /** Masuk peringkat baru. Peringkat bukan kerja: terus hantar 'idle' dengan department peringkat tu. */
    private function startStage(int $i, int $stage, ?float $duration = null, bool $emit = true): void
    {
        $now = microtime(true);
        [, $min, $max, $dept] = self::STAGES[$stage];
        if ($stage === self::STAGE_CHILL) {
            $dept = self::CHILL_ROOMS[array_rand(self::CHILL_ROOMS)]; // bilik chill rawak setiap lawatan
        }
        $m = $this->rotators[$i];

        $this->rot[$i] = [
            'stage' => $stage,
            'room' => $dept,
            'until' => $now + ($duration ?? random_int($min, $max) / $this->speed),
            'ping' => $now + 20 / $this->speed,
            'next' => $now + random_int(1, 4) / $this->speed,
            'end' => null,
            'dept' => null,
            'step' => null,
        ];

        if ($emit && $dept !== null) {
            // Habis kerja (masuk tandas): token Claude bertambah
            $this->emit($m, 'idle', null, null, $dept, $stage === self::STAGE_TOILET ? $this->bumpUsage($m) : null);
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
            project: $m['project'] ?? 'eadata-web',
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
            $this->reception?->tick();
            $this->floors?->tick();
        }
    }
}
