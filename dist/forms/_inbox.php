<?php
// hello@shelterdayout.com inbox automation (works with Ward's laptop off).
// Mail arrives through a cPanel forwarder "Pipe to a Program" -> forms/_inbox_mail.php -> inbox_receive().
// The server itself handles: bounces (address suppressed from the monthly batch), out-of-office (filed),
// opt-outs ("stop", "unsubscribe", "remove us" -> optouts.txt + short confirmation), and mail loops.
// Everything else is queued in sdo_private/inbox_queue.json. GitHub workflow inbox.yml fetches the queue
// ENCRYPTED to the inbox task's public key (_inbox_task_pub.pem) and stores it on the public repo's inbox-data
// branch; the scheduled inbox task decrypts it, works the items (listing fixes, claims, new shelters, questions)
// and returns replies encrypted to this server's own key, which inbox.yml posts back here to be sent from hello@.
// No email text ever reaches GitHub unencrypted.
require_once dirname(__DIR__) . '/api/_lib.php';
require_once __DIR__ . '/_email.php';

const INBOX_OWN = ['hello@shelterdayout.com', 'hello@shelteradoption.com'];

function inbox_log(string $s): void { @file_put_contents(sdo_private() . '/inbox.log', gmdate('c') . " $s\n", FILE_APPEND | LOCK_EX); }
function inbox_load(): array { $j = json_decode((string)@file_get_contents(sdo_private() . '/inbox_queue.json'), true); return is_array($j) ? $j : []; }
function inbox_save(array $q): void { @file_put_contents(sdo_private() . '/inbox_queue.json', json_encode($q, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE), LOCK_EX); }

function inbox_header(string $head, string $name): string {
    if (!preg_match('/^' . preg_quote($name, '/') . ':\s*(.*(?:\r?\n[ \t].*)*)/mi', $head, $m)) return '';
    $v = preg_replace('/\r?\n[ \t]+/', ' ', trim($m[1]));
    return function_exists('iconv_mime_decode') ? (string)@iconv_mime_decode($v, ICONV_MIME_DECODE_CONTINUE_ON_ERROR, 'UTF-8') : $v;
}
function inbox_decode(string $body, string $head): string {
    $enc = strtolower(inbox_header($head, 'Content-Transfer-Encoding'));
    if ($enc === 'base64') $body = (string)base64_decode(preg_replace('/\s+/', '', $body));
    elseif ($enc === 'quoted-printable') $body = quoted_printable_decode($body);
    if (preg_match('/charset="?([\w-]+)/i', inbox_header($head, 'Content-Type'), $c) && strtolower($c[1]) !== 'utf-8')
        $body = (string)@iconv($c[1], 'UTF-8//IGNORE', $body);
    return $body;
}
// Returns [text, html] of the first readable parts.
function inbox_parts(string $head, string $body, int $depth = 0): array {
    $ct = inbox_header($head, 'Content-Type');
    if ($depth < 5 && preg_match('/multipart\/[a-z]+;.*boundary="?([^";]+)"?/is', $ct, $b)) {
        $text = $html = '';
        foreach (preg_split('/\r?\n--' . preg_quote($b[1], '/') . '(?:--)?\r?\n?/', $body) as $part) {
            $sp = preg_split('/\r?\n\r?\n/', $part, 2); if (count($sp) < 2) continue;
            [$t, $h] = inbox_parts($sp[0], $sp[1], $depth + 1);
            if ($text === '' && $t !== '') $text = $t; if ($html === '' && $h !== '') $html = $h;
        }
        return [$text, $html];
    }
    if (stripos($ct, 'text/html') !== false) return ['', inbox_decode($body, $head)];
    if ($ct === '' || stripos($ct, 'text/plain') !== false) return [inbox_decode($body, $head), ''];
    return ['', ''];
}
function inbox_new_text(string $t): string {
    // drop quoted history: "On ... wrote:", "-----Original Message-----", "From: ... Sent:", lines starting with ">"
    $t = str_replace("\r\n", "\n", $t);
    $t = preg_split('/\n(On .{5,200}wrote:|-{2,}\s*Original Message\s*-{2,}|From: .{1,200}\n(Sent|Date): |_{10,})/i', $t)[0];
    $t = implode("\n", array_filter(explode("\n", $t), fn($l) => !preg_match('/^\s*>/', $l)));
    return trim(preg_replace("/\n{3,}/", "\n\n", $t));
}
function inbox_optout_add(string $email, string $why): void {
    $email = strtolower(trim($email)); if ($email === '' || in_array($email, INBOX_OWN, true)) return;
    $f = sdo_private() . '/optouts.txt';
    $have = array_map('strtolower', array_map('trim', @file($f) ?: []));
    if (!in_array($email, $have, true)) @file_put_contents($f, "$email\n", FILE_APPEND | LOCK_EX);
    inbox_log("optout $email ($why)");
}

