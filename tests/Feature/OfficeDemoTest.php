<?php

namespace Tests\Feature;

use App\Console\Commands\OfficeDemo;
use App\Models\Agent;
use App\Models\AgentEvent;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class OfficeDemoTest extends TestCase
{
    use RefreshDatabase;

    private function runDemo(): void
    {
        // speed besar: satu kitaran siap dalam beberapa saat. Queue = sync dalam test.
        // 13 staff IT sahaja (modul reception dan staff aras diuji berasingan)
        $this->artisan('office:demo', ['--once' => true, '--speed' => 400, '--hours' => 1, '--no-reception' => true, '--no-floors' => true])->assertSuccessful();
    }

    public function test_demo_creates_thirteen_staff_from_four_vendors_with_friendly_names(): void
    {
        $this->runDemo();

        $this->assertSame(13, Agent::count());
        $this->assertEqualsCanonicalizing(
            array_merge(
                array_fill(0, 5, 'claude'),
                array_fill(0, 3, 'codex'),
                array_fill(0, 2, 'hermes'),
                array_fill(0, 3, 'antigravity'),
            ),
            Agent::pluck('vendor')->all(),
        );
        $this->assertEqualsCanonicalizing(
            ['Aiman', 'Balqis', 'Chandra', 'Dewi', 'Evan', 'Nurul', 'Sofea', 'Aina', 'Zack', 'Danish', 'Mika', 'Qila', 'Hakim'],
            Agent::pluck('custom_name')->all(),
        );
        $this->assertSame(['DEMO-PC'], Agent::pluck('pc')->unique()->values()->all());
        $this->assertSame(['eadata-web'], Agent::pluck('project')->unique()->values()->all());
    }

    public function test_demo_staff_get_their_avatars(): void
    {
        $this->runDemo();

        $expected = [
            'Aiman' => 'default', 'Balqis' => 'woman', 'Chandra' => 'default', 'Dewi' => 'woman', 'Evan' => 'hiphop',
            'Nurul' => 'woman', 'Sofea' => 'woman', 'Aina' => 'woman',
            'Zack' => 'hiphop', 'Danish' => 'hiphop',
            'Mika' => 'genz', 'Qila' => 'genz', 'Hakim' => 'genz',
        ];

        foreach ($expected as $name => $avatar) {
            $this->assertSame($avatar, Agent::where('custom_name', $name)->value('avatar'), "avatar {$name}");
        }
    }

    public function test_everyone_goes_to_the_boardroom_before_working(): void
    {
        $this->runDemo();

        foreach (Agent::all() as $agent) {
            $events = $agent->events()->orderBy('id')->get();
            $firstBoardroom = $events->search(fn ($e) => $e->department === 'boardroom');
            $firstWork = $events->search(fn ($e) => in_array($e->event, ['tool_start', 'tool_end'], true));

            $this->assertNotFalse($firstBoardroom, "{$agent->custom_name} tak masuk boardroom");
            $this->assertNotFalse($firstWork, "{$agent->custom_name} tak kerja");
            $this->assertLessThan($firstWork, $firstBoardroom, "{$agent->custom_name} kerja sebelum briefing");
            $this->assertSame('Board briefing', $events[$firstBoardroom]->target);
        }
    }

    public function test_rotators_visit_toilet_pantry_chill_room_and_their_workstations(): void
    {
        $this->runDemo();

        $departments = AgentEvent::query()->distinct()->pluck('department')->all();

        foreach (['toilet_2', 'pantry', 'research', 'deploy', 'ops'] as $department) {
            $this->assertContains($department, $departments, "tiada event di {$department}");
        }
        // Rotator kerja di L2: guna tandas L2, bukan tandas L1
        $this->assertNotContains('toilet', $departments);
        // Chill di salah satu bilik chill (dipilih rawak setiap lawatan)
        $this->assertNotEmpty(array_intersect(OfficeDemo::CHILL_ROOMS, $departments), 'tiada rotator ke bilik chill');

        // Rotator rehat dengan event 'idle' (bukan tool) di bilik masing-masing
        $rooms = array_merge(['toilet_2', 'pantry'], OfficeDemo::CHILL_ROOMS);
        $this->assertGreaterThan(0, AgentEvent::where('event', 'idle')->whereIn('department', $rooms)->count());
    }

    /** Main balik event ikut id: kira berapa orang "dalam pantri" (department terakhir = pantry) pada setiap saat. */
    private function pantryReplay(): array
    {
        $in = [];
        $max = 0;
        $visited = [];

        foreach (AgentEvent::query()->orderBy('id')->get(['id', 'agent_id', 'department']) as $e) {
            if ($e->department === 'pantry') {
                $in[$e->agent_id] = true;
                $visited[$e->agent_id] = true;
            } else {
                unset($in[$e->agent_id]);
            }
            $max = max($max, count($in));
        }

        return ['max' => $max, 'visited' => count($visited), 'visitedIds' => array_keys($visited)];
    }

    public function test_pantry_never_has_more_than_two_people_at_once(): void
    {
        $this->runDemo();

        $replay = $this->pantryReplay();

        $this->assertGreaterThan(0, $replay['max'], 'tiada sesiapa ke pantri');
        $this->assertLessThanOrEqual(2, $replay['max'], 'pantri lebih 2 orang serentak');
    }

    public function test_at_least_eight_different_staff_take_a_drink_in_the_pantry(): void
    {
        $this->runDemo();

        $replay = $this->pantryReplay();

        $this->assertGreaterThanOrEqual(8, $replay['visited'], 'kurang 8 staff yang ke pantri');

        // Staff team pun minum (pantri bukan rotator sahaja)
        $teamIds = Agent::whereIn('custom_name', ['Aiman', 'Balqis', 'Chandra', 'Dewi', 'Evan'])->pluck('id')->all();
        $this->assertNotEmpty(array_intersect($teamIds, $replay['visitedIds']), 'tiada staff team ke pantri');
    }

    public function test_team_drink_run_has_no_work_events_while_in_pantry(): void
    {
        $this->runDemo();

        // Lepas event 'idle' pantry, event seterusnya staff yang sama mesti bukan tool_end/tool_error/needs_approval
        // (dia tak buat kerja di pantri); keluar pantri hanya melalui tool_start / turn_done / idle bilik lain / boardroom.
        $teamIds = Agent::whereIn('custom_name', ['Aiman', 'Balqis', 'Chandra', 'Dewi', 'Evan'])->pluck('id')->all();
        foreach ($teamIds as $id) {
            $prev = null;
            foreach (AgentEvent::where('agent_id', $id)->orderBy('id')->get() as $e) {
                if ($prev && $prev->department === 'pantry' && $e->department !== 'pantry') {
                    $this->assertContains($e->event, ['tool_start', 'turn_done', 'subagent_start', 'idle', 'rate_limited'], "keluar pantri dengan {$e->event}");
                }
                $prev = $e;
            }
        }
        $this->assertTrue(true);
    }

    public function test_pantry_gate_allows_two_and_team_has_priority(): void
    {
        $demo = new OfficeDemo;

        $this->assertTrue($demo->pantryTryEnter('a'));
        $this->assertTrue($demo->pantryTryEnter('a')); // dah dalam: idempoten
        $this->assertSame(1, $demo->pantryCount());
        $this->assertTrue($demo->pantryTryEnter('b'));
        $this->assertFalse($demo->pantryTryEnter('c'));
        $this->assertFalse($demo->pantryTryEnter('t', true)); // team penuh: masuk senarai tunggu
        $this->assertSame(2, $demo->pantryCount());

        $demo->pantryLeave('a');
        $this->assertFalse($demo->pantryTryEnter('c')); // slot kosong tu untuk team yang tunggu
        $this->assertTrue($demo->pantryTryEnter('t', true));
        $this->assertSame(2, $demo->pantryCount());

        $demo->pantryClear();
        $this->assertSame(0, $demo->pantryCount());
        $this->assertTrue($demo->pantryTryEnter('c'));
    }

    public function test_demo_sessions_are_never_terminated(): void
    {
        $this->runDemo();

        $this->assertSame(0, AgentEvent::where('event', 'session_end')->count());
        $this->assertSame(0, Agent::whereNotNull('ended_at')->count());
        $this->assertNotContains('ended', Agent::pluck('status')->all());
    }

    public function test_sweep_never_ends_a_demo_agent_even_after_hours_of_silence(): void
    {
        $demo = Agent::create([
            'vendor' => 'claude', 'session_id' => 'demo-aiman', 'name' => 'Claude demo1', 'label' => 'Claude Code',
            'status' => 'idle', 'department' => 'backend', 'last_event_at' => now()->subHours(5),
        ]);
        $real = Agent::create([
            'vendor' => 'claude', 'session_id' => 'real-1', 'name' => 'Claude real', 'label' => 'Claude Code',
            'status' => 'idle', 'department' => 'backend', 'last_event_at' => now()->subHours(5),
        ]);

        $this->artisan('office:sweep')->assertSuccessful();

        $this->assertNull($demo->fresh()->ended_at);
        $this->assertNotSame('ended', $demo->fresh()->status);
        $this->assertSame('playroom', $demo->fresh()->department); // tetap boleh chill
        $this->assertNotNull($real->fresh()->ended_at); // sesi sebenar masih ditamatkan
    }

    public function test_demo_alerts_do_not_notify_telegram(): void
    {
        config(['services.telegram.token' => 'abc', 'services.telegram.chat_id' => '1']);
        Http::fake();

        $this->runDemo(); // ada needs_approval/error rawak, dan rate_limited pasti (mesin kopi)

        Http::assertNothingSent();
    }
}
