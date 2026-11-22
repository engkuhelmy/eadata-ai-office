<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Models\AgentEvent;
use App\Models\User;
use App\Office\Demo\FloorStaffModule;
use App\Office\Demo\ReceptionModule;
use App\Office\DepartmentRouter;
use App\Office\NormalizedEvent;
use Closure;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Hash;
use Tests\TestCase;

class FloorStaffModuleTest extends TestCase
{
    use RefreshDatabase;

    private const NEW_DEPARTMENTS = [
        'training', 'sales', 'client', 'marketing', 'head_office', 'toilet_2', 'outdoor_chill',
        'ceo', 'cfo', 'md', 'hod', 'gaming', 'auditorium', 'pool', 'rooftop',
    ];

    private float $t = 1000.0;

    /** @var array<int, array{sid: string, event: string, tool: ?string, dept: ?string, at: float}> */
    private array $log = [];

    /** @var array<string, true> */
    private array $pantry = [];

    private int $pantryMax = 0;

    private int $seed = 11;

    private const PARTY_TEXTS = ['Pool party!', 'Bakar BBQ di rooftop'];

    private const LAUNCH_TEXTS = ['Pelancaran produk baharu', 'Hadir pelancaran produk'];

    /**
     * Modul dengan jam palsu, rawak berbenih dan pintu pantri ujian (had 2, boleh diisi orang lain dulu).
     * $dispatch: hantar juga ke ProcessAgentEvent (DB) atau log sahaja (laju).
     */
    private function module(bool $dispatch = false, ?Closure $enter = null, float $speed = 1.0, bool $events = false, ?Closure $rotators = null, ?Closure $rotHook = null): FloorStaffModule
    {
        mt_srand($this->seed);

        return new FloorStaffModule(
            function (array $m, string $event, ?string $tool, ?string $target, ?string $department) use ($dispatch): void {
                $this->log[] = ['sid' => $m['sid'], 'event' => $event, 'tool' => $tool, 'dept' => $department, 'at' => $this->t];
                if ($dispatch) {
                    ProcessAgentEvent::dispatch(new NormalizedEvent(
                        vendor: $m['vendor'], agentKey: $m['sid'], name: $m['auto'], label: $m['label'], pc: 'DEMO-PC',
                        project: 'eadata-web', event: $event, tool: $tool, target: $target, department: $department,
                        ts: new DateTimeImmutable('now'),
                    ));
                }
            },
            fn (): float => $this->t,
            fn (int $min, int $max): int => mt_rand($min, $max),
            $speed,
            $enter ?? function (string $sid): bool {
                if (! isset($this->pantry[$sid]) && count($this->pantry) >= 2) {
                    return false;
                }
                $this->pantry[$sid] = true;

                return true;
            },
            function (string $sid): void {
                unset($this->pantry[$sid]);
            },
            $events,
            $rotators,
            $rotHook,
        );
    }

    private function advance(FloorStaffModule $m, int $seconds): void
    {
        for ($i = 0; $i < $seconds; $i++) {
            $this->t += 1.0;
            $m->tick();
        }
    }

    private function eventsOf(string $sid): array
    {
        return array_values(array_filter($this->log, fn ($e) => $e['sid'] === $sid));
    }

    private function user(string $role): User
    {
        $user = new User(['name' => $role, 'email' => "{$role}@example.test", 'password' => Hash::make('rahsia-kuat-123')]);
        $user->forceFill(['role' => $role])->save();

        return $user;
    }

