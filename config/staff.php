<?php

/*
| Staff OS: staf AI sebenar. Fail MD (satu staf satu fail + README.md) disimpan di luar git dalam
| storage/app/private/staff-os, kemudian: php artisan office:staff-import
|
| placements: meja tetap ikut jawatan dalam bangunan 4 aras (kunci DepartmentRouter::DEPARTMENTS).
| Staf tanpa placement guna department dalam fail MD kalau sah, atau head_office.
*/

return [
    'path' => env('STAFF_OS_PATH', storage_path('app/private/staff-os')),

    'label' => 'Staff OS',

    // Mesyuarat / handoff (tool task, agent, delegate_task, handoff, meeting; subagent_*)
    'meeting_department' => 'boardroom',

    'meeting_tools' => ['task', 'agent', 'delegate_task', 'handoff', 'meeting'],

    'placements' => [
        'mira' => ['home' => 'hod', 'room' => 'L3 · Head of Department', 'project' => 'shared', 'avatar' => 'exec_w'],
        'mary' => ['home' => 'cfo', 'room' => 'L3 · Pejabat CFO', 'project' => 'shared', 'avatar' => 'exec_w'],
        'hana' => ['home' => 'head_office', 'room' => 'L2 · Head Office', 'project' => 'shared', 'avatar' => 'woman'],
        'anna' => ['home' => 'head_office', 'room' => 'L2 · Head Office', 'project' => 'shared', 'avatar' => 'woman'],
        'zara' => ['home' => 'sales', 'room' => 'L2 · Sales', 'project' => 'eamarketplace', 'avatar' => 'woman'],
        'anabell' => ['home' => 'sales', 'room' => 'L2 · Sales', 'project' => 'ea-academy', 'avatar' => 'woman'],
        'mila' => ['home' => 'marketing', 'room' => 'L2 · Marketing', 'project' => 'ea-media', 'avatar' => 'woman'],
        'ayu' => ['home' => 'marketing', 'room' => 'L2 · Marketing', 'project' => 'ea-media', 'avatar' => 'genz'],
        'nia' => ['home' => 'marketing', 'room' => 'L2 · Marketing', 'project' => 'ea-media', 'avatar' => 'genz'],
        'adriana' => ['home' => 'backend', 'room' => 'L2 · IT Backend', 'project' => 'eaclouds', 'avatar' => 'woman'],
        'bill' => ['home' => 'ops', 'room' => 'L2 · IT Ops', 'project' => 'eaclouds', 'avatar' => 'default'],
        'elizabeth' => ['home' => 'training', 'room' => 'L1 · Training Room', 'project' => 'ea-academy', 'avatar' => 'woman'],
        'mas-elon' => ['home' => 'training', 'room' => 'L1 · Training Room', 'project' => 'ea-academy', 'avatar' => 'default'],
        'sam' => ['home' => 'client', 'room' => 'L1 · Client Space', 'project' => 'eaclouds', 'avatar' => 'hiphop'],
    ],

    // Langkah kerja yang dihantar balik semasa check-in (ikut README Staff OS)
    'workflow' => [
        'Check in: POST /api/staff/checkin dengan {"agent":"<key>"}. Office balas brief ini dan kamu berjalan ke meja tetap.',
        'Baca brief: jawatan, skop buat / tak boleh buat, SOP, handoff dan perkara yang perlu approval Pak Engku.',
        'Terima tugasan daripada Mira (atau ketua team) dalam format handoff: Kepada / Tugasan / Input / Output diharap / Deadline / Perlu approval.',
        'Setiap tugasan: hantar tool_start bila mula dan tool_end bila habis ke /api/ingest?src=generic (tool = nama tugasan, target = ringkasan tanpa PII).',
        'Tutup tugasan dengan SIAP + link output, atau BLOCKED + sebab. Data tak cukup: tanya Mira, jangan agak.',
        'Perlu keputusan manusia: hantar event needs_approval dan tunggu Pak Engku.',
        'Serah kerja kepada staf lain: tool handoff (ke Big Meeting Room) dan ikut senarai handoff dalam brief.',
        'Habis kerja: hantar session_end. Kamu dipaparkan Off sehingga check in semula.',
    ],
];
