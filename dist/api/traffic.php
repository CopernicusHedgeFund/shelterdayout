<?php
// Read-only traffic summary for both sites, for Claude's cloud tasks (works with Ward's laptop off).
// Only the shelterdayout repo's traffic.yml workflow can read it: it proves itself with a GitHub identity token. Aggregates only.
require __DIR__ . '/_lib.php';
require __DIR__ . '/_gh_oidc.php';
header('Content-Type: application/json; charset=utf-8'); header('X-Robots-Tag: noindex'); header('Cache-Control: no-store');
$tok = (string)($_POST['t'] ?? '');
if ($tok === '' || strlen($tok) > 6000 || !gh_oidc_check($tok, 'shelterdayout-traffic', ['traffic.yml'])) { http_response_code(404); exit; }
@set_time_limit(120);
$SE = '/(^|\.)(google|bing|duckduckgo|yahoo|ecosia|brave|startpage|yandex|baidu|kagi|perplexity|chatgpt|openai)\./';
$out = ['generated' => gmdate('c'), 'timezone' => 'America/Denver', 'sites' => []];
foreach (['dayout' => 'shelterdayout.com', 'adopt' => 'shelteradoption.com'] as $key => $host) {
    $days = []; $pages = []; $refs = [];
    $d7 = (new DateTime('now', new DateTimeZone('America/Denver')))->modify('-6 days')->format('Y-m-d');
    foreach (['hits', 'hits_people'] as $sub) {
        foreach (glob(sdo_private() . "/$sub/$key/*.log") ?: [] as $f) {
            $d = basename($f, '.log'); if (!preg_match('/^\d{4}-\d{2}-\d{2}$/', $d)) continue;
            foreach (file($f, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
                $x = explode("\t", $line); if (count($x) < 5) continue;
                $p = $sub === 'hits' ? '' : 'p';
                $days[$d][$p . 'v'] = ($days[$d][$p . 'v'] ?? 0) + 1; $days[$d][$p . 'u'][$x[1]] = 1;
                if ($x[3] !== '' && preg_match($SE, $x[3])) $days[$d][$p . 's'] = ($days[$d][$p . 's'] ?? 0) + 1;
                if ($sub === 'hits' && $d >= $d7) { $pages[$x[2]] = ($pages[$x[2]] ?? 0) + 1; if ($x[3] !== '') $refs[$x[3]] = ($refs[$x[3]] ?? 0) + 1; }
            }
        }
    }
    ksort($days); $daily = []; $tv = $tu = $tpv = $tpu = 0;
    foreach ($days as $d => $x) {
        $u = count($x['u'] ?? []); $pu = count($x['pu'] ?? []);
        $tv += $x['v'] ?? 0; $tu += $u; $tpv += $x['pv'] ?? 0; $tpu += $pu;
        $daily[] = ['date' => $d, 'views' => $x['v'] ?? 0, 'visitors' => $u, 'search_visits' => $x['s'] ?? 0,
            'people_views' => $x['pv'] ?? 0, 'people_visitors' => $pu, 'people_search_visits' => $x['ps'] ?? 0,
            'total_views' => $tv, 'total_visitors' => $tu, 'total_people_views' => $tpv, 'total_people_visitors' => $tpu];
    }
    arsort($pages); arsort($refs);
    $out['sites'][$host] = ['daily' => $daily, 'top_pages_7d' => array_slice($pages, 0, 25, true), 'top_referrers_7d' => array_slice($refs, 0, 25, true)];
}
echo json_encode($out, JSON_UNESCAPED_SLASHES);
