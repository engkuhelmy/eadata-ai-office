<?php

namespace App\Office\Staff;

/**
 * Baca fail MD Staff OS: frontmatter (name, role, unit, reports_to, team, fasa, office_hub)
 * + seksyen "## 2. Skop" (Buat / Tak boleh buat) dan "## 8. Handoff".
 */
class StaffFileParser
{
    /** @return array{key:?string,name:?string,role:?string,unit:?string,reports_to:?string,team:list<string>,fasa:?int,department:?string,scope:list<string>,limits:list<string>,handoffs:list<string>} */
    public function parse(string $markdown): array
    {
        $markdown = str_replace("\r\n", "\n", $markdown);
        $front = [];
        $body = $markdown;

        if (preg_match('/\A---\n(.*?)\n---\n?(.*)\z/s', $markdown, $m)) {
            $body = $m[2];
            foreach (explode("\n", $m[1]) as $line) {
                if (preg_match('/^([a-z_]+):\s*(.*)$/i', trim($line), $kv)) {
                    $front[strtolower($kv[1])] = trim($kv[2]);
                }
            }
        }

        $hub = $this->inlineMap($front['office_hub'] ?? '');
        $sections = $this->sections($body);
        $skop = $this->sectionStarting($sections, '2.');

        return [
            'key' => $this->key($hub['agent'] ?? null),
            'name' => $front['name'] ?? null,
            'role' => $front['role'] ?? null,
            'unit' => $front['unit'] ?? null,
            'reports_to' => $front['reports_to'] ?? null,
            'team' => $this->inlineList($front['team'] ?? ''),
            'fasa' => isset($front['fasa']) && is_numeric($front['fasa']) ? (int) $front['fasa'] : null,
            'department' => $hub['department'] ?? null,
            'scope' => $this->bullets($this->between($skop, '**Buat:**', '**Tak boleh buat:**')),
            'limits' => $this->bullets($this->between($skop, '**Tak boleh buat:**', null)),
            'handoffs' => $this->handoffs($this->sectionStarting($sections, '8.')),
        ];
    }

    /** Senarai bullet dari seksyen README (cth. "Peraturan wajib semua staf"). */
    public function bulletsUnder(string $markdown, string $heading): array
    {
        $sections = $this->sections(str_replace("\r\n", "\n", $markdown));
        foreach ($sections as $title => $text) {
            if (stripos($title, $heading) !== false) {
                return $this->bullets($text);
            }
        }

        return [];
    }

    /** Blok kod pertama di bawah seksyen README (cth. "Format handoff"). */
    public function codeUnder(string $markdown, string $heading): ?string
    {
        $sections = $this->sections(str_replace("\r\n", "\n", $markdown));
        foreach ($sections as $title => $text) {
            if (stripos($title, $heading) !== false && preg_match('/```[a-z]*\n(.*?)\n```/s', $text, $m)) {
                return trim($m[1]);
            }
        }

        return null;
    }

    private function key(?string $agent): ?string
    {
        $key = strtolower(trim((string) $agent));

        return preg_match('/^[a-z0-9][a-z0-9_-]{0,63}$/', $key) ? $key : null;
    }

    /** "{ agent: mila, department: research }" */
    private function inlineMap(string $value): array
    {
        $out = [];
        foreach (explode(',', trim($value, "{} \t")) as $pair) {
            if (str_contains($pair, ':')) {
                [$k, $v] = array_map('trim', explode(':', $pair, 2));
                $out[strtolower($k)] = trim($v, "'\"");
            }
        }

        return $out;
    }

    /** "[Ayu (Intern Research), Nia (Intern Content)]" */
    private function inlineList(string $value): array
    {
        $value = trim($value, "[] \t");

        return $value === '' ? [] : array_values(array_filter(array_map('trim', explode(',', $value))));
    }

    /** @return array<string,string> tajuk "## ..." => isi */
    private function sections(string $body): array
    {
        $out = [];
        $parts = preg_split('/^## +/m', $body);
        foreach (array_slice($parts, 1) as $part) {
            [$title, $text] = array_pad(explode("\n", $part, 2), 2, '');
            $out[trim($title)] = $text;
        }

        return $out;
    }

    private function sectionStarting(array $sections, string $prefix): string
    {
        foreach ($sections as $title => $text) {
            if (str_starts_with($title, $prefix)) {
                return $text;
            }
        }

        return '';
    }

    private function between(string $text, string $start, ?string $end): string
    {
        $from = strpos($text, $start);
        if ($from === false) {
            return '';
        }
        $from += strlen($start);
        $to = $end !== null ? strpos($text, $end, $from) : false;

        return $to === false ? substr($text, $from) : substr($text, $from, $to - $from);
    }

    private function bullets(string $text): array
    {
        preg_match_all('/^- +(.+)$/m', $text, $m);

        return array_values(array_map([$this, 'plain'], $m[1]));
    }

    /** Bullet handoff; kalau tiada (cth. Mira), ayat biasa di luar blok kod. */
    private function handoffs(string $text): array
    {
        $bullets = $this->bullets($text);
        if ($bullets !== []) {
            return $bullets;
        }

        $plain = preg_replace('/```.*?```/s', '', $text);
        $lines = array_filter(array_map('trim', explode("\n", (string) $plain)), fn ($l) => $l !== '' && ! str_ends_with($l, ':'));

        return array_values(array_map([$this, 'plain'], $lines));
    }

    private function plain(string $text): string
    {
        return trim(str_replace(['**', '`'], '', $text));
    }
}
