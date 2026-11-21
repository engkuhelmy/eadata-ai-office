<?php

namespace App\Http\Controllers;

use App\Jobs\ProcessAgentEvent;
use App\Office\AdapterRegistry;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class IngestController extends Controller
{
    public function __invoke(Request $request, AdapterRegistry $registry): JsonResponse
    {
        $src = (string) $request->query('src', '');

        if (! $registry->has($src)) {
            return response()->json(['message' => 'Unknown src.'], 422);
        }

        $eventHint = $request->query('event');

        $event = $registry->get($src)->normalize(
            $request->json()->all(),
            is_string($eventHint) && $eventHint !== '' ? $eventHint : null,
        );

        if ($event === null) {
            return response()->json(['message' => 'Payload tidak dikenali.'], 422);
        }

        ProcessAgentEvent::dispatch($event);

        return response()->json(['status' => 'accepted'], 202);
    }
}
