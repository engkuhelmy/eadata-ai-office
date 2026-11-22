<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Office\Demo\ReceptionModule;
use App\Office\DepartmentRouter;
use App\Office\NormalizedEvent;
use Closure;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ReceptionModuleTest extends TestCase
{
    use RefreshDatabase;

    private float $t = 1000.0;

    /** @var array<int, array{sid: string, event: string, tool: ?string, target: ?string, dept: ?string, at: float}> */
    private array $log = [];

    /** Modul dengan jam palsu, rawak berbenih, dan emit yang masuk ProcessAgentEvent (queue sync dalam test). */
    private function module(?Closure $rand = null, float $speed = 1.0): ReceptionModule
    {
        mt_srand(42);

        return new ReceptionModule(
            function (array $m, string $event, ?string $tool, ?string $target, ?string $department): void {
                $this->log[] = ['sid' => $m['sid'], 'event' => $event, 'tool' => $tool, 'target' => $target, 'dept' => $department, 'at' => $this->t];
                ProcessAgentEvent::dispatch(new NormalizedEvent(
                    vendor: $m['vendor'], agentKey: $m['sid'], name: $m['auto'], label: $m['label'], pc: 'DEMO-PC',
                    project: $m['project'] ?? 'eadata-web', event: $event, tool: $tool, target: $target, department: $department,
                    ts: new DateTimeImmutable('now'),
                ));
            },
            fn (): float => $this->t,
            $rand ?? fn (int $min, int $max): int => mt_rand($min, $max),
            $speed,
        );
    }

    /** Maju jam palsu 1 saat demi 1 saat. */
    private function advance(ReceptionModule $m, int $seconds, ?Closure $each = null): void
    {
        for ($i = 0; $i < $seconds; $i++) {
            $this->t += 1.0;
            $m->tick();
            if ($each) {
                $each($m);
            }
        }
    }

    private function visitorEvents(string $sid): array
    {
        return array_values(array_filter($this->log, fn ($e) => $e['sid'] === $sid));
    }

    private function receptionistEvents(): array
    {
        return array_values(array_filter($this->log, fn ($e) => $e['sid'] === ReceptionModule::SID));
    }

    private function visitorSids(): array
    {
        return array_values(array_unique(array_filter(array_column($this->log, 'sid'), fn ($s) => str_starts_with($s, ReceptionModule::PREFIX))));
    }

    public function test_start_registers_receptionist_and_purges_leftover_visitors(): void
    {
        $left = Agent::create(['vendor' => 'generic', 'session_id' => 'demo-visit-dhl-9', 'name' => 'DHL Ravi', 'label' => 'DHL Express', 'status' => 'active', 'department' => 'reception']);
        AgentEvent::create(['agent_id' => $left->id, 'event' => 'tool_start', 'department' => 'reception', 'ts' => now()]);

        $this->module()->start();

        $this->assertSame(0, Agent::where('session_id', 'like', 'demo-visit-%')->count());
        $this->assertSame(0, AgentEvent::where('agent_id', $left->id)->count());

        $reni = Agent::where('session_id', ReceptionModule::SID)->firstOrFail();
        $this->assertSame('generic', $reni->vendor);
        $this->assertSame('Reni', $reni->custom_name);
        $this->assertSame('Reception AI', $reni->label);
        $this->assertSame('recep', $reni->avatar);
        $this->assertSame('DEMO-PC', $reni->pc);
        $this->assertSame('frontdesk', $reni->department);
        $this->assertNull($reni->ended_at);
    }

    public function test_visitor_lifecycle_door_then_reception_then_leave_then_cleanup(): void
    {
        $m = $this->module();
        $m->start();

        $seenDuring = null;
        $this->advance($m, 200, function (ReceptionModule $m) use (&$seenDuring) {
            if ($m->visitorSid() !== null && $seenDuring === null) {
                $a = Agent::where('session_id', $m->visitorSid())->first();
                if ($a) {
                    $seenDuring = $a->only(['vendor', 'avatar', 'pc', 'project', 'department', 'status', 'custom_name', 'label']);
                }
            }
        });

        $sids = $this->visitorSids();
        $this->assertGreaterThanOrEqual(1, count($sids));
        $first = $this->visitorEvents($sids[0]);

        // Urutan: session_start (door) -> tool_start (reception) -> tool_end (reception) -> session_end (door)
        $this->assertSame(['session_start', 'tool_start', 'tool_end', 'session_end'], array_column($first, 'event'));
        $this->assertSame(['door', 'reception', 'reception', 'door'], array_column($first, 'dept'));

        // Tempoh: ~4-5s di pintu, ~12-15s di kaunter
        $this->assertEqualsWithDelta(4.5, $first[1]['at'] - $first[0]['at'], 0.6);
        $this->assertEqualsWithDelta(13.5, $first[3]['at'] - $first[1]['at'], 1.6);

        // Bubble = teks tool, sebut brand + penerima
        $this->assertMatchesRegularExpression('/^Hantar (makanan|parcel) .+ untuk .+$/', $first[1]['tool']);
        $this->assertArrayHasKey($first[1]['target'], ReceptionModule::RECIPIENTS);
        $this->assertSame(explode(' untuk ', $first[1]['tool'])[1], $first[1]['target']);

        // Semasa hidup: Agent berdaftar dengan avatar jenama
        $this->assertNotNull($seenDuring);
        $this->assertContains($seenDuring['avatar'], ['grab', 'shopee', 'jnt', 'dhl']);
        $this->assertSame('generic', $seenDuring['vendor']);
        $this->assertSame('delivery', $seenDuring['project']);
        $this->assertSame('DEMO-PC', $seenDuring['pc']);

        // Lepas keluar, baris Agent + event dipadam
        $this->assertSame(0, Agent::where('session_id', $sids[0])->count());
        $this->assertSame(0, AgentEvent::whereHas('agent', fn ($q) => $q->where('session_id', $sids[0]))->count());
        $this->assertSame(1, Agent::where('session_id', ReceptionModule::SID)->count());
    }

    public function test_cleanup_happens_about_25_seconds_after_session_end(): void
    {
        $m = $this->module();
        $m->start();

        $endedAt = null;
        $deletedAt = null;
        $this->advance($m, 120, function () use (&$endedAt, &$deletedAt) {
            $sids = $this->visitorSids();
            if (! $sids || $deletedAt !== null) {
                return;
            }
            $sid = $sids[0];
            if ($endedAt === null && Agent::where('session_id', $sid)->where('status', 'ended')->exists()) {
                $endedAt = $this->t;
            }
            if ($endedAt !== null && ! Agent::where('session_id', $sid)->exists()) {
                $deletedAt = $this->t;
            }
        });

        $this->assertNotNull($endedAt);
        $this->assertNotNull($deletedAt);
        $this->assertEqualsWithDelta(25, $deletedAt - $endedAt, 1.5);
    }

    public function test_only_one_visitor_at_a_time_and_several_arrive_over_time(): void
    {
        $m = $this->module();
        $m->start();

        $max = 0;
        $this->advance($m, 900, function () use (&$max) {
            $max = max($max, Agent::where('session_id', 'like', 'demo-visit-%')->count());
        });

        $this->assertSame(1, $max);
        $sids = $this->visitorSids();
        $this->assertGreaterThanOrEqual(5, count($sids));
        $this->assertSame(count($sids), count(array_unique($sids)), 'session id mesti unik');

        // Semua brand dapat giliran
        $brands = array_unique(array_map(fn ($s) => explode('-', $s)[2], $sids));
        $this->assertEqualsCanonicalizing(['grab', 'shopee', 'jnt', 'dhl'], $brands);

        // Jarak antara dua ketibaan: sekurang-kurangnya 40s
        $starts = array_values(array_column(array_filter($this->log, fn ($e) => $e['event'] === 'session_start'), 'at'));
        for ($i = 1; $i < count($starts); $i++) {
            $this->assertGreaterThanOrEqual(40, $starts[$i] - $starts[$i - 1]);
        }
    }

    public function test_first_arrival_is_15_to_20_seconds_after_start(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 40);

        $starts = array_values(array_filter($this->log, fn ($e) => $e['event'] === 'session_start'));
        $this->assertNotEmpty($starts);
        $this->assertGreaterThanOrEqual(1015.0, $starts[0]['at']);
        $this->assertLessThanOrEqual(1020.0, $starts[0]['at']);
    }

    public function test_receptionist_takes_the_parcel_then_does_a_round_starting_at_the_recipient_and_returns(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 90);

        $sid = $this->visitorSids()[0];
        $visitor = $this->visitorEvents($sid);
        $recipient = $visitor[1]['target'];
        $brandShort = explode(' ', $visitor[1]['tool'])[2];

        $reni = $this->receptionistEvents();
        $take = array_values(array_filter($reni, fn ($e) => $e['event'] === 'tool_start' && str_starts_with((string) $e['tool'], 'Terima pakej')));
        $this->assertNotEmpty($take);
        $this->assertSame('Terima pakej '.$brandShort, $take[0]['tool']);
        $this->assertSame('frontdesk', $take[0]['dept']);
        $this->assertEqualsWithDelta($visitor[1]['at'], $take[0]['at'], 0.01); // serentak penghantar sampai kaunter

        // Pusingan bermula selepas penghantar tamat (session_end)
        $round = array_values(array_filter($reni, fn ($e) => $e['at'] >= $visitor[3]['at'] && in_array($e['event'], ['tool_start', 'tool_end', 'idle'], true)));
        $this->assertSame('tool_start', $round[0]['event']);
        $this->assertSame(ReceptionModule::RECIPIENTS[$recipient], $round[0]['dept']);
        $this->assertSame('Arahan: parcel '.$brandShort.' untuk '.$recipient, $round[0]['tool']);

        $starts = array_values(array_filter($round, fn ($e) => $e['event'] === 'tool_start'));
        $ends = array_values(array_filter($round, fn ($e) => $e['event'] === 'tool_end'));
        $this->assertGreaterThanOrEqual(3, count($ends));
        $this->assertLessThanOrEqual(4, count($ends));
        foreach ($ends as $i => $end) {
            $this->assertSame($starts[$i]['dept'], $end['dept'], 'tool_end di tempat yang sama dengan tool_start');
            $this->assertGreaterThanOrEqual(6, $end['at'] - $starts[$i]['at']);
            $this->assertLessThanOrEqual(9, $end['at'] - $starts[$i]['at']);
        }
        $this->assertSame(count($ends), count(array_unique(array_column($ends, 'dept'))), 'tiada hentian berganda');

        // Habis pusingan: balik ke frontdesk
        $lastEnd = end($ends);
        $back = array_values(array_filter($round, fn ($e) => $e['event'] === 'idle' && $e['at'] >= $lastEnd['at']));
        $this->assertNotEmpty($back);
        $this->assertSame('frontdesk', $back[0]['dept']);
        $this->assertSame('frontdesk', Agent::where('session_id', ReceptionModule::SID)->value('department'));
    }

    public function test_receptionist_covers_every_place_over_time(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 1800);

        $visited = array_unique(array_column(array_filter($this->receptionistEvents(), fn ($e) => $e['event'] === 'tool_start' && str_starts_with((string) $e['tool'], 'Arahan')), 'dept'));
        foreach (array_keys(ReceptionModule::PLACES) as $dept) {
            $this->assertContains($dept, $visited, "Reni tak pernah ke {$dept}");
        }
        foreach (array_column($this->receptionistEvents(), 'dept') as $dept) {
            $this->assertContains($dept, DepartmentRouter::DEPARTMENTS);
        }
    }

    public function test_next_visitor_never_arrives_before_receptionist_is_back_at_frontdesk(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 900);

        $reni = $this->receptionistEvents();
        foreach (array_filter($this->log, fn ($e) => $e['event'] === 'session_start') as $arrival) {
            $before = array_values(array_filter($reni, fn ($e) => $e['at'] <= $arrival['at']));
            $last = end($before);
            $this->assertSame('idle', $last['event'], 'penyambut belum balik sebelum penghantar baru');
            $this->assertSame('frontdesk', $last['dept']);
        }
    }

    public function test_receptionist_pings_home_and_does_an_idle_round_when_no_delivery_for_three_minutes(): void
    {
        // Ketibaan pertama dilengahkan jauh (rawak 15-20 jadi 100000 saat)
        $m = $this->module(fn (int $min, int $max): int => $min === 15 ? 100000 : mt_rand($min, $max));
        $m->start();
        $this->advance($m, 100);

        $idle = array_filter($this->receptionistEvents(), fn ($e) => $e['event'] === 'idle' && $e['dept'] === 'frontdesk');
        $this->assertGreaterThanOrEqual(5, count($idle)); // ping ~20s sekali
        $this->assertEmpty($this->visitorSids());

        $this->advance($m, 150); // lepas 180s tanpa aktiviti
        $rounds = array_values(array_filter($this->receptionistEvents(), fn ($e) => $e['event'] === 'tool_start'));
        $this->assertNotEmpty($rounds);
        $this->assertStringStartsWith('Arahan: update status ke', $rounds[0]['tool']);
        $this->assertEmpty($this->visitorSids());
    }

    public function test_speed_scales_the_timeline(): void
    {
        $m = $this->module(null, 10.0);
        $m->start();
        $this->advance($m, 4);

        $starts = array_values(array_filter($this->log, fn ($e) => $e['event'] === 'session_start'));
        $this->assertNotEmpty($starts, 'speed 10: ketibaan pertama dalam ~2s');
    }

    public function test_finish_removes_a_visitor_that_is_still_inside(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 22);
        $this->assertNotNull($m->visitorSid());
        $this->assertSame(1, Agent::where('session_id', 'like', 'demo-visit-%')->count());

        $m->finish();

        $this->assertNull($m->visitorSid());
        $this->assertSame(0, Agent::where('session_id', 'like', 'demo-visit-%')->count());
        $this->assertSame(1, Agent::where('session_id', ReceptionModule::SID)->count());
    }

    public function test_sweep_skips_demo_visit_sessions_until_they_are_ended_explicitly(): void
    {
        $visitor = Agent::create([
            'vendor' => 'generic', 'session_id' => 'demo-visit-grab-1', 'name' => 'Grab Adam', 'label' => 'Grab Food',
            'status' => 'active', 'department' => 'reception', 'last_event_at' => now()->subHours(5),
        ]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertNull($visitor->fresh()->ended_at);
        $this->assertNotSame('ended', $visitor->fresh()->status);
    }

    public function test_demo_command_adds_the_receptionist_and_can_disable_the_module(): void
    {
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1])->assertSuccessful();

        // 13 staff IT + 12 staff aras + Reni
        $this->assertSame(26, Agent::where('session_id', 'not like', 'demo-visit-%')->count());
        $this->assertSame('recep', Agent::where('session_id', ReceptionModule::SID)->value('avatar'));
        $this->assertSame(0, Agent::where('session_id', 'like', 'demo-visit-%')->count(), 'penghantar dibersihkan bila demo tamat');
        // Reni tak ikut briefing semua staff (kekal di mejanya)
        $reni = Agent::where('session_id', ReceptionModule::SID)->firstOrFail();
        $this->assertSame(0, $reni->events()->where('event', 'subagent_start')->count());

        Agent::query()->delete();
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true, '--no-floors' => true])->assertSuccessful();

        $this->assertSame(13, Agent::count());
        $this->assertSame(0, Agent::where('session_id', ReceptionModule::SID)->count());
    }

    public function test_receptionist_round_spans_the_whole_building_and_recipients_include_floor_staff(): void
    {
        foreach (['training', 'sales', 'client', 'marketing', 'head_office', 'ceo', 'cfo', 'md', 'hod', 'gaming', 'outdoor_work', 'rooftop'] as $dept) {
            $this->assertArrayHasKey($dept, ReceptionModule::PLACES);
        }
        foreach (array_merge(array_keys(ReceptionModule::PLACES), ReceptionModule::RECIPIENTS) as $dept) {
            $this->assertContains($dept, DepartmentRouter::DEPARTMENTS);
        }
        foreach (\App\Office\Demo\FloorStaffModule::staff() as $m) {
            $this->assertSame($m['routine'][0][0], ReceptionModule::RECIPIENTS[$m['name']] ?? null, "penerima {$m['name']}");
        }
        $this->assertCount(25, ReceptionModule::RECIPIENTS);
    }

    public function test_receptionist_skips_the_pantry_when_it_is_full(): void
    {
        mt_srand(7);
        $log = [];
        $m = new ReceptionModule(
            function (array $m, string $event, ?string $tool, ?string $target, ?string $department) use (&$log): void {
                $log[] = $department;
            },
            fn (): float => $this->t,
            fn (int $min, int $max): int => mt_rand($min, $max),
            1.0,
            fn (string $sid): bool => false, // pantri sentiasa penuh
            fn (string $sid) => null,
        );
        $m->start();
        $this->advance($m, 3600);

        $this->assertNotContains('pantry', $log);
        $this->assertContains('rooftop', $log);
    }

    public function test_new_reception_departments_and_avatars_are_valid(): void
    {
        $this->assertContains('reception', DepartmentRouter::DEPARTMENTS);
        $this->assertContains('frontdesk', DepartmentRouter::DEPARTMENTS);
        $this->assertSame('reception', (new DepartmentRouter)->route('tool_start', explicit: 'reception'));
        $this->assertSame(['recep', 'grab', 'shopee', 'jnt', 'dhl'], array_slice(Agent::AVATARS, 4, 5));
    }
}