    public function test_start_registers_twelve_floor_staff_with_names_avatars_and_home_departments(): void
    {
        $this->module()->start();

        $this->assertSame(12, Agent::count());
        $expected = [
            'Datuk Hafiz' => ['claude', 'exec', 'ceo'], 'Mei Ling' => ['codex', 'exec_w', 'cfo'],
            'Rajesh' => ['hermes', 'exec', 'md'], 'Puan Rosnah' => ['antigravity', 'exec_w', 'hod'],
            'Encik Kamal' => ['claude', 'exec', 'head_office'], 'Farah' => ['codex', 'woman', 'marketing'],
            'Iqbal' => ['antigravity', 'genz', 'marketing'], 'Amir' => ['claude', 'default', 'sales'],
            'Liyana' => ['hermes', 'woman', 'sales'], 'Cikgu Azlan' => ['claude', 'default', 'training'],
            'Intern Danial' => ['codex', 'genz', 'training'], 'Intern Sara' => ['antigravity', 'woman', 'training'],
        ];
        foreach ($expected as $name => [$vendor, $avatar, $dept]) {
            $a = Agent::where('custom_name', $name)->firstOrFail();
            $this->assertSame($vendor, $a->vendor, $name);
            $this->assertSame($avatar, $a->avatar, $name);
            $this->assertSame($dept, $a->department, $name);
            $this->assertStringStartsWith('demo-', $a->session_id);
            $this->assertSame('DEMO-PC', $a->pc);
            $this->assertSame('eadata-web', $a->project);
        }
        $this->assertEmpty($this->log, 'start() belum hantar event');
    }

    public function test_every_routine_uses_valid_departments_and_unique_texts(): void
    {
        foreach (FloorStaffModule::staff() as $m) {
            $this->assertContains($m['avatar'], Agent::AVATARS);
            $this->assertCount(count($m['routine']), array_unique(array_column($m['routine'], 3)), "teks berganda {$m['name']}");
            foreach ($m['routine'] as [$dept, $min, $max, $text]) {
                $this->assertContains($dept, DepartmentRouter::DEPARTMENTS, "{$m['name']}: {$dept}");
                $this->assertLessThanOrEqual($max, $min);
                $this->assertNotSame('', $text);
            }
        }
    }

    public function test_staff_follow_their_routine_in_order_and_start_staggered(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 1200);

        // Mula bergilir: hentian pertama tak semua pada saat yang sama
        $firsts = [];
        foreach (FloorStaffModule::staff() as $s) {
            $firsts[] = $this->eventsOf($s['sid'])[0]['at'];
        }
        $this->assertGreaterThan(1, count(array_unique($firsts)));
        $this->assertLessThanOrEqual(1000 + 8, max($firsts));

