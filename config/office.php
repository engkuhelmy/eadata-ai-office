<?php

return [
    // Kunci embed awam (/embed?key=...). Kosong = embed dimatikan.
    'embed_key' => env('OFFICE_EMBED_KEY', ''),
    // Laman yang dibenarkan membenamkan iframe (CSP frame-ancestors).
    'embed_origins' => env('OFFICE_EMBED_ORIGINS', 'https://kerjaai.my https://www.kerjaai.my'),
];
