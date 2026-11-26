<?php
// Monthly batch for shelters without a day-out program.
// Run from cron only:  php /home/USER/public_html/shelterdayout.com/forms/send_batches.php
// Groups queued requests by shelter, emails each shelter one summary (if we know its email),
// archives what was sent, keeps the rest queued, and emails hello@ a report.
if (php_sapi_name() !== 'cli') { http_response_code(404); exit; }
const BRAND = 'ShelterDayOut';
const SITE_EMAIL = 'hello@shelterdayout.com';
require_once __DIR__ . '/_email.php';
$PRIVATE = dirname(__DIR__, 3) . '/sdo_private';
if (!is_dir($PRIVATE)) { $PRIVATE = dirname(__DIR__, 2) . '/sdo_private'; }
$queue = $PRIVATE . '/pending_requests.jsonl';
$listings = json_decode((string)@file_get_contents(__DIR__ . '/listings.json'), true) ?: [];
$optouts = array_map('strtolower', array_filter(array_map('trim', @file($PRIVATE . '/optouts.txt') ?: [])));

function send_mail(string $to, string $subject, string $body): bool {
    $h = ['From: ' . BRAND . ' <' . SITE_EMAIL . '>', 'Reply-To: ' . SITE_EMAIL, 'MIME-Version: 1.0', 'Content-Type: text/plain; charset=UTF-8'];
    return @mail($to, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, implode("\r\n", $h), '-f' . SITE_EMAIL);
}

$fh = @fopen($queue, 'c+');
if (!$fh) { exit("no queue\n"); }
flock($fh, LOCK_EX);
$rows = [];
while (($line = fgets($fh)) !== false) { $r = json_decode($line, true); if ($r) { $rows[] = $r; } }
$by = [];
foreach ($rows as $r) { $by[$r['listing']][] = $r; }