function inbox_receive(string $raw): string {
    $sp = preg_split('/\r?\n\r?\n/', $raw, 2); $head = $sp[0]; $body = $sp[1] ?? '';
    $fromH = inbox_header($head, 'From'); $subject = mb_substr(inbox_header($head, 'Subject'), 0, 300);
    $from = preg_match('/<([^>]+@[^>]+)>/', $fromH, $m) ? strtolower($m[1]) : strtolower(trim(preg_replace('/^.*?([\w.+-]+@[\w.-]+).*$/s', '$1', $fromH)));
    $name = trim(preg_replace('/\s*<.*$/', '', $fromH), " \"'");
    $replyTo = inbox_header($head, 'Reply-To'); if (preg_match('/([\w.+-]+@[\w.-]+\.\w+)/', $replyTo, $r)) $from = strtolower($r[1]);
    [$text, $html] = inbox_parts($head, $body);
    if ($text === '' && $html !== '') $text = html_entity_decode(strip_tags(preg_replace('/<(br|\/p|\/div|\/tr)[^>]*>/i', "\n", $html)), ENT_QUOTES, 'UTF-8');
    $new = inbox_new_text($text);
    $auto = inbox_header($head, 'Auto-Submitted');
    // 1. loops and our own mail
    if (in_array($from, INBOX_OWN, true)) { inbox_log("ignored own mail: $subject"); return 'own'; }
    // 2. bounces: suppress the failed address
    if (preg_match('/^(mailer-daemon|postmaster|mail-daemon)@/i', $from) || preg_match('/(undeliverable|delivery status notification|mail delivery (failed|subsystem)|returned mail|delivery failure|failure notice)/i', $subject)) {
        if (preg_match_all('/(?:Final-Recipient:\s*rfc822;\s*|Original-Recipient:\s*rfc822;\s*|<)([\w.+-]+@[\w.-]+\.\w+)>?/i', $text . "\n" . $body, $mm))
            foreach (array_unique(array_map('strtolower', $mm[1])) as $bad) if (!in_array($bad, INBOX_OWN, true) && !preg_match('/^(mailer-daemon|postmaster)@/', $bad)) inbox_optout_add($bad, 'bounce');
        return 'bounce';
    }
    // 3. out-of-office / auto replies
    if (($auto !== '' && stripos($auto, 'no') !== 0) || preg_match('/^(out of (the )?office|automatic reply|auto[- ]?reply|autoreply|away from|on vacation|thank you for (your email|contacting)|we (have )?received your)/i', $subject)) {
        inbox_log("auto-reply filed: $from $subject"); return 'auto';
    }
    // 4. opt-outs (short messages only, so a real question that mentions "stop" is not swallowed)
    if (mb_strlen($new) < 400 && preg_match('/\b(unsubscribe|opt[- ]?out|stop (sending|emailing|the emails)|remove (me|us|our (shelter|email))|take (me|us) off|no more (emails|requests)|do not (email|contact))\b|^\s*stop\s*\.?\s*$/im', $new . "\n" . $subject)) {
        inbox_optout_add($from, 'asked');
        $msg = "Hi,\n\nDone. We've removed $from, so ShelterDayOut won't send you any more visitor request emails. If this was a mistake, just reply and we'll turn them back on.\n\nShelterDayOut (a free directory run by Charity Good)\nhttps://shelterdayout.com/";
        sdo_mail($from, 'Re: ' . ($subject ?: 'ShelterDayOut emails'), $msg, nl2br(sdo_h($msg)));
        return 'optout';
    }
    // 5. everything else waits for the inbox task
    $q = inbox_load();
    $id = substr(hash('sha256', $from . $subject . substr($new, 0, 500) . date('YmdH')), 0, 10);
    if (isset($q[$id])) return 'duplicate';
    $q[$id] = ['id' => $id, 'at' => gmdate('c'), 'from' => $from, 'name' => mb_substr($name, 0, 120), 'subject' => $subject,
        'text' => mb_substr($new !== '' ? $new : trim($text), 0, 8000), 'msgid' => inbox_header($head, 'Message-ID'), 'status' => 'open'];
    inbox_save($q); inbox_log("queued $id from $from: $subject");
    return "queued $id";
}

