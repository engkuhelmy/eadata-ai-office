<?php

namespace App\Office\Demo;

use App\Models\Agent;
use App\Models\AgentEvent;
use Closure;

/**
 * Modul demo reception: penyambut tetamu AI ("Reni") dan penghantar (Grab, ShopeeFood, J&T, DHL).
 *
 * Penghantar: muncul di pintu (session_start, department 'door'), masuk ke kaunter (department 'reception')
 * dan HANYA ke kaunter, serah barang, lepas tu session_end (keluar ikut pintu). Barisnya dipadam ~25s kemudian
 * supaya senarai Team/Tamat 24 jam tak penuh. Paling ramai SATU penghantar pada satu masa.
 * Penyambut: tinggal di 'frontdesk', terima pakej, lepas penghantar pergi dia buat pusingan 3-4 hentian
 * (hentian pertama = meja penerima) menghantar arahan, kemudian pulang ke 'frontdesk'.
 *
 * Dipacu tick() (dipanggil tiap saat dari loop OfficeDemo). Masa, rawak dan emit disuntik supaya boleh diuji
 * tanpa tidur: $emit(array $member, string $event, ?string $tool, ?string $target, ?string $department).
 */
class ReceptionModule
{
    public const SID = 'demo-reception';

    public const PREFIX = 'demo-visit-';

    private const RECEPTIONIST = [
        'vendor' => 'generic', 'sid' => self::SID, 'auto' => 'Reception AI', 'label' => 'Reception AI',
        'name' => 'Reni', 'avatar' => 'recep',
    ];

    /** brand => [avatar, label, kata kerja bubble, nama penghantar]. */
    public const BRANDS = [
        'grab' => ['avatar' => 'grab', 'label' => 'Grab Food', 'short' => 'Grab', 'verb' => 'Hantar makanan', 'names' => ['Adam', 'Hafiz', 'Lim']],
        'shopee' => ['avatar' => 'shopee', 'label' => 'ShopeeFood', 'short' => 'ShopeeFood', 'verb' => 'Hantar makanan', 'names' => ['Siti', 'Amin', 'Wei']],
        'jnt' => ['avatar' => 'jnt', 'label' => 'J&T Express', 'short' => 'J&T', 'verb' => 'Hantar parcel', 'names' => ['Kumar', 'Farid', 'Tan']],
        'dhl' => ['avatar' => 'dhl', 'label' => 'DHL Express', 'short' => 'DHL', 'verb' => 'Hantar parcel', 'names' => ['Ravi', 'Zul', 'Chong']],
    ];

    /** Meja biasa setiap staff demo (penerima pakej / arahan). */
    public const RECIPIENTS = [
        'Aiman' => 'frontend', 'Balqis' => 'backend', 'Chandra' => 'research', 'Dewi' => 'deploy', 'Evan' => 'qa',
        'Nurul' => 'research', 'Sofea' => 'research', 'Aina' => 'research', 'Zack' => 'deploy',
        'Danish' => 'deploy', 'Mika' => 'deploy', 'Qila' => 'ops', 'Hakim' => 'ops',
    ];

    /** Semua tempat yang Reni lawat bergilir-gilir. */
    public const PLACES = [
        'kanban' => 'Marketing Plan', 'frontend' => 'Coding (frontend)', 'backend' => 'Coding (backend)', 'qa' => 'Debugging',
        'research' => 'Design Draft', 'deploy' => 'Support Call', 'ops' => 'Onboarding', 'boardroom' => 'Board Room',
        'pantry' => 'Pantry', 'playroom' => 'Chill Room',
    ];

    private const IDLE_ROUND_AFTER = 180;

    private const PING_EVERY = 20;

    private const CLEANUP_AFTER = 25;

    /** @var Closure(array, string, ?string, ?string, ?string): void */
    private Closure $emit;

    /** @var Closure(): float */
    private Closure $clock;

    /** @var Closure(int, int): int */
    private Closure $rand;

    private float $speed;

    private bool $started = false;

    private int $seq = 0;

    private int $brandCursor = 0;

    private int $placeCursor = 0;

    private float $nextArrivalAt = 0.0;

    private float $lastActivityAt = 0.0;

    private float $pingAt = 0.0;

    /** @var array<string, mixed>|null */
    private ?array $visitor = null;

    /** @var array{stops: array<int, array{dept: string, text: string}>, i: int, open: bool, until: float}|null */
    private ?array $round = null;

