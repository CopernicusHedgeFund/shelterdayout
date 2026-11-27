<?php
// ShelterDayOut form handler (GoDaddy cPanel, PHP mail()).
// Handles: shelter (claim/opt-in), suggest (suggest/report), request (outing request -> shelter emails).
declare(strict_types=1);

const SITE_EMAIL = 'hello@shelterdayout.com';
const BRAND = 'ShelterDayOut';
require_once __DIR__ . '/_email.php';
// Private log folder outside the web root (created if missing).
// Keep logs outside every web root: prefer the account home (two levels above public_html/<domain>).
$PRIVATE = dirname(__DIR__, 3) . '/sdo_private';
if (!is_dir($PRIVATE) && !@mkdir($PRIVATE, 0700, true)) { $PRIVATE = dirname(__DIR__, 2) . '/sdo_private'; }

function back(string $where): void { header('Location: /' . ($where === '' ? '' : $where . '/'), true, 303); exit; }
function clean(string $k, int $max = 500): string {
    $v = isset($_POST[$k]) ? (string)$_POST[$k] : '';
    $v = str_replace(["\r", "\0"], '', $v);
    return trim(mb_substr($v, 0, $max));
}
function one_line(string $s): string { return trim(preg_replace('/[\n\t]+/', ' ', $s)); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') { back(''); }
if (clean('website') !== '') { back('thanks'); } // honeypot: silently drop bots

// Basic rate limit: 8 submissions per IP per hour.
@mkdir($PRIVATE, 0700, true);
if (!is_file($PRIVATE . '/.htaccess')) { @file_put_contents($PRIVATE . '/.htaccess', "Require all denied\n"); }
$ip = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$rlFile = $PRIVATE . '/rate_' . md5($ip) . '.json';
$now = time();
$hits = is_file($rlFile) ? (json_decode((string)file_get_contents($rlFile), true) ?: []) : [];
$hits = array_values(array_filter($hits, fn($t) => $t > $now - 3600));
if (count($hits) >= 8) { back('oops'); }
$hits[] = $now;
@file_put_contents($rlFile, json_encode($hits));

$form = clean('form', 20);
$email = clean('email', 200);
if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) { back('oops'); }
$listing = preg_replace('/[^a-z0-9-]/', '', clean('listing', 200));

$listings = json_decode((string)@file_get_contents(__DIR__ . '/listings.json'), true) ?: [];
$L = $listing && isset($listings[$listing]) ? $listings[$listing] : null;

$fields = [];
foreach (['kind','org','city','name','role','email','phone','when','confirm'] as $k) {
    $v = one_line(clean($k, 300));
    if ($v !== '') { $fields[$k] = $v; }
}
$message = clean('message', 4000);

function send(string $to, string $subject, string $body, string $replyTo = '', string $cc = ''): bool {
    $headers = [
        'From: ' . BRAND . ' <' . SITE_EMAIL . '>',
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
    ];
    if ($replyTo !== '') { $headers[] = 'Reply-To: ' . $replyTo; }
    if ($cc !== '') { $headers[] = 'Cc: ' . $cc; }
    $subject = '=?UTF-8?B?' . base64_encode(one_line($subject)) . '?=';
    return @mail($to, $subject, $body, implode("\r\n", $headers), '-f' . SITE_EMAIL);
}

function log_row(string $dir, array $row): void {
    $f = fopen($dir . '/submissions.csv', 'a');
    if ($f) { fputcsv($f, $row); fclose($f); }
}

$stamp = gmdate('Y-m-d H:i:s') . ' UTC';
$LABELS = ['kind' => 'Type of outing', 'org' => 'Organization', 'city' => 'City', 'name' => 'Name', 'role' => 'Role',
           'email' => 'Email', 'phone' => 'Phone', 'when' => 'Preferred date(s)'];
$lines = [];
foreach ($fields as $k => $v) {
    if ($k === 'confirm') { if ($form === 'request') { $lines[] = 'Confirmed: 18 or older, and understands the shelter decides whether to approve the outing'; } continue; }
    $lines[] = ($LABELS[$k] ?? ucfirst($k)) . ': ' . $v;
}
if ($L) { $lines[] = 'Listing: ' . $L['org'] . ' (' . $L['city'] . ', ' . $L['state'] . ') https://shelterdayout.com/listings/' . $listing . '/'; }
if ($message !== '') { $lines[] = "\nMessage:\n" . $message; }
$summary = implode("\n", $lines);

