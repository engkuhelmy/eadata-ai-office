<?php

namespace App\Office\Demo;

use App\Models\Agent;
use Closure;

/**
 * Modul demo staff aras (bangunan 4 aras): 12 staff yang setiap seorang pusing ikut rutin peribadi.
 *
 * L3: CEO Datuk Hafiz, CFO Mei Ling, MD Rajesh, HOD Puan Rosnah (pejabat masing-masing + lawatan).
 * L2: Head of Department Encik Kamal, Marketing Farah dan Iqbal.
 * L1: Sales Amir dan Liyana, trainer Cikgu Azlan, intern Danial dan Sara.
 *
 * Setiap hentian rutin = [department, min saat, max saat, teks bubble]. Sampai di hentian: tool_start (tool = teks
 * bubble), lepas 10-18s tool_end, kemudian 'idle' setiap ~20s selagi berlegar di situ (sweep tak pernah pindahkan
 * mereka ke chill room). Habis tempoh: hentian seterusnya (berpusing).
 *
 * Pantri L1 ('pantry', had 2 orang) dikawal pintu yang disuntik ($pantryEnter / $pantryLeave, OfficeDemo kongsi
 * pintunya). Pantri penuh = hentian tu dilangkau. Slot dilepas SELEPAS event keluar pantri dihantar.
 *
 * hold() semasa briefing semua staff (OfficeDemo hantar mereka ke boardroom), resume() lepas tu: setiap staff
 * sambung di titik rawak rutinnya, bergilir (tak serentak).
 *
 * Dipacu tick() (tiap saat dari loop OfficeDemo). Masa, rawak dan emit disuntik supaya boleh diuji tanpa tidur:
 * $emit(array $member, string $event, ?string $tool, ?string $target, ?string $department).
 */
class FloorStaffModule
{
    /** Tempoh bubble tugas (saat) sebelum tool_end, dan jarak ping 'idle' semasa berlegar. */
    private const TASK_MIN = 10;

    private const TASK_MAX = 18;

    private const PING_EVERY = 20;

    /** Lengah rawak (saat) sebelum hentian pertama selepas start/resume, supaya tak semua bergerak serentak. */
    private const STAGGER_MAX = 8;

    public const PANTRY = 'pantry';

    public const PANTRY_CAPACITY = 2;