    public function __construct(Closure $emit, ?Closure $clock = null, ?Closure $rand = null, float $speed = 1.0)
    {
        $this->emit = $emit;
        $this->clock = $clock ?? fn (): float => microtime(true);
        $this->rand = $rand ?? fn (int $min, int $max): int => random_int($min, $max);
        $this->speed = max(0.1, $speed);
    }

    public static function receptionist(): array
    {
        return self::RECEPTIONIST;
    }

    /** Daftar penyambut tetamu, buang penghantar tertinggal dari larian lepas, jadualkan penghantar pertama. */
    public function start(): void
    {
        $now = ($this->clock)();
        $this->purgeVisitors();

        $m = self::RECEPTIONIST;
        Agent::updateOrCreate(
            ['vendor' => $m['vendor'], 'session_id' => $m['sid']],
            [
                'name' => $m['auto'], 'custom_name' => $m['name'], 'avatar' => $m['avatar'], 'label' => $m['label'],
                'pc' => 'DEMO-PC', 'project' => 'eadata-web', 'department' => 'frontdesk',
                'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now(), 'ended_at' => null, 'current_task' => null,
            ],
        );

        $this->started = true;
        $this->nextArrivalAt = $now + $this->span(15, 20);
        $this->lastActivityAt = $now;
        $this->home($now);
    }

    /** Penghantar yang tengah berlalu dipadam (demo tamat). Penyambut dibiar hidup. */
    public function finish(): void
    {
        $this->purgeVisitors();
        $this->visitor = null;
        if ($this->round !== null) {
            $this->round = null;
            $this->home(($this->clock)());
        }
    }

    public function visitorSid(): ?string
    {
        return $this->visitor['sid'] ?? null;
    }

    public function isReceptionistHome(): bool
    {
        return $this->round === null;
    }

    public function tick(): void
    {
        if (! $this->started) {
            return;
        }

        $now = ($this->clock)();

        $this->tickVisitor($now);
        $this->tickRound($now);

        if ($this->visitor === null && $this->round === null) {
            if ($now >= $this->nextArrivalAt) {
                $this->spawnVisitor($now);
            } elseif ($now - $this->lastActivityAt >= self::IDLE_ROUND_AFTER / $this->speed) {
                $this->startRound($now, null);
            } elseif ($now >= $this->pingAt) {
                $this->home($now); // jaga last_event_at segar supaya sweep tak hantar dia ke chill room
            }
        }
        // Semasa penghantar ada / pusingan jalan, event tool sendiri menjaga last_event_at (tiada ping 'idle'
        // supaya bubble "Terima pakej" tak terpadam).
    }

    // ---- penghantar ----

    private function spawnVisitor(float $now): void
    {
        $keys = array_keys(self::BRANDS);
        // Giliran berpusing, sekali-sekala melompat supaya tak terlalu mudah diteka
        $this->brandCursor += ($this->rand)(1, 5) === 5 ? 2 : 1;
        $brand = $keys[$this->brandCursor % count($keys)];
        $b = self::BRANDS[$brand];
        $name = $b['short'].' '.$b['names'][($this->rand)(0, count($b['names']) - 1)];
        $names = array_keys(self::RECIPIENTS);
        $recipient = $names[($this->rand)(0, count($names) - 1)];

        $this->seq++;
        $sid = self::PREFIX.$brand.'-'.$this->seq;
        $m = ['vendor' => 'generic', 'sid' => $sid, 'auto' => $name, 'label' => $b['label'], 'project' => 'delivery'];

        Agent::updateOrCreate(
            ['vendor' => 'generic', 'session_id' => $sid],
            [
                'name' => $name, 'custom_name' => $name, 'avatar' => $b['avatar'], 'label' => $b['label'],
                'pc' => 'DEMO-PC', 'project' => 'delivery', 'department' => 'door',
                'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now(), 'ended_at' => null,
            ],
        );

        $this->visitor = [
            'm' => $m, 'sid' => $sid, 'brand' => $brand, 'recipient' => $recipient,
            'phase' => 'arrive', 'until' => $now + $this->span(4, 5), 'deleteAt' => 0.0,
        ];
        $this->nextArrivalAt = $now + $this->span(40, 70);
        $this->lastActivityAt = $now;

        ($this->emit)($m, 'session_start', null, null, 'door');
    }