if ($form === 'request') {
    if (!$L || $email === '' || ($fields['name'] ?? '') === '' || ($fields['confirm'] ?? '') !== 'yes') { back('oops'); }
    if (!empty($L['noprog'])) {
        // Shelter has no program yet: queue the request for the monthly batch (send_batches.php).
        $row = ['at' => $stamp, 'listing' => $listing, 'org' => $L['org'], 'city' => $L['city'], 'state' => $L['state'],
                'name' => $fields['name'], 'email' => $email, 'phone' => $fields['phone'] ?? '', 'when' => $fields['when'] ?? '',
                'kind' => $fields['kind'] ?? '', 'message' => $message];
        $ok = (bool)@file_put_contents($PRIVATE . '/pending_requests.jsonl', json_encode($row) . "\n", FILE_APPEND | LOCK_EX);
        log_row($PRIVATE, [$stamp, 'request-queued', $listing, '', $fields['name'], $email, $fields['phone'] ?? '', $fields['when'] ?? '', $ok ? 'queued' : 'FAILED']);
        send($email, 'Your outing request for ' . $L['org'],
            "Hi " . $fields['name'] . ",\n\nThanks for asking to take a dog out from " . $L['org'] . " (" . $L['city'] . ", " . $L['state'] . ").\n\n"
            . "This shelter doesn't run a day-out program yet, so we don't forward requests one at a time. Once a month we send each shelter a note telling them how many people want to take their dogs out, with each person's name and contact details and a free guide to starting a program. If they start one, they may contact you directly.\n\n"
            . "Your request:\n" . $summary . "\n\nIn the meantime, see programs you can join now at https://shelterdayout.com/\n\n" . BRAND . " (shelterdayout.com)\nCharity Good, 121 South Tejon Street, Suite 900, Colorado Springs, CO 80903\n", SITE_EMAIL);
        back($ok ? 'thanks' : 'oops');
    }
    $to = array_values(array_filter(array_unique(array_merge(
        isset($L['email_program']) && $L['email_program'] ? [$L['email_program']] : [],
        isset($L['email_main']) && $L['email_main'] ? [$L['email_main']] : []
    )), fn($e) => filter_var($e, FILTER_VALIDATE_EMAIL)));
    if (!$to) { back('oops'); }
    $name = $fields['name'];
    $page = 'https://shelterdayout.com/listings/' . $listing . '/';
    $body = "NEW OUTING REQUEST FROM SHELTERDAYOUT.COM\n"
        . "==========================================\n\n"
        . "Hello " . $L['org'] . ",\n\n"
        . $name . " found your program on ShelterDayOut.com (https://shelterdayout.com), the free nationwide directory of shelter day-out, field trip and sleepover programs, and sent this request through your listing:\n"
        . $page . "\n\n"
        . "Reply to this email to reach " . $name . " directly. ShelterDayOut doesn't arrange outings; you decide whether to approve this request under your own rules and agreements.\n\n"
        . "----- Request sent via ShelterDayOut.com -----\n" . $summary . "\n----------------------------------------------\n\n"
        . "Lead source: ShelterDayOut.com, " . $stamp . "\n"
        . "Your listing: " . $page . "\n"
        . "Your adoption page: https://shelteradoption.com/shelters/" . $listing . "/\n"
        . "Update your listing or change where requests go: https://shelterdayout.com/for-shelters/?listing=" . $listing . "\n"
        . "Free badge for your website: https://shelterdayout.com/for-shelters/badge/?listing=" . $listing . "\n"
        . "To stop receiving requests, reply STOP.\n\n"
        . "ShelterDayOut.com - https://shelterdayout.com\n"
        . "A free program of Charity Good (charitygood.org). Sister site: ShelterAdoption.com - https://shelteradoption.com\n"
        . "Charity Good, 121 South Tejon Street, Suite 900, Colorado Springs, CO 80903\n";
    $html = sdo_html_email([
        'kicker' => 'New outing request from ShelterDayOut.com',
        'title' => $name . ' wants to take one of your animals out!',
        'intro' => $name . ' found ' . $L['org'] . "'s program on ShelterDayOut.com and sent this request through your listing. Just hit Reply to answer them directly. You decide whether to approve the outing under your own rules.",
        'rows' => ['Type of outing' => $fields['kind'] ?? '', 'Name' => $name, 'Email' => $email, 'Phone' => $fields['phone'] ?? '',
                   'Preferred date(s)' => $fields['when'] ?? '', 'Confirmed' => '18 or older; understands the shelter decides',
                   'Sent' => $stamp],
        'message' => $message,
        'buttons' => [['Reply to ' . $name, 'mailto:' . $email . '?subject=' . rawurlencode('Your outing request for ' . $L['org']), true],
                      ['View your ShelterDayOut listing', $page]],
        'note' => "Want requests to go to a different email, or need to update your program details? Update your listing at https://shelterdayout.com/for-shelters/?listing=" . $listing . ". To stop receiving requests, reply STOP.",
        'footer_links' => [['ShelterDayOut.com', 'https://shelterdayout.com'], ['Your listing', $page],
                           ['Your adoption page', 'https://shelteradoption.com/shelters/' . $listing . '/'],
                           ['Update listing', 'https://shelterdayout.com/for-shelters/?listing=' . $listing],
                           ['Free website badge', 'https://shelterdayout.com/for-shelters/badge/?listing=' . $listing]],
    ]);
    $ok = sdo_mail(implode(', ', $to), 'New outing request from ShelterDayOut.com: ' . $name, $body, $html, $name . ' <' . $email . '>', SITE_EMAIL);
    log_row($PRIVATE, [$stamp, 'request', $listing, implode(' ', $to), $name, $email, $fields['phone'] ?? '', $fields['when'] ?? '', $ok ? 'sent' : 'FAILED']);
    // Confirmation to the requester.
    send($email, 'Your outing request to ' . $L['org'],
        "Hi " . $name . ",\n\nYour outing request was sent to " . $L['org'] . " (" . $L['city'] . ", " . $L['state'] . "). The shelter will reply to you directly. Shelters are busy, so if you don't hear back in a few days, call them or use the sign-up link on their listing.\n\nYour request:\n" . $summary . "\n\nThanks for helping shelter animals!\n" . BRAND . " (shelterdayout.com)\nCharity Good, 121 South Tejon Street, Suite 900, Colorado Springs, CO 80903\n", SITE_EMAIL);
    back($ok ? 'thanks' : 'oops');
}

