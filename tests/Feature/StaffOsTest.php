<?php

namespace Tests\Feature;

use App\Models\Agent;
use App\Models\Device;
use App\Models\StaffMember;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\File;
use Tests\TestCase;

class StaffOsTest extends TestCase
{
    use RefreshDatabase;

    private const TOKEN = 'eod_stafftoken000000000000000000000000000000';

    private string $dir;

    protected function setUp(): void
    {
        parent::setUp();

        $this->dir = storage_path('framework/testing/staff-os-'.uniqid());
        File::ensureDirectoryExists($this->dir);
        config(['staff.path' => $this->dir]);

        File::put($this->dir.'/ZARA.md', <<<'MD'
---
name: Zara
role: Live Host Manager
unit: eAMarketplace (Shopee Live)
reports_to: Mira
fasa: 1
office_hub: { agent: zara, department: research }
---

# Zara: Live Host Manager

## 2. Skop
**Buat:**
- Susun `working_hour` setiap host tanpa clash.
- Kira fees host.

**Tak boleh buat:**
- Muktamadkan bayaran host.

## 8. Handoff
- Fees bulanan → **Mary**
- Content sesi live → **Mila**
MD);
        File::put($this->dir.'/MILA.md', <<<'MD'
---
name: Mila
role: Manager, EA Media Online
unit: EA Media Online
reports_to: Mira
team: [Ayu (Intern Research), Nia (Intern Content)]
fasa: 2
office_hub: { agent: mila, department: research }
---

## 2. Skop
**Buat:**
- Agih tugasan.

**Tak boleh buat:**
- Terbit post belum Approved.

## 8. Handoff
- Leads → **Anabell**
MD);
        File::put($this->dir.'/README.md', <<<'MD'
# Staff OS

## Peraturan wajib semua staf

- **Jangan agak.** Tanya Mira dulu.
- **Balas handoff.** SIAP atau BLOCKED.

## Format handoff (Mira → staf)

```
Kepada: <nama>
Tugasan: <apa>
```
MD);
    }

    protected function tearDown(): void
    {
        File::deleteDirectory($this->dir);
        parent::tearDown();
    }

    private function device(): void
    {
        Device::create(['name' => 'STAFF-PC', 'token_hash' => hash('sha256', self::TOKEN)]);
    }

    private function import(): void
    {
        $this->artisan('office:staff-import')->assertSuccessful();
    }

    public function test_import_creates_staff_with_scope_handoffs_and_desk(): void
    {
        $this->import();

        $zara = StaffMember::where('key', 'zara')->firstOrFail();
        $this->assertSame('Live Host Manager', $zara->role);
        $this->assertSame('sales', $zara->home_department); // placement config, bukan 'research' dalam MD
        $this->assertSame('eamarketplace', $zara->project);
        $this->assertSame(['Susun working_hour setiap host tanpa clash.', 'Kira fees host.'], $zara->scope);
        $this->assertSame(['Muktamadkan bayaran host.'], $zara->limits);
        $this->assertSame(['Fees bulanan → Mary', 'Content sesi live → Mila'], $zara->handoffs);
        $this->assertStringContainsString('# Zara: Live Host Manager', $zara->brief);

        $this->assertSame(['Ayu (Intern Research)', 'Nia (Intern Content)'], StaffMember::where('key', 'mila')->firstOrFail()->team);

        $agent = Agent::where('vendor', 'generic')->where('session_id', 'zara')->firstOrFail();
        $this->assertSame(Agent::STATUS_OFF, $agent->status);
        $this->assertNull($agent->ended_at);
        $this->assertSame('Staff OS', $agent->label);
    }

    public function test_off_staff_listed_in_state_with_profile(): void
    {
        $this->import();
        $user = new \App\Models\User(['name' => 'v', 'email' => 'v@example.test', 'password' => \Illuminate\Support\Facades\Hash::make('rahsia-kuat-123')]);
        $user->forceFill(['role' => 'viewer'])->save();
        $this->actingAs($user);

        $agents = collect($this->getJson('/office/state')->assertOk()->json('agents'));
        $zara = $agents->firstWhere('name', 'Zara');

        $this->assertSame('off', $zara['status']);
        $this->assertSame('Live Host Manager', $zara['staff']['role']);
        $this->assertSame('sales', $zara['staff']['home']);
        $this->assertNull($zara['staff']['checked_in_at']);
        $this->assertArrayNotHasKey('brief', $zara['staff']);
    }

    public function test_checkin_unknown_staff_is_404(): void
    {
        $this->device();
        $this->import();

        $this->withToken(self::TOKEN)->postJson('/api/staff/checkin', ['agent' => 'siapa'])
            ->assertStatus(404)
            ->assertJsonPath('status', 'unknown_staff');
    }

