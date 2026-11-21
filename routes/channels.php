<?php

use Illuminate\Support\Facades\Broadcast;

Broadcast::channel('App.Models.User.{id}', function ($user, $id) {
    return (int) $user->id === (int) $id;
});

// Semua user login (owner + viewer) boleh tengok office live
Broadcast::channel('office', function ($user) {
    return $user !== null;
});
