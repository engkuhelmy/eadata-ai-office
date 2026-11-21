<?php

namespace Tests\Feature;

use App\Jobs\ProcessAgentEvent;
use App\Models\Agent;
use App\Office\Adapters\ClaudeCodeAdapter;
use App\Office\NormalizedEvent;
use App\Office\Notifier;
use DateTimeImmutable;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use Tests\TestCase;

class NotifierTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Cache::flush();
        config(['services.telegram.token' => 'T0KEN', 'services.telegram.chat_id' => '12345']);
        Http::fake(['api.telegram.org/*' => Http::response(['ok' => true])]);
    }

    private function run_event(string $event, string $session = 'sess-1', ?array $usage = null): void
    {
        (new ProcessAgentEvent(new NormalizedEvent(
            vendor: 'claude', agentKey: $session, name: 'Claude sess', label: 'Claude Code',
            pc: 'PC-A', project: 'webapp', event: $event, tool: 'Edit', target: 'secret/path/.env',
            department: 'backend', ts: new DateTimeImmutable('now'), usage: $usage,
        )))->handle();
    }

    public function test_sent_on_transition_to_needs_approval(): void
    {
        $this->run_event('tool_start');
        Http::assertNothingSent();

        $this->run_event('needs_approval');

        Http::assertSentCount(1);
        Http::assertSent(function ($request) {
            return $request->url() === 'https://api.telegram.org/botT0KEN/sendMessage'
                && $request['chat_id'] === '12345'
                && str_contains($request['text'], 'Claude sess')
                && str_contains($request['text'], 'claude')
                && str_contains($request['text'], 'webapp')
                && str_contains($request['text'], 'perlu approval')
                && ! str_contains($request['text'], 'secret');
        });
    }

    public function test_error_and_rate_limited_also_notify(): void
    {
        $this->run_event('tool_start', 'a');
        $this->run_event('tool_error', 'a');
        $this->run_event('tool_start', 'b');
        $this->run_event('rate_limited', 'b');

        Http::assertSentCount(2);
    }

    public function test_new_agent_starting_in_alert_status_notifies(): void
    {
        $this->run_event('needs_approval');
        Http::assertSentCount(1);
    }

    public function test_not_sent_when_unconfigured(): void
    {
        config(['services.telegram.token' => null]);
        $this->run_event('needs_approval');
        Http::assertNothingSent();

        config(['services.telegram.token' => 'T0KEN', 'services.telegram.chat_id' => '']);
        $this->run_event('tool_start', 'x');
        $this->run_event('error', 'x');
        Http::assertNothingSent();
    }

    public function test_not_repeated_when_status_unchanged_or_within_throttle(): void
    {
        $this->run_event('needs_approval');
        $this->run_event('needs_approval'); // status sama, bukan transition
        Http::assertSentCount(1);

        $this->run_event('tool_start'); // pulih
        $this->run_event('needs_approval'); // transition lagi, tapi dalam 5 minit
        Http::assertSentCount(1);

        $this->travel(6)->minutes();
        $this->run_event('tool_start');
        $this->run_event('needs_approval');
        Http::assertSentCount(2);
    }

    public function test_not_sent_for_non_alert_statuses(): void
    {
        foreach (['session_start', 'prompt', 'tool_start', 'tool_end', 'turn_done', 'idle', 'session_end'] as $event) {
            $this->run_event($event);
        }
        Http::assertNothingSent();
    }

    public function test_http_failure_never_throws(): void
    {
        Http::fake(fn () => throw new \RuntimeException('network down https://api.telegram.org/botT0KEN/'));
        Log::spy();

        $agent = Agent::create(['vendor' => 'claude', 'session_id' => 's', 'name' => 'X', 'status' => 'error']);
        Notifier::statusChanged($agent, 'active');

        Log::shouldHaveReceived('warning')->once()->withArgs(fn ($m, $ctx = []) => ! str_contains(json_encode($ctx), 'T0KEN'));
        $this->addToAssertionCount(1);
    }

    public function test_usage_replaces_totals_and_is_presented(): void
    {
        $this->run_event('turn_done', 'u', ['input' => 10, 'output' => 20, 'cache_read' => 30, 'cache_create' => 40]);
        $this->run_event('turn_done', 'u', ['input' => 15, 'output' => 25, 'cache_read' => 35, 'cache_create' => 45]);
        $this->run_event('tool_start', 'u'); // tanpa usage: jumlah kekal

        $agent = Agent::firstWhere('session_id', 'u');
        $this->assertSame([15, 25, 35, 45], [$agent->tokens_in, $agent->tokens_out, $agent->tokens_cache_read, $agent->tokens_cache_create]);

        $user = new \App\Models\User(['name' => 'v', 'email' => 'v@example.test', 'password' => 'x']);
        $user->forceFill(['role' => 'viewer'])->save();
        $this->actingAs($user)->getJson('/office/state')
            ->assertJsonPath('agents.0.usage', ['input' => 15, 'output' => 25, 'cache_read' => 35, 'cache_create' => 45]);
    }

    public function test_default_usage_is_zero_and_adapter_reads_ints_only(): void
    {
        $this->run_event('tool_start', 'z');
        $this->assertSame(0, Agent::firstWhere('session_id', 'z')->tokens_in);

        $adapter = app(ClaudeCodeAdapter::class);
        $base = ['session_id' => 's1', 'hook_event_name' => 'Stop', 'cwd' => 'C:\\proj'];

        $ok = $adapter->normalize($base + ['usage' => ['input' => 5, 'output' => 6, 'cache_read' => 7, 'cache_create' => 8]]);
        $this->assertSame(['input' => 5, 'output' => 6, 'cache_read' => 7, 'cache_create' => 8], $ok->usage);

        $mixed = $adapter->normalize($base + ['usage' => ['input' => '9', 'output' => 6, 'cache_read' => -1, 'cache_create' => 1.5]]);
        $this->assertSame(['input' => 0, 'output' => 6, 'cache_read' => 0, 'cache_create' => 0], $mixed->usage);

        $this->assertNull($adapter->normalize($base + ['usage' => ['input' => 'abc']])->usage);
        $this->assertNull($adapter->normalize($base)->usage);
        $this->assertNull($adapter->normalize($base + ['usage' => 'oops'])->usage);
    }
}
