<?php
// Link checker. CLI (cron/monthly) or temporary token access. Reports links that fail or land somewhere unexpected.
$isCli = php_sapi_name() === 'cli';
if (!$isCli && ($_GET['t'] ?? '') !== '857f4eb5b853923a052754f08d068342') { http_response_code(404); exit; }
header('Content-Type: application/json');
$L = json_decode((string)@file_get_contents(__DIR__ . '/listings.json'), true) ?: [];
$only = $_GET['field'] ?? 'url';
$urls = [];
foreach ($L as $slug => $r) { if (!empty($r[$only])) { $urls[$slug] = $r[$only]; } }
$off = (int)($_GET['offset'] ?? 0); $lim = (int)($_GET['limit'] ?? 400);
$urls = array_slice($urls, $off, $lim, true);
$mh = curl_multi_init(); $hs = [];
foreach ($urls as $slug => $u) {
  $ch = curl_init($u);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_FOLLOWLOCATION => true, CURLOPT_MAXREDIRS => 8,
    CURLOPT_TIMEOUT => 25, CURLOPT_CONNECTTIMEOUT => 10, CURLOPT_SSL_VERIFYPEER => false,
    CURLOPT_USERAGENT => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 ShelterDayOut-linkcheck',
    CURLOPT_HTTPHEADER => ['Accept: text/html,*/*'], CURLOPT_ENCODING => '']);
  curl_multi_add_handle($mh, $ch); $hs[$slug] = $ch;
}
do { $st = curl_multi_exec($mh, $run); if ($run) { curl_multi_select($mh, 1.0); } } while ($run && $st == CURLM_OK);
$bad = []; $ok = 0;
foreach ($hs as $slug => $ch) {
  $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); $final = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
  $body = (string)curl_multi_getcontent($ch);
  $h1 = parse_url($urls[$slug], PHP_URL_HOST); $h2 = parse_url($final, PHP_URL_HOST);
  $strip = fn($h) => preg_replace('/^www\./', '', strtolower((string)$h));
  $notFound = preg_match('/(page not found|404 not found|page (you|you\'re) looking for (could not|can\'t|cannot) be found|doesn.t exist)/i', substr($body, 0, 20000));
  if ($code >= 400 || $code == 0 || $notFound || $strip($h1) !== $strip($h2)) {
    $bad[$slug] = ['code' => $code, 'final' => $final, 'nf' => (bool)$notFound, 'err' => curl_error($ch)];
  } else { $ok++; }
  curl_multi_remove_handle($mh, $ch);
}
echo json_encode(['checked' => count($urls), 'ok' => $ok, 'bad' => $bad], JSON_UNESCAPED_SLASHES);
