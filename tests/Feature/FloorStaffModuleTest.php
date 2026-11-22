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
        'ceo', 'cfo', 'md', 'hod', 'gaming', 'outdoor_work', 'rooftop',
    ];

    private float $t = 1000.0;

    /** @var array<int, array{sid: string, event: string, tool: ?string, dept: ?string, at: float}> */
    private array $log = [];

    /** @var array<string, true> */
    private array $pantry = [];

    private int $pantryMax = 0;

    /**
     * Modul dengan jam palsu, rawak berbenih dan pintu pantri ujian (had 2, boleh diisi orang lain dulu).
     * $dispatch: hantar juga ke ProcessAgentEvent (DB) atau log sahaja (laju).
     */
    private function module(bool $dispatch = false, ?Closure $enter = null, float $speed = 1.0): FloorStaffModule
    {
        mt_srand(11);

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