    /**
     * Staff aras. routine: [department, min s, max s, teks bubble]. Teks unik dalam setiap rutin.
     *
     * @var array<int, array<string, mixed>>
     */
    public const STAFF = [
        // ---- L3: eksekutif ----
        ['vendor' => 'claude', 'sid' => 'demo-hafiz', 'auto' => 'Claude CEO', 'label' => 'Claude Code', 'name' => 'Datuk Hafiz', 'avatar' => 'exec', 'routine' => [
            ['ceo', 60, 90, 'Semak laporan syarikat'],
            ['head_office', 25, 40, 'Bincang KPI dengan Encik Kamal'],
            ['ceo', 50, 80, 'Lulus bajet projek'],
            ['boardroom', 30, 45, 'Sediakan slaid board meeting'],
            ['ceo', 50, 80, 'Call dengan pelabur'],
            ['rooftop', 30, 50, 'Rehat sekejap di rooftop'],
        ]],
        ['vendor' => 'codex', 'sid' => 'demo-meiling', 'auto' => 'Codex CFO', 'label' => 'Codex', 'name' => 'Mei Ling', 'avatar' => 'exec_w', 'routine' => [
            ['cfo', 60, 90, 'Semak bajet Q4'],
            ['sales', 25, 40, 'Semak sasaran jualan'],
            ['cfo', 50, 80, 'Sahkan invois pembekal'],
            ['coffee', 20, 35, 'Kopi di big pantry'],
            ['cfo', 50, 80, 'Unjuran aliran tunai'],
            ['outdoor_work', 40, 60, 'Kira cukai di outdoor deck'],
        ]],
        ['vendor' => 'hermes', 'sid' => 'demo-rajesh', 'auto' => 'Hermes MD', 'label' => 'Hermes', 'name' => 'Rajesh', 'avatar' => 'exec', 'routine' => [
            ['md', 60, 90, 'Semak roadmap produk'],
            ['frontend', 20, 35, 'Walkabout IT: frontend'],
            ['backend', 20, 35, 'Walkabout IT: backend'],
            ['md', 50, 80, 'Mesyuarat dengan vendor'],
            ['outdoor_work', 40, 60, 'Kerja di outdoor deck'],
            ['gaming', 30, 45, 'Main arcade sekejap'],
        ]],
        ['vendor' => 'antigravity', 'sid' => 'demo-rosnah', 'auto' => 'Antigravity HOD', 'label' => 'Antigravity', 'name' => 'Puan Rosnah', 'avatar' => 'exec_w', 'routine' => [
            ['hod', 60, 90, 'Semak prestasi jabatan'],
            ['marketing', 25, 40, 'Semak kempen marketing'],
            ['hod', 50, 80, 'Temuduga calon baharu'],
            ['training', 25, 40, 'Pantau sesi latihan'],
            ['hod', 50, 80, 'Sediakan laporan HR'],
            ['outdoor_chill', 30, 45, 'Rehat di teres'],
        ]],
        // ---- L2: Head of Department + Marketing ----
        ['vendor' => 'claude', 'sid' => 'demo-kamal', 'auto' => 'Claude HoD', 'label' => 'Claude Code', 'name' => 'Encik Kamal', 'avatar' => 'exec', 'routine' => [
            ['head_office', 60, 90, 'Semak pelan marketing'],
            ['marketing', 25, 40, 'Brief pasukan marketing'],
            ['head_office', 40, 70, 'Luluskan bajet iklan'],
            ['qa', 20, 35, 'Semak status QA'],
            ['kanban', 20, 35, 'Kemas kini papan tugas'],
        ]],
        ['vendor' => 'codex', 'sid' => 'demo-farah', 'auto' => 'Codex marketing1', 'label' => 'Codex', 'name' => 'Farah', 'avatar' => 'woman', 'routine' => [
            ['marketing', 60, 90, 'Reka poster kempen'],
            ['kanban', 20, 30, 'Kemas kini Marketing Plan'],
            ['meeting', 35, 50, 'Pitch kempen kepada klien'],
            ['marketing', 50, 80, 'Tulis caption media sosial'],
            ['coffee', 20, 35, 'Kopi di big pantry'],
            ['outdoor_chill', 30, 45, 'Brainstorm di teres'],
        ]],
        ['vendor' => 'antigravity', 'sid' => 'demo-iqbal', 'auto' => 'Antigravity marketing2', 'label' => 'Antigravity', 'name' => 'Iqbal', 'avatar' => 'genz', 'routine' => [
            ['marketing', 60, 90, 'Edit video TikTok'],
            ['kanban', 20, 30, 'Gerak kad ke Done'],
            ['meeting', 35, 50, 'Demo kempen kepada klien'],
            ['marketing', 50, 80, 'Analisis iklan Meta'],
            ['coffee', 20, 35, 'Ambil latte'],
            ['outdoor_chill', 30, 45, 'Rehat di teres'],
        ]],
        // ---- L1: Sales + Training ----
        ['vendor' => 'claude', 'sid' => 'demo-amir', 'auto' => 'Claude sales1', 'label' => 'Claude Code', 'name' => 'Amir', 'avatar' => 'default', 'routine' => [
            ['sales', 50, 80, 'Call prospek baharu'],
            ['client', 30, 45, 'Layan pelanggan'],
            ['sales', 40, 70, 'Sediakan sebut harga'],
            ['meeting', 35, 50, 'Mesyuarat klien'],
            ['pantry', 20, 30, 'Minum di pantry'],
        ]],
        ['vendor' => 'hermes', 'sid' => 'demo-liyana', 'auto' => 'Hermes sales2', 'label' => 'Hermes', 'name' => 'Liyana', 'avatar' => 'woman', 'routine' => [
            ['sales', 50, 80, 'Follow up lead'],
            ['meeting', 35, 50, 'Bentang proposal'],
            ['sales', 40, 70, 'Kemas kini CRM'],
            ['pantry', 20, 30, 'Teh tarik di pantry'],
            ['client', 30, 45, 'Tunjuk demo produk'],
        ]],
        ['vendor' => 'claude', 'sid' => 'demo-azlan', 'auto' => 'Claude trainer', 'label' => 'Claude Code', 'name' => 'Cikgu Azlan', 'avatar' => 'default', 'routine' => [
            ['training', 80, 120, 'Ajar modul Laravel'],
            ['meeting', 30, 45, 'Sediakan bahan latihan'],
            ['training', 80, 120, 'Sesi soal jawab'],
        ]],
        ['vendor' => 'codex', 'sid' => 'demo-danial', 'auto' => 'Codex intern1', 'label' => 'Codex', 'name' => 'Intern Danial', 'avatar' => 'genz', 'routine' => [
            ['training', 70, 100, 'Latihan: buat CRUD'],
            ['toilet', 20, 30, 'Ke tandas'],
            ['training', 60, 90, 'Kuiz modul 1'],
            ['client', 25, 40, 'Ikut sales jumpa klien'],
        ]],
        ['vendor' => 'antigravity', 'sid' => 'demo-sara', 'auto' => 'Antigravity intern2', 'label' => 'Antigravity', 'name' => 'Intern Sara', 'avatar' => 'woman', 'routine' => [
            ['training', 70, 100, 'Latihan: reka UI'],
            ['client', 25, 40, 'Bantu layan pelanggan'],
            ['training', 60, 90, 'Nota kelas'],
            ['toilet', 20, 30, 'Rehat ke tandas'],
        ]],
    ];