if ($form === 'shelter') {
    if (($fields['org'] ?? '') === '' || $email === '' || ($fields['confirm'] ?? '') !== 'yes') { back('oops'); }
    $ok = send(SITE_EMAIL, 'Shelter: ' . ($fields['kind'] ?? '') . ' - ' . ($fields['org'] ?? ''), "New For Shelters submission\n\n" . $summary . "\n\nIP: " . $ip . "\n" . $stamp, $email);
    log_row($PRIVATE, [$stamp, 'shelter', $listing, $fields['kind'] ?? '', $fields['org'] ?? '', $fields['name'] ?? '', $email, $fields['phone'] ?? '', $ok ? 'sent' : 'FAILED']);
    back($ok ? 'thanks' : 'oops');
}

if ($form === 'suggest') {
    if (($fields['city'] ?? '') === '' || $message === '') { back('oops'); }
    $ok = send(SITE_EMAIL, 'Suggestion: ' . ($fields['kind'] ?? '') . ' - ' . ($fields['org'] ?? $fields['city']), "New suggestion\n\n" . $summary . "\n\nIP: " . $ip . "\n" . $stamp, $email);
    log_row($PRIVATE, [$stamp, 'suggest', $listing, $fields['kind'] ?? '', $fields['org'] ?? '', $fields['city'] ?? '', $email, '', $ok ? 'sent' : 'FAILED']);
    back($ok ? 'thanks' : 'oops');
}

back('oops');