// ---- encryption between this server and the inbox task (RSA-OAEP key wrap + AES-256-CBC) ----
function inbox_server_key() {
    $f = sdo_private() . '/inbox_server_key.pem';
    if (!is_file($f)) {
        $k = openssl_pkey_new(['private_key_bits' => 3072, 'private_key_type' => OPENSSL_KEYTYPE_RSA]);
        openssl_pkey_export($k, $pem); @file_put_contents($f, $pem, LOCK_EX); @chmod($f, 0600);
    }
    return openssl_pkey_get_private((string)file_get_contents($f));
}
function inbox_server_pub(): string { return openssl_pkey_get_details(inbox_server_key())['key']; }
function inbox_encrypt_for_task(string $plain): string {
    $pub = openssl_pkey_get_public((string)file_get_contents(__DIR__ . '/_inbox_task_pub.pem'));
    $key = random_bytes(32); $iv = random_bytes(16);
    openssl_public_encrypt($key, $wk, $pub, OPENSSL_PKCS1_OAEP_PADDING);
    $ct = openssl_encrypt($plain, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv);
    return json_encode(['k' => base64_encode($wk), 'iv' => bin2hex($iv), 'd' => base64_encode($ct)]);
}
function inbox_decrypt_from_task(string $blob): ?string {
    $j = json_decode($blob, true); if (!is_array($j) || !isset($j['k'], $j['iv'], $j['d'])) return null;
    if (!openssl_private_decrypt(base64_decode($j['k']), $key, inbox_server_key(), OPENSSL_PKCS1_OAEP_PADDING)) return null;
    $p = openssl_decrypt(base64_decode($j['d']), 'aes-256-cbc', $key, OPENSSL_RAW_DATA, hex2bin($j['iv']));
    return $p === false ? null : $p;
}

// Replies from the inbox task: [{"id":"..","action":"reply|close","subject":"..","body":"..","to":"(optional, only the original sender)"}]
function inbox_apply_replies(array $items): array {
    $q = inbox_load(); $sent = $closed = $skip = 0;
    foreach ($items as $it) {
        $id = (string)($it['id'] ?? ''); if (!isset($q[$id]) || $q[$id]['status'] !== 'open') { $skip++; continue; }
        if (($it['action'] ?? '') === 'reply' && trim((string)($it['body'] ?? '')) !== '') {
            $to = $q[$id]['from'];                      // only ever the original sender
            $subj = trim((string)($it['subject'] ?? '')) ?: ('Re: ' . ($q[$id]['subject'] ?: 'Your message to ShelterDayOut'));
            $txt = (string)$it['body'];
            if (!sdo_mail($to, $subj, $txt, nl2br(sdo_h($txt)))) { $skip++; inbox_log("send failed $id"); continue; }
            $q[$id]['status'] = 'replied'; $q[$id]['done'] = gmdate('c'); $sent++; inbox_log("replied $id to $to");
        } else { $q[$id]['status'] = 'closed'; $q[$id]['done'] = gmdate('c'); $closed++; inbox_log("closed $id"); }
    }
    // keep finished items 30 days for reference, then drop them
    foreach ($q as $k => $v) if ($v['status'] !== 'open' && strtotime($v['done'] ?? $v['at']) < time() - 30 * 86400) unset($q[$k]);
    inbox_save($q);
    return ['sent' => $sent, 'closed' => $closed, 'skipped' => $skip];
}