    private function tickVisitor(float $now): void
    {
        $v = &$this->visitor;
        if ($v === null) {
            return;
        }

        if ($v['phase'] === 'arrive' && $now >= $v['until']) {
            $b = self::BRANDS[$v['brand']];
            ($this->emit)($v['m'], 'tool_start', $b['verb'].' '.$b['short'].' untuk '.$v['recipient'], $v['recipient'], 'reception');
            ($this->emit)(self::RECEPTIONIST, 'tool_start', 'Terima pakej '.$b['short'], $v['recipient'], 'frontdesk');
            $v['phase'] = 'handover';
            $v['until'] = $now + $this->span(12, 15);
            $this->lastActivityAt = $now;
        } elseif ($v['phase'] === 'handover' && $now >= $v['until']) {
            $b = self::BRANDS[$v['brand']];
            ($this->emit)($v['m'], 'tool_end', $b['verb'].' '.$b['short'].' untuk '.$v['recipient'], $v['recipient'], 'reception');
            ($this->emit)($v['m'], 'session_end', null, null, 'door');
            $v['phase'] = 'leaving';
            $v['deleteAt'] = $now + self::CLEANUP_AFTER / $this->speed;
            $this->lastActivityAt = $now;
            $this->startRound($now, ['brand' => $b['short'], 'recipient' => $v['recipient']]);
        } elseif ($v['phase'] === 'leaving' && $now >= $v['deleteAt']) {
            $this->deleteVisitor($v['sid']);
            $v = null;
        }
    }

    private function deleteVisitor(string $sid): void
    {
        $agent = Agent::where('vendor', 'generic')->where('session_id', $sid)->first();
        if ($agent) {
            AgentEvent::where('agent_id', $agent->id)->delete();
            $agent->delete();
        }
    }

    private function purgeVisitors(): void
    {
        Agent::where('session_id', 'like', self::PREFIX.'%')->each(function (Agent $agent) {
            AgentEvent::where('agent_id', $agent->id)->delete();
            $agent->delete();
        });
    }

    // ---- penyambut tetamu ----

    /** @param array{brand: string, recipient: string}|null $delivery */
    private function startRound(float $now, ?array $delivery): void
    {
        $stops = [];
        if ($delivery !== null) {
            $stops[] = [
                'dept' => self::RECIPIENTS[$delivery['recipient']] ?? 'ops',
                'text' => 'Arahan: parcel '.$delivery['brand'].' untuk '.$delivery['recipient'],
            ];
        }

        $want = ($this->rand)(3, 4);
        $keys = array_keys(self::PLACES);
        $guard = 0;
        while (count($stops) < $want && $guard++ < 40) {
            $dept = $keys[$this->placeCursor % count($keys)];
            $this->placeCursor++;
            if (in_array($dept, array_column($stops, 'dept'), true)) {
                continue;
            }
            $stops[] = ['dept' => $dept, 'text' => 'Arahan: update status ke '.self::PLACES[$dept]];
        }

        $this->round = ['stops' => $stops, 'i' => 0, 'open' => false, 'until' => 0.0];
        $this->lastActivityAt = $now;
        $this->tickRound($now);
    }

    private function tickRound(float $now): void
    {
        $r = &$this->round;
        if ($r === null) {
            return;
        }

        if ($r['open'] && $now >= $r['until']) {
            $stop = $r['stops'][$r['i']];
            ($this->emit)(self::RECEPTIONIST, 'tool_end', $stop['text'], null, $stop['dept']);
            $r['open'] = false;
            $r['i']++;
        }

        if (! $r['open']) {
            if ($r['i'] >= count($r['stops'])) {
                $r = null;
                $this->lastActivityAt = $now;
                $this->home($now);

                return;
            }
            $stop = $r['stops'][$r['i']];
            ($this->emit)(self::RECEPTIONIST, 'tool_start', $stop['text'], null, $stop['dept']);
            $r['open'] = true;
            $r['until'] = $now + $this->span(6, 9);
        }
    }

    private function home(float $now): void
    {
        ($this->emit)(self::RECEPTIONIST, 'idle', null, null, 'frontdesk');
        $this->pingAt = $now + self::PING_EVERY / $this->speed;
    }

    /** Saat rawak [min, max] dilaraskan dengan speed. */
    private function span(int $min, int $max): float
    {
        return ($this->rand)($min, $max) / $this->speed;
    }
}