    /** @var Closure(array, string, ?string, ?string, ?string): void */
    private Closure $emit;

    /** @var Closure(): float */
    private Closure $clock;

    /** @var Closure(int, int): int */
    private Closure $rand;

    /** @var Closure(string): bool */
    private Closure $pantryEnter;

    /** @var Closure(string): void */
    private Closure $pantryLeave;

    private float $speed;

    private bool $started = false;

    private bool $held = false;

    /** @var array<string, true> pintu pantri dalaman (bila tiada pintu disuntik) */
    private array $ownPantry = [];

    /**
     * Keadaan setiap staff (ikut indeks STAFF).
     *
     * @var array<int, array{i: int, phase: string, until: float, taskUntil: float, ping: float, pantry: bool}>
     */
    private array $state = [];

    public function __construct(
        Closure $emit,
        ?Closure $clock = null,
        ?Closure $rand = null,
        float $speed = 1.0,
        ?Closure $pantryEnter = null,
        ?Closure $pantryLeave = null,
    ) {
        $this->emit = $emit;
        $this->clock = $clock ?? fn (): float => microtime(true);
        $this->rand = $rand ?? fn (int $min, int $max): int => random_int($min, $max);
        $this->speed = max(0.1, $speed);
        $this->pantryEnter = $pantryEnter ?? function (string $sid): bool {
            if (! isset($this->ownPantry[$sid]) && count($this->ownPantry) >= self::PANTRY_CAPACITY) {
                return false;
            }
            $this->ownPantry[$sid] = true;

            return true;
        };
        $this->pantryLeave = $pantryLeave ?? function (string $sid): void {
            unset($this->ownPantry[$sid]);
        };
    }

    /** @return array<int, array<string, mixed>> */
    public static function staff(): array
    {
        return self::STAFF;
    }

    /** Daftar semua staff aras (nama + avatar + meja asal) dan jadualkan hentian pertama. Belum hantar event. */
    public function start(): void
    {
        foreach (self::STAFF as $m) {
            Agent::updateOrCreate(
                ['vendor' => $m['vendor'], 'session_id' => $m['sid']],
                [
                    'name' => $m['auto'], 'custom_name' => $m['name'], 'avatar' => $m['avatar'], 'label' => $m['label'],
                    'pc' => 'DEMO-PC', 'project' => 'eadata-web', 'department' => $m['routine'][0][0],
                    'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now(), 'ended_at' => null, 'current_task' => null,
                ],
            );
        }

        $this->started = true;
        $this->held = false;
        $this->schedule(($this->clock)());
    }

    /** Tahan semua (briefing). Slot pantri dilepas; event boardroom dihantar oleh pemanggil. */
    public function hold(): void
    {
        $this->held = true;
        $this->releasePantry();
    }

    /** Sambung selepas briefing: setiap staff mula semula di titik rawak rutinnya, bergilir. */
    public function resume(): void
    {
        $this->held = false;
        if ($this->started) {
            $this->schedule(($this->clock)());
        }
    }