$keep = []; $sent = []; $noemail = []; $skipped = [];
foreach ($by as $slug => $reqs) {
    $L = $listings[$slug] ?? null;
    $to = [];
    if ($L) {
        foreach ([$L['email_program'] ?? '', $L['email_main'] ?? ''] as $e) {
            if ($e && filter_var($e, FILTER_VALIDATE_EMAIL) && !in_array(strtolower($e), $optouts, true)) { $to[] = $e; }
        }
    }
    $org = $reqs[0]['org'];
    if ($L && (!empty($L['email_main']) || !empty($L['email_program'])) && !$to) { $skipped[] = "$org (opted out)"; continue; }
    if (!$to) { $noemail[] = "$org, {$reqs[0]['city']} {$reqs[0]['state']}: " . count($reqs); foreach ($reqs as $r) { $keep[] = $r; } continue; }
    $n = count($reqs);
    $list = '';
    foreach ($reqs as $i => $r) {
        $list .= ($i + 1) . ". " . $r['name'] . " <" . $r['email'] . ">" . ($r['phone'] ? ", " . $r['phone'] : '')
            . ($r['kind'] ? " | " . $r['kind'] : '') . ($r['when'] ? " | " . $r['when'] : '') . "\n"
            . ($r['message'] ? "   \"" . str_replace("\n", ' ', mb_substr($r['message'], 0, 400)) . "\"\n" : '');
    }
    $page = 'https://shelterdayout.com/listings/' . $slug . '/';
    $body = "OUTING REQUESTS FROM SHELTERDAYOUT.COM\n"
        . "======================================\n\n"
        . "Hello " . $org . ",\n\n"
        . "This month, " . $n . " " . ($n === 1 ? "person" : "people") . " asked on ShelterDayOut.com (https://shelterdayout.com) to take one of your dogs out for the day, through your listing:\n"
        . $page . "\n\n"
        . "We list shelter day-out, field trip and sleepover programs nationwide. Your shelter doesn't have one that we know of, so we collect requests and send them once a month instead of one at a time. Everyone below asked us to pass their details to you, so you can contact them if you'd like.\n\n"
        . $list . "\n"
        . "Thinking about starting a program? Shelters report that dogs who go on field trips are adopted more often, and it can be simple to run. Free guides:\n"
        . "- Maddie's Fund field trip toolkit: https://www.maddiesfund.org/assets/foster-care/field-trip-pilot-program-toolkit.pdf\n"
        . "- ASPCApro on doggy day outs: https://www.aspcapro.org/node/104645\n\n"
        . "Already run a program, or want to tell us where requests should go? Reply to this email or visit https://shelterdayout.com/for-shelters/?listing=" . $slug . " and we'll update your listing.\n"
        . "To stop these monthly notes, reply STOP.\n\n"
        . "Lead source: ShelterDayOut.com\n"
        . "Your listing: " . $page . "\n"
        . "Your adoption page: https://shelteradoption.com/shelters/" . $slug . "/\n\n"
        . "ShelterDayOut.com - https://shelterdayout.com\n"
        . "A free program of Charity Good (charitygood.org). Sister site: ShelterAdoption.com - https://shelteradoption.com\n"
        . "Charity Good, 121 South Tejon Street, Suite 900, Colorado Springs, CO 80903\n";
    $people = [];
    foreach ($reqs as $i => $r) {
        $people[($i + 1) . '. ' . $r['name']] = implode(' · ', array_filter([$r['email'], $r['phone'] ?? '', $r['kind'] ?? '', $r['when'] ?? '']));
    }
    $notes = [];
    foreach ($reqs as $r) { if (!empty($r['message'])) { $notes[] = $r['name'] . ': "' . str_replace("\n", ' ', mb_substr($r['message'], 0, 400)) . '"'; } }
    $html = sdo_html_email([
        'kicker' => 'Monthly outing requests from ShelterDayOut.com',
        'title' => $n . ($n === 1 ? ' person wants' : ' people want') . ' to take your dogs out!',
        'intro' => 'This month, ' . $n . ($n === 1 ? ' person' : ' people') . ' asked on ShelterDayOut.com to take one of ' . $org . "'s dogs out for the day. We don't know of a day-out program at your shelter, so we collect requests and send them once a month. Everyone below asked us to pass their details to you, so you can contact them if you'd like.",
        'rows' => $people,
        'message' => implode("\n", $notes),
        'buttons' => [['Free field trip toolkit', 'https://www.maddiesfund.org/assets/foster-care/field-trip-pilot-program-toolkit.pdf', true],
                      ['View your ShelterDayOut listing', $page],
                      ['Tell us about your program', 'https://shelterdayout.com/for-shelters/?listing=' . $slug]],
        'note' => "Shelters report that dogs who go on field trips are adopted more often, and a program can be simple to run. ASPCApro's guide: https://www.aspcapro.org/node/104645 To stop these monthly notes, reply STOP.",
        'footer_links' => [['ShelterDayOut.com', 'https://shelterdayout.com'], ['Your listing', $page],
                           ['Your adoption page', 'https://shelteradoption.com/shelters/' . $slug . '/']],
    ]);
    $ok = sdo_mail(implode(', ', $to), $n . ($n === 1 ? ' person wants' : ' people want') . ' to take your dogs out (via ShelterDayOut.com)', $body, $html);
    if ($ok) { $sent[] = "$org: $n -> " . implode(' ', $to); foreach ($reqs as $r) { $r['sent'] = gmdate('Y-m-d'); @file_put_contents($PRIVATE . '/sent_requests.jsonl', json_encode($r) . "\n", FILE_APPEND); } }
    else { $noemail[] = "$org: send FAILED"; foreach ($reqs as $r) { $keep[] = $r; } }
}
ftruncate($fh, 0); rewind($fh);
foreach ($keep as $r) { fwrite($fh, json_encode($r) . "\n"); }
flock($fh, LOCK_UN); fclose($fh);

$report = "Monthly batch " . gmdate('Y-m-d') . "\n\nSent (" . count($sent) . "):\n" . implode("\n", $sent ?: ['none'])
    . "\n\nStill queued, need a shelter email (" . count($noemail) . "):\n" . implode("\n", $noemail ?: ['none'])
    . "\n\nOpted out (" . count($skipped) . "):\n" . implode("\n", $skipped ?: ['none']) . "\n";
if ($rows) { send_mail(SITE_EMAIL, BRAND . ' monthly batch report', $report); }
echo $report;
