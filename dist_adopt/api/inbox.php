<?php
// Inbox relay for the GitHub workflow inbox.yml (proves itself with a GitHub identity token; no stored secret).
// op=pull -> {"n": open items, "queue": <open items encrypted to the inbox task's key>, "pubkey": <this server's public key>}
// op=send -> r = replies encrypted to this server's key; sends them from hello@ and returns counts only.
require __DIR__ . '/_lib.php';
require __DIR__ . '/_gh_oidc.php';
header('Content-Type: application/json; charset=utf-8'); header('X-Robots-Tag: noindex'); header('Cache-Control: no-store');
$tok = (string)($_POST['t'] ?? '');
if ($tok === '' || strlen($tok) > 6000 || !gh_oidc_check($tok, 'shelterdayout-inbox', ['inbox.yml'])) { http_response_code(404); exit; }
require dirname(__DIR__) . '/forms/_inbox.php';
$op = (string)($_POST['op'] ?? '');
if ($op === 'pull') {
    $open = array_values(array_filter(inbox_load(), fn($x) => ($x['status'] ?? '') === 'open'));
    echo json_encode(['n' => count($open), 'h' => substr(hash('sha256', json_encode(array_column($open, 'id'))), 0, 16), 'queue' => inbox_encrypt_for_task(json_encode($open, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)), 'pubkey' => inbox_server_pub()]);
} elseif ($op === 'send') {
    $p = inbox_decrypt_from_task((string)($_POST['r'] ?? ''));
    $items = $p === null ? null : json_decode($p, true);
    if (!is_array($items)) { http_response_code(400); echo json_encode(['error' => 'could not read replies']); exit; }
    echo json_encode(inbox_apply_replies($items));
} else { http_response_code(400); echo '{}'; }