    public function finish(): void
    {
        $this->releasePantry();
        $this->started = false;
    }

    public function isHeld(): bool
    {
        return $this->held;
    }

    public function tick(): void
    {
        if (! $this->started || $this->held) {
            return;
        }

        $now = ($this->clock)();

        foreach (array_keys(self::STAFF) as $k) {
            $s = $this->state[$k];

            if ($s['phase'] === 'wait') {
                if ($now >= $s['until']) {
                    $this->enter($k, $s['i'], $now, true);
                }

                continue;
            }

            if ($now >= $s['until']) {
                $this->next($k, $now);
            } elseif ($s['phase'] === 'task' && $now >= $s['taskUntil']) {
                [$dept, , , $text] = $this->stop($k, $s['i']);
                ($this->emit)(self::STAFF[$k], 'tool_end', $text, null, $dept);
                $this->state[$k]['phase'] = 'linger';
                $this->state[$k]['ping'] = $now + self::PING_EVERY / $this->speed;
            } elseif ($s['phase'] === 'linger' && $now >= $s['ping']) {
                // Jaga last_event_at segar supaya sweep tak hantar ke chill room
                ($this->emit)(self::STAFF[$k], 'idle', null, null, $this->stop($k, $s['i'])[0]);
                $this->state[$k]['ping'] = $now + self::PING_EVERY / $this->speed;
            }
        }
    }

    // ---- dalaman ----

    private function schedule(float $now): void
    {
        foreach (self::STAFF as $k => $m) {
            $this->state[$k] = [
                'i' => ($this->rand)(0, count($m['routine']) - 1),
                'phase' => 'wait',
                'until' => $now + ($this->rand)(0, self::STAGGER_MAX) / $this->speed,
                'taskUntil' => 0.0,
                'ping' => 0.0,
                'pantry' => false,
            ];
        }
    }

    /** Habis hentian sekarang: tool_end (kalau tugas masih terbuka), masuk hentian seterusnya, baru lepas slot pantri. */
    private function next(int $k, float $now): void
    {
        $s = $this->state[$k];
        [$dept, , , $text] = $this->stop($k, $s['i']);

        if ($s['phase'] === 'task') {
            ($this->emit)(self::STAFF[$k], 'tool_end', $text, null, $dept);
        }

        $this->enter($k, ($s['i'] + 1) % count(self::STAFF[$k]['routine']), $now, false);

        if ($s['pantry'] && ! $this->state[$k]['pantry']) {
            ($this->pantryLeave)(self::STAFF[$k]['sid']); // event keluar pantri dah dihantar
        }
    }

    /** Masuk hentian $i (pantri penuh = langkau ke hentian lain). $partial: tempoh dipendekkan (mula di tengah hentian). */
    private function enter(int $k, int $i, float $now, bool $partial): void
    {
        $m = self::STAFF[$k];
        $n = count($m['routine']);
        $wasInPantry = $this->state[$k]['pantry'];

        for ($guard = 0; $guard < $n; $guard++) {
            if ($m['routine'][$i][0] !== self::PANTRY) {
                break;
            }
            if ($wasInPantry || ($this->pantryEnter)($m['sid'])) {
                break;
            }
            $i = ($i + 1) % $n;
        }

        [$dept, $min, $max, $text] = $m['routine'][$i];
        $duration = ($this->rand)($min, $max) / $this->speed;
        if ($partial) {
            $duration *= ($this->rand)(40, 100) / 100;
        }
        $task = ($this->rand)(self::TASK_MIN, self::TASK_MAX) / $this->speed;

        $this->state[$k] = [
            'i' => $i,
            'phase' => 'task',
            'until' => $now + $duration,
            'taskUntil' => $now + min($task, $duration),
            'ping' => 0.0,
            'pantry' => $dept === self::PANTRY,
        ];

        ($this->emit)($m, 'tool_start', $text, null, $dept);
    }

    /** @return array{0: string, 1: int, 2: int, 3: string} */
    private function stop(int $k, int $i): array
    {
        return self::STAFF[$k]['routine'][$i];
    }

    private function releasePantry(): void
    {
        foreach ($this->state as $k => $s) {
            if ($s['pantry']) {
                ($this->pantryLeave)(self::STAFF[$k]['sid']);
                $this->state[$k]['pantry'] = false;
            }
        }
    }
}