    public function test_checkin_requires_device_token(): void
    {
        $this->import();

        $this->postJson('/api/staff/checkin', ['agent' => 'zara'])->assertStatus(401);
    }

    public function test_checkin_returns_brief_and_walks_staff_to_desk(): void
    {
        $this->device();
        $this->import();

        $res = $this->withToken(self::TOKEN)->postJson('/api/staff/checkin', ['agent' => 'Zara'])
            ->assertOk()
            ->assertJsonPath('status', 'checked_in')
            ->assertJsonPath('staff.name', 'Zara')
            ->assertJsonPath('staff.reports_to', 'Mira')
            ->assertJsonPath('staff.desk.department', 'sales')
            ->assertJsonPath('scope.tak_boleh_buat.0', 'Muktamadkan bayaran host.')
            ->assertJsonPath('rules.0', 'Jangan agak. Tanya Mira dulu.')
            ->assertJsonPath('handoff_format', "Kepada: <nama>\nTugasan: <apa>");

        $this->assertStringContainsString('# Zara', $res->json('brief_markdown'));
        $this->assertNotEmpty($res->json('workflow'));

        $agent = Agent::where('vendor', 'generic')->where('session_id', 'zara')->firstOrFail();
        $this->assertSame(Agent::STATUS_ACTIVE, $agent->status);
        $this->assertSame('sales', $agent->department);
        $this->assertSame('STAFF-PC', $agent->pc);
        $this->assertNotNull(StaffMember::where('key', 'zara')->value('checked_in_at'));
    }

    public function test_inactive_staff_cannot_check_in(): void
    {
        $this->device();
        $this->import();
        StaffMember::where('key', 'zara')->update(['is_active' => false]);

        $this->withToken(self::TOKEN)->postJson('/api/staff/checkin', ['agent' => 'zara'])->assertStatus(403);
    }

    public function test_staff_tasks_go_to_desk_meetings_to_boardroom_and_session_end_is_off(): void
    {
        $this->device();
        $this->import();
        $send = fn (array $p) => $this->withToken(self::TOKEN)->postJson('/api/ingest?src=generic', $p + ['agent' => 'zara'])->assertStatus(202);
        $agent = fn () => Agent::where('vendor', 'generic')->where('session_id', 'zara')->firstOrFail();

        $send(['event' => 'tool_start', 'tool' => 'generate_report', 'target' => 'GMV harian']);
        $this->assertSame('sales', $agent()->department);
        $this->assertSame('Staff OS', $agent()->label);
        $this->assertSame('eamarketplace', $agent()->project);

        $send(['event' => 'tool_start', 'tool' => 'handoff', 'target' => 'Fees kepada Mary']);
        $this->assertSame('boardroom', $agent()->department);

        // Department eksplisit dihormati
        $send(['event' => 'tool_start', 'tool' => 'semak', 'department' => 'pantry']);
        $this->assertSame('pantry', $agent()->department);

        $send(['event' => 'needs_approval', 'tool' => 'bayaran host']);
        $this->assertSame('approval', $agent()->department);

        $send(['event' => 'session_end']);
        $this->assertSame(Agent::STATUS_OFF, $agent()->status);
        $this->assertNull($agent()->ended_at);
    }

    public function test_sweep_marks_silent_staff_off_instead_of_ended(): void
    {
        $this->import();
        $agent = Agent::where('vendor', 'generic')->where('session_id', 'zara')->firstOrFail();
        $agent->forceFill(['status' => Agent::STATUS_ACTIVE, 'department' => 'boardroom', 'last_event_at' => now()->subHours(2)])->save();

        $other = Agent::create(['vendor' => 'generic', 'session_id' => 'random-bot', 'name' => 'Bot', 'label' => 'Generic',
            'status' => Agent::STATUS_ACTIVE, 'last_event_at' => now()->subHours(2)]);

        $this->artisan('office:sweep')->assertSuccessful();

        $agent->refresh();
        $this->assertSame(Agent::STATUS_OFF, $agent->status);
        $this->assertNull($agent->ended_at);
        $this->assertSame('sales', $agent->department);
        $this->assertNotNull($other->refresh()->ended_at);
    }

    public function test_reimport_keeps_live_session_and_owner_avatar(): void
    {
        $this->device();
        $this->import();
        $this->withToken(self::TOKEN)->postJson('/api/staff/checkin', ['agent' => 'zara'])->assertOk();
        Agent::where('session_id', 'zara')->update(['avatar' => 'hiphop']);

        $this->import();

        $agent = Agent::where('vendor', 'generic')->where('session_id', 'zara')->firstOrFail();
        $this->assertSame(Agent::STATUS_ACTIVE, $agent->status);
        $this->assertSame('hiphop', $agent->avatar);
        $this->assertSame(2, StaffMember::count());
    }
}