        foreach (FloorStaffModule::staff() as $s) {
            $texts = array_column($s['routine'], 3);
            $starts = array_values(array_filter($this->eventsOf($s['sid']), fn ($e) => $e['event'] === 'tool_start'));
            $this->assertGreaterThanOrEqual(5, count($starts), "{$s['name']} kurang bergerak");

            $prev = null;
            foreach ($starts as $e) {
                $idx = array_search($e['tool'], $texts, true);
                $this->assertNotFalse($idx, "teks bubble luar rutin: {$e['tool']}");
                $this->assertSame($s['routine'][$idx][0], $e['dept']);
                if ($prev !== null) {
                    $step = ($idx - $prev + count($texts)) % count($texts);
                    // Hentian seterusnya; +2 hanya bila pantri penuh dilangkau
                    $skipped = $s['routine'][($prev + 1) % count($texts)][0] === 'pantry';
                    $this->assertContains($step, $skipped ? [1, 2] : [1], "{$s['name']} lompat rutin");
                }
                $prev = $idx;
            }
        }
    }

    public function test_tool_start_then_tool_end_then_idle_pings_so_sweep_never_moves_them(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 1500);

        foreach (FloorStaffModule::staff() as $s) {
            $events = $this->eventsOf($s['sid']);
            $this->assertNotEmpty(array_filter($events, fn ($e) => $e['event'] === 'idle'), "{$s['name']} tiada ping");

            $dept = null;
            for ($i = 1; $i < count($events); $i++) {
                // Tiada senyap lebih ~20s (sweep chill selepas 120s idle)
                $this->assertLessThanOrEqual(21, $events[$i]['at'] - $events[$i - 1]['at'], "{$s['name']} senyap terlalu lama");
            }
            foreach ($events as $e) {
                if ($e['event'] === 'tool_start') {
                    $dept = $e['dept'];
                } else {
                    $this->assertSame($dept, $e['dept'], 'tool_end / idle di hentian yang sama');
                }
                $this->assertContains($e['event'], ['tool_start', 'tool_end', 'idle']);
            }
        }
    }

    public function test_hold_freezes_everyone_and_resume_restarts_staggered(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 60);

        $m->hold();
        $this->assertTrue($m->isHeld());
        $before = count($this->log);
        $this->advance($m, 300);
        $this->assertSame($before, count($this->log), 'tiada event semasa briefing');
        $this->assertEmpty($this->pantry, 'slot pantri dilepas semasa briefing');

        $resumeAt = $this->t;
        $m->resume();
        $this->assertFalse($m->isHeld());
        $this->advance($m, 10);

        foreach (FloorStaffModule::staff() as $s) {
            $after = array_values(array_filter($this->eventsOf($s['sid']), fn ($e) => $e['at'] > $resumeAt));
            $this->assertNotEmpty($after, "{$s['name']} tak sambung");
            $this->assertSame('tool_start', $after[0]['event']);
        }
    }

    public function test_pantry_gate_is_respected_and_released_after_leaving(): void
    {
        $m = $this->module();
        $m->start();
        $this->advance($m, 3000);

        // Main balik: bilangan dalam pantri (department terakhir = pantry) tak pernah lebih 2
        $in = [];
        $max = 0;
        foreach ($this->log as $e) {
            if ($e['dept'] === 'pantry') {
                $in[$e['sid']] = true;
            } else {
                unset($in[$e['sid']]);
            }
            $max = max($max, count($in));
        }
        $this->assertGreaterThan(0, $max, 'Amir/Liyana tak pernah ke pantri');
        $this->assertLessThanOrEqual(2, $max);

        $visitors = array_unique(array_column(array_filter($this->log, fn ($e) => $e['dept'] === 'pantry'), 'sid'));
        $this->assertEqualsCanonicalizing(['demo-amir', 'demo-liyana'], array_values($visitors));
    }

    public function test_full_pantry_is_skipped(): void
    {
        $m = $this->module(false, fn (string $sid): bool => false);
        $m->start();
        $this->advance($m, 2000);

        $this->assertNotContains('pantry', array_column($this->log, 'dept'));
        $this->assertNotEmpty(array_filter($this->log, fn ($e) => $e['sid'] === 'demo-amir' && $e['dept'] === 'meeting'));
    }

    public function test_events_go_through_the_pipeline_and_bubble_is_the_task_text(): void
    {
        $m = $this->module(true);
        $m->start();
        $this->advance($m, 12);

        $start = collect($this->log)->firstWhere('event', 'tool_start');
        $this->assertNotNull($start);
        $agent = Agent::where('session_id', $start['sid'])->firstOrFail();
        $this->assertSame($start['tool'], $agent->current_task);
        $this->assertSame($start['dept'], $agent->department);
        $this->assertSame('active', $agent->status);
        $this->assertGreaterThan(0, AgentEvent::where('agent_id', $agent->id)->count());
    }

    public function test_speed_scales_the_timeline(): void
    {
        $m = $this->module(false, null, 10.0);
        $m->start();
        $this->advance($m, 2);

        $this->assertCount(12, array_unique(array_column($this->log, 'sid')), 'speed 10: semua mula dalam ~1s');
    }

    public function test_new_departments_are_valid_routable_and_pinnable(): void
    {
        $agent = Agent::create(['vendor' => 'claude', 'session_id' => 'sess-1', 'label' => 'Claude Code', 'name' => 'Claude sess', 'department' => 'backend', 'status' => 'active']);
        $this->actingAs($this->user('owner'));

        foreach (self::NEW_DEPARTMENTS as $dept) {
            $this->assertContains($dept, DepartmentRouter::DEPARTMENTS);
            $this->assertSame($dept, (new DepartmentRouter)->route('tool_start', explicit: $dept));

            $this->patchJson("/office/agents/{$agent->id}", ['department' => $dept])
                ->assertOk()
                ->assertJsonPath('agent.department', $dept);
        }

        // Routing automatik tak berubah: tak pernah hasilkan kunci baharu
        $this->assertSame('frontend', (new DepartmentRouter)->route('tool_start', 'Edit', 'resources/js/app.vue'));
        $this->assertNull((new DepartmentRouter)->route('idle'));
    }

    public function test_outdoor_work_is_gone_and_new_keys_are_pinnable_while_the_old_one_is_rejected(): void
    {
        $this->assertNotContains('outdoor_work', DepartmentRouter::DEPARTMENTS);
        foreach (['auditorium', 'pool'] as $dept) {
            $this->assertContains($dept, DepartmentRouter::DEPARTMENTS);
        }
        foreach (FloorStaffModule::staff() as $s) {
            $this->assertNotContains('outdoor_work', array_column($s['routine'], 0), $s['name']);
        }

        $agent = Agent::create(['vendor' => 'claude', 'session_id' => 'sess-1', 'label' => 'Claude Code', 'name' => 'Claude sess', 'department' => 'backend', 'status' => 'active']);
        $this->actingAs($this->user('owner'));
        $this->patchJson("/office/agents/{$agent->id}", ['department' => 'pool'])->assertOk()->assertJsonPath('agent.department', 'pool');
        $this->patchJson("/office/agents/{$agent->id}", ['department' => 'auditorium'])->assertOk()->assertJsonPath('agent.department', 'auditorium');
        $this->patchJson("/office/agents/{$agent->id}", ['department' => 'outdoor_work'])->assertStatus(422);
    }

    public function test_sales_sit_on_l2_visit_l1_client_meeting_and_auditorium_and_trainer_uses_glass_room_and_auditorium(): void
    {
        $staff = collect(FloorStaffModule::staff())->keyBy('sid');
        foreach (['demo-amir', 'demo-liyana'] as $sid) {
            $depts = array_column($staff[$sid]['routine'], 0);
            $this->assertSame('sales', $depts[0]);
            $this->assertContains('client', $depts);
            $this->assertContains('meeting', $depts);
        }
        $this->assertContains('auditorium', array_column($staff['demo-amir']['routine'], 0));
        $this->assertEqualsCanonicalizing(['training', 'auditorium'], array_unique(array_column($staff['demo-azlan']['routine'], 0)));
        $this->assertContains('pool', array_column($staff['demo-meiling']['routine'], 0));
        $this->assertContains('rooftop', array_column($staff['demo-rajesh']['routine'], 0));
    }

    // ---- acara demo: pelancaran produk + pool party ----

    private function rotators(int $n = 6): array
    {
        $out = [];
        for ($i = 0; $i < $n; $i++) {
            $out[] = ['vendor' => 'claude', 'sid' => "demo-rot$i", 'auto' => "Rot $i", 'label' => 'Claude Code', 'name' => "Rot $i"];
        }

        return $out;
    }

    /** @return array<int, array{sid: string, event: string, tool: ?string, dept: ?string, at: float}> */
    private function after(float $t): array
    {
        return array_values(array_filter($this->log, fn ($e) => $e['at'] >= $t));
    }

    private function logTools(array $tools, ?string $event = null): array
    {
        return array_values(array_filter($this->log, fn ($e) => in_array($e['tool'], $tools, true) && ($event === null || $e['event'] === $event)));
    }

    public function test_launch_event_runs_in_the_auditorium_and_everyone_returns_to_routine(): void
    {
        $m = $this->module(events: true);
        $m->start();

        $this->advance($m, 170);
        $this->assertFalse($m->isLaunchActive(), 'belum ~3 min');
        $this->assertEmpty($this->logTools(self::LAUNCH_TEXTS));

        $this->advance($m, 20);
        $this->assertTrue($m->isLaunchActive());

        $presenter = $this->logTools(['Pelancaran produk baharu']);
        $this->assertCount(1, $presenter);
        $this->assertSame('demo-azlan', $presenter[0]['sid']);
        $this->assertSame('tool_start', $presenter[0]['event']);
        $this->assertSame('auditorium', $presenter[0]['dept']);
        $this->assertSame(1180.0, $presenter[0]['at']);

        $audience = $this->logTools(['Hadir pelancaran produk']);
        $this->assertEqualsCanonicalizing(FloorStaffModule::LAUNCH_AUDIENCE, array_column($audience, 'sid'));
        foreach ($audience as $e) {
            $this->assertSame('tool_start', $e['event']);
            $this->assertSame('auditorium', $e['dept']);
            $this->assertSame($presenter[0]['at'], $e['at']);
        }

        // Semasa acara tiada peserta berpindah (tiada tool_start lain)
        $attendees = array_merge(['demo-azlan'], FloorStaffModule::LAUNCH_AUDIENCE);
        $this->advance($m, 70);
        $moved = array_filter($this->after($presenter[0]['at'] + 1), fn ($e) => in_array($e['sid'], $attendees, true) && $e['event'] === 'tool_start');
        $this->assertEmpty($moved);

        // ~90s kemudian tamat: tool_end di auditorium (urutan: tool_start dahulu, tool_end kemudian)
        $this->advance($m, 40);
        $this->assertFalse($m->isLaunchActive());
        $ends = $this->logTools(self::LAUNCH_TEXTS, 'tool_end');
        $this->assertCount(8, $ends);
        $endAt = $ends[0]['at'];
        $this->assertGreaterThanOrEqual(80, $endAt - $presenter[0]['at']);
        $this->assertLessThanOrEqual(100, $endAt - $presenter[0]['at']);
        foreach ($ends as $e) {
            $this->assertSame('auditorium', $e['dept']);
        }

        // Lepas itu sambung rutin masing-masing (hentian dalam rutin sendiri)
        $this->advance($m, 30);
        foreach ($attendees as $sid) {
            $routine = collect(FloorStaffModule::staff())->firstWhere('sid', $sid)['routine'];
            $back = array_values(array_filter($this->eventsOf($sid), fn ($e) => $e['at'] > $endAt && $e['event'] === 'tool_start'));
            $this->assertNotEmpty($back, "$sid tak sambung rutin");
            $this->assertContains($back[0]['tool'], array_column($routine, 3), "$sid kembali ke rutin");
        }
    }

    public function test_launch_repeats_every_six_to_eight_minutes(): void
    {
        $m = $this->module(events: true);
        $m->start();
        $this->advance($m, 3600);

        $starts = array_column($this->logTools(['Pelancaran produk baharu'], 'tool_start'), 'at');
        $this->assertGreaterThanOrEqual(7, count($starts));
        $this->assertSame(1180.0, $starts[0]);
        for ($i = 1; $i < count($starts); $i++) {
            $this->assertGreaterThanOrEqual(360, $starts[$i] - $starts[$i - 1]);
            // 6-8 min; boleh tertunda sedikit kalau Cikgu Azlan kebetulan sedang pool party
            $this->assertLessThanOrEqual(481 + 90, $starts[$i] - $starts[$i - 1]);
        }
    }

    public function test_launch_and_party_are_speed_aware(): void
    {
        $m = $this->module(events: true, speed: 10.0, rotators: fn (): array => $this->rotators());
        $m->start();
        $this->advance($m, 17);
        $this->assertEmpty($this->logTools(self::LAUNCH_TEXTS), '180s / 10 = 18s');
        $this->advance($m, 3);
        $this->assertNotEmpty($this->logTools(self::LAUNCH_TEXTS));
        $this->advance($m, 12); // acara ~9s
        $this->assertFalse($m->isLaunchActive());
        $this->advance($m, 11); // parti pada ~30s
        $this->assertNotEmpty($this->logTools(self::PARTY_TEXTS));
    }

    public function test_pool_party_has_six_to_eight_guests_at_pool_or_rooftop_then_everyone_returns(): void
    {
        $hook = [];
        $rotators = $this->rotators(4);
        $m = $this->module(
            events: true,
            rotators: fn (): array => $rotators,
            rotHook: function (string $sid, bool $join) use (&$hook): void {
                $hook[] = [$sid, $join];
            },
        );
        $m->start();

        $this->advance($m, 295);
        $this->assertFalse($m->isPartyActive());
        $this->assertEmpty($this->logTools(self::PARTY_TEXTS));
        $this->advance($m, 10);
        $this->assertTrue($m->isPartyActive());

        $party = $this->logTools(self::PARTY_TEXTS);
        $this->assertGreaterThanOrEqual(6, count($party));
        $this->assertLessThanOrEqual(8, count($party));
        $this->assertCount(count($party), array_unique(array_column($party, 'sid')), 'seorang sekali');
        foreach ($party as $e) {
            $this->assertSame('tool_start', $e['event']);
            $this->assertSame($e['tool'] === 'Pool party!' ? 'pool' : 'rooftop', $e['dept']);
        }
        $rotSids = array_column($rotators, 'sid');
        $rotGuests = array_values(array_filter(array_column($party, 'sid'), fn ($sid) => in_array($sid, $rotSids, true)));
        $this->assertEqualsCanonicalizing($rotGuests, array_column(array_filter($hook, fn ($h) => $h[1]), 0), 'hook join untuk rotator tetamu');
        $partyStart = $party[0]['at'];

        $this->advance($m, 100);
        $this->assertFalse($m->isPartyActive());
        $ends = $this->logTools(self::PARTY_TEXTS, 'tool_end');
        $this->assertCount(count($party), $ends);
        $endAt = $ends[0]['at'];
        $this->assertGreaterThanOrEqual(65, $endAt - $partyStart);
        $this->assertLessThanOrEqual(85, $endAt - $partyStart);
        $this->assertEqualsCanonicalizing($rotGuests, array_column(array_filter($hook, fn ($h) => ! $h[1]), 0), 'rotator dilepas semula');

        // Staff aras sambung rutin masing-masing
        $this->advance($m, 20);
        $floorGuests = array_values(array_diff(array_column($party, 'sid'), $rotSids));
        $this->assertNotEmpty($floorGuests);
        foreach ($floorGuests as $sid) {
            $routine = collect(FloorStaffModule::staff())->firstWhere('sid', $sid)['routine'];
            $back = array_values(array_filter($this->eventsOf($sid), fn ($e) => $e['at'] > $endAt && $e['event'] === 'tool_start'));
            $this->assertNotEmpty($back, "$sid tak sambung");
            $this->assertContains($back[0]['tool'], array_column($routine, 3));
        }
    }

    public function test_pool_party_repeats_every_ten_to_twelve_minutes(): void
    {
        $m = $this->module(events: true, rotators: fn (): array => $this->rotators());
        $m->start();
        $this->advance($m, 4000);

        $starts = [];
        foreach ($this->logTools(self::PARTY_TEXTS, 'tool_start') as $e) {
            $starts[(string) $e['at']] = $e['at'];
        }
        $starts = array_values($starts);
        $this->assertGreaterThanOrEqual(5, count($starts));
        $this->assertSame(1300.0, $starts[0]);
        for ($i = 1; $i < count($starts); $i++) {
            $this->assertGreaterThanOrEqual(600, $starts[$i] - $starts[$i - 1]);
            $this->assertLessThanOrEqual(721, $starts[$i] - $starts[$i - 1]);
        }
    }

    public function test_pool_party_never_invites_anyone_in_the_pantry_gate_and_launch_frees_their_slot(): void
    {
        $partyChecked = 0;
        $launchChecked = 0;

        foreach (range(1, 40) as $seed) {
            $this->seed = $seed;
            $this->log = [];
            $this->pantry = [];
            $this->t = 1000.0;
            $m = $this->module(events: true);
            $m->start();

            $partySeen = false;
            $launchSeen = false;
            for ($i = 0; $i < 400 && ! ($partySeen && $launchSeen); $i++) {
                $inPantry = array_keys($this->pantry);
                $this->t += 1.0;
                $m->tick();

                if (! $launchSeen && $m->isLaunchActive()) {
                    $launchSeen = true;
                    $freed = array_intersect($inPantry, FloorStaffModule::LAUNCH_AUDIENCE, ['demo-amir', 'demo-liyana', 'demo-azlan']);
                    $this->assertEmpty(array_intersect(array_keys($this->pantry), FloorStaffModule::LAUNCH_AUDIENCE), 'penonton tak pegang slot pantri');
                    $launchChecked += count($freed) > 0 ? 1 : 0;
                }
                if (! $partySeen && $m->isPartyActive()) {
                    $partySeen = true;
                    $guests = array_column($this->logTools(self::PARTY_TEXTS, 'tool_start'), 'sid');
                    $this->assertEmpty(array_intersect($guests, $inPantry), "seed $seed: tetamu parti dari pantri");
                    $partyChecked += count($inPantry) > 0 ? 1 : 0;
                }
            }
            $this->assertTrue($partySeen && $launchSeen);
            $this->assertLessThanOrEqual(2, count($this->pantry));
        }

        $this->assertGreaterThan(0, $partyChecked, 'tiada senario pantri semasa parti diuji');
        $this->assertGreaterThan(0, $launchChecked, 'tiada senario pantri semasa launch diuji');
    }

    public function test_events_never_run_while_held_and_hold_cancels_a_running_event(): void
    {
        $hook = [];
        $rotators = $this->rotators();
        $m = $this->module(events: true, rotators: fn (): array => $rotators, rotHook: function (string $sid, bool $join) use (&$hook): void {
            $hook[] = [$sid, $join];
        });
        $m->start();
        $this->advance($m, 305); // parti sedang jalan, launch dah tamat
        $this->assertTrue($m->isPartyActive());
        $joined = count(array_filter($hook, fn ($h) => $h[1]));

        $m->hold();
        $this->assertFalse($m->isPartyActive());
        $this->assertFalse($m->isLaunchActive());
        $this->assertCount($joined, array_filter($hook, fn ($h) => ! $h[1]), 'rotator parti dilepas bila briefing');

        // Semasa briefing (jauh lewat jadual): senyap, tiada acara
        $before = count($this->log);
        $this->advance($m, 1500);
        $this->assertSame($before, count($this->log));

        // Resume: acara tertunggak ditunda, tak serentak dengan resume
        $resumeAt = $this->t;
        $m->resume();
        $this->advance($m, 20);
        $this->assertEmpty(array_filter($this->after($resumeAt), fn ($e) => in_array($e['tool'], array_merge(self::LAUNCH_TEXTS, self::PARTY_TEXTS), true)));
        $this->advance($m, 60);
        $this->assertNotEmpty(array_filter($this->after($resumeAt), fn ($e) => $e['tool'] === 'Pelancaran produk baharu'));
    }

    public function test_events_can_be_disabled(): void
    {
        $m = $this->module(events: false, rotators: fn (): array => $this->rotators());
        $m->start();
        $this->advance($m, 2500);

        $this->assertEmpty($this->logTools(array_merge(self::LAUNCH_TEXTS, self::PARTY_TEXTS)));
        $this->assertFalse($m->isLaunchActive());
        $this->assertFalse($m->isPartyActive());
    }

    public function test_demo_command_no_events_flag_keeps_floors_but_skips_the_events(): void
    {
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true, '--no-events' => true])->assertSuccessful();

        $this->assertSame(25, Agent::count());
        $this->assertSame(0, AgentEvent::whereIn('tool', array_merge(self::LAUNCH_TEXTS, self::PARTY_TEXTS))->count());
        $this->assertGreaterThan(0, AgentEvent::where('event', 'tool_start')->whereIn('department', ['ceo', 'sales'])->count());
    }

    public function test_demo_command_runs_both_events_end_to_end(): void
    {
        // Satu kitaran penuh ~412s masa demo (> 300s): pelancaran (3 min) dan pool party (5 min) sempat berlaku
        $this->artisan('office:demo', ['--once' => true, '--speed' => 800, '--hours' => 1, '--no-reception' => true])->assertSuccessful();

        $this->assertGreaterThan(0, AgentEvent::where('tool', 'Pelancaran produk baharu')->where('department', 'auditorium')->count());
        $this->assertGreaterThan(0, AgentEvent::where('tool', 'Hadir pelancaran produk')->where('department', 'auditorium')->count());
        $this->assertGreaterThan(0, AgentEvent::whereIn('tool', self::PARTY_TEXTS)->whereIn('department', ['pool', 'rooftop'])->count());
        $this->assertSame(0, AgentEvent::where('event', 'session_end')->count());
    }

    public function test_no_floors_flag_also_disables_the_events(): void
    {
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true, '--no-floors' => true])->assertSuccessful();

        $this->assertSame(0, AgentEvent::whereIn('tool', array_merge(self::LAUNCH_TEXTS, self::PARTY_TEXTS))->count());
    }

    public function test_rotators_chill_in_the_new_rooms(): void
    {
        $this->assertSame(['playroom', 'gaming', 'pool', 'rooftop', 'outdoor_chill'], \App\Console\Commands\OfficeDemo::CHILL_ROOMS);
        foreach (\App\Console\Commands\OfficeDemo::CHILL_ROOMS as $room) {
            $this->assertContains($room, DepartmentRouter::DEPARTMENTS);
        }
    }

    public function test_exec_avatars_are_accepted_by_patch(): void
    {
        $this->assertSame(['exec', 'exec_w'], array_slice(Agent::AVATARS, -2));

        $agent = Agent::create(['vendor' => 'claude', 'session_id' => 'sess-1', 'label' => 'Claude Code', 'name' => 'Claude sess', 'department' => 'backend', 'status' => 'active']);
        $this->actingAs($this->user('owner'));

        foreach (['exec', 'exec_w'] as $avatar) {
            $this->patchJson("/office/agents/{$agent->id}", ['avatar' => $avatar])
                ->assertOk()
                ->assertJsonPath('agent.avatar', $avatar);
        }
    }

    public function test_demo_command_runs_floor_staff_and_everyone_attends_the_briefing(): void
    {
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true])->assertSuccessful();

        $this->assertSame(25, Agent::count());

        $briefing = AgentEvent::where('department', 'boardroom')->where('event', 'subagent_start')->distinct()->pluck('agent_id');
        $this->assertCount(25, $briefing, 'semua staff (kecuali Reni) hadir briefing');

        foreach (FloorStaffModule::staff() as $s) {
            $agent = Agent::where('session_id', $s['sid'])->firstOrFail();
            $events = $agent->events()->orderBy('id')->get();
            $firstBoardroom = $events->search(fn ($e) => $e->event === 'subagent_start');
            $firstWork = $events->search(fn ($e) => $e->event === 'tool_start');
            $this->assertNotFalse($firstBoardroom, "{$s['name']} tak masuk briefing");
            $this->assertNotFalse($firstWork, "{$s['name']} tak sambung rutin selepas briefing");
            $this->assertLessThan($firstWork, $firstBoardroom, "{$s['name']} bergerak sebelum briefing");
        }

        // Pantri L1 tak pernah lebih 2 orang (staff team + rotator + staff aras kongsi pintu yang sama)
        $in = [];
        $max = 0;
        foreach (AgentEvent::query()->orderBy('id')->get(['agent_id', 'department']) as $e) {
            if ($e->department === 'pantry') {
                $in[$e->agent_id] = true;
            } else {
                unset($in[$e->agent_id]);
            }
            $max = max($max, count($in));
        }
        $this->assertLessThanOrEqual(2, $max);

        $this->assertSame(0, AgentEvent::where('event', 'session_end')->count());
    }

    public function test_no_floors_option_disables_the_module(): void
    {
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true, '--no-floors' => true])->assertSuccessful();

        $this->assertSame(0, Agent::whereIn('session_id', array_column(FloorStaffModule::staff(), 'sid'))->count());
        $this->assertSame(0, Agent::where('session_id', ReceptionModule::SID)->count());
    }
}
