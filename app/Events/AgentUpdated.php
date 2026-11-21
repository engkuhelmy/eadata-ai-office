<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Broadcasting\InteractsWithSockets;
use Illuminate\Broadcasting\PrivateChannel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcast;
use Illuminate\Foundation\Events\Dispatchable;
use Illuminate\Queue\SerializesModels;

class AgentUpdated implements ShouldBroadcast
{
    use Dispatchable, InteractsWithSockets, SerializesModels;

    /**
     * @param  array<string, mixed>  $agent  hasil OfficePresenter::agent()
     * @param  array<string, mixed>|null  $event  hasil OfficePresenter::event() untuk feed
     */
    public function __construct(public array $agent, public ?array $event = null) {}

    /** @return array<int, Channel> */
    public function broadcastOn(): array
    {
        return [new PrivateChannel('office')];
    }

    public function broadcastAs(): string
    {
        return 'agent.updated';
    }

    public function broadcastWith(): array
    {
        return ['agent' => $this->agent, 'event' => $this->event];
    }
}
