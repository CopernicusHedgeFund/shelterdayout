<?php
// Shared branded email for ShelterDayOut: an HTML version (logo, friendly dog, buttons back to the site)
// plus the plain-text version, sent together as multipart/alternative so every mail app shows one of them.
// Images are hosted on shelterdayout.com; the email still reads fine with images blocked.

if (!function_exists('sdo_h')) {
function sdo_h(string $s): string { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }

function sdo_linkify(string $s): string {
    return preg_replace('~(https?://[^\s<]+[^\s<.,)])~', '<a href="$1" style="color:#2a9d8f">$1</a>', sdo_h($s));
}

/**
 * $o keys: kicker, title, intro (plain text), rows (label => value), message (plain text),
 *          buttons ([label, url, primary?]), note (plain text), footer_links ([label, url])
 */
function sdo_html_email(array $o): string {
    $site = 'https://shelterdayout.com';
    $rows = '';
    foreach (($o['rows'] ?? []) as $k => $v) {
        if ($v === '' || $v === null) { continue; }
        $val = sdo_h((string)$v);
        if (filter_var($v, FILTER_VALIDATE_EMAIL)) { $val = '<a href="mailto:' . sdo_h($v) . '" style="color:#2a9d8f">' . $val . '</a>'; }
        elseif (preg_match('/^\+?[\d\s().-]{10,}$/', (string)$v)) { $val = '<a href="tel:' . preg_replace('/[^\d+]/', '', (string)$v) . '" style="color:#2a9d8f">' . $val . '</a>'; }
        elseif (preg_match('~^https?://~', (string)$v)) { $val = '<a href="' . sdo_h($v) . '" style="color:#2a9d8f">' . $val . '</a>'; }
        $rows .= '<tr><td style="padding:9px 12px;border-bottom:1px solid #f1e6d6;color:#5c6178;font-size:13px;width:38%;vertical-align:top">' . sdo_h($k)
              . '</td><td style="padding:9px 12px;border-bottom:1px solid #f1e6d6;color:#2b2d42;font-size:15px;font-weight:600">' . $val . '</td></tr>';
    }
    $msg = '';
    if (!empty($o['message'])) {
        $msg = '<div style="margin:18px 0 0;padding:14px 16px;background:#fff8ec;border-left:4px solid #ffd166;border-radius:8px;color:#2b2d42;font-size:15px;line-height:1.5">'
             . '<div style="font-size:12px;color:#5c6178;text-transform:uppercase;letter-spacing:.06em;font-weight:700;margin-bottom:6px">Their message</div>'
             . nl2br(sdo_h($o['message'])) . '</div>';
    }
    $btns = '';
    foreach (($o['buttons'] ?? []) as $b) {
        [$label, $url, $primary] = $b + [2 => false];
        $style = $primary
            ? 'background:#ff7a59;color:#ffffff;border:2px solid #ff7a59'
            : 'background:#ffffff;color:#2a9d8f;border:2px solid #2a9d8f';
        $btns .= '<a href="' . sdo_h($url) . '" style="display:inline-block;margin:6px 8px 6px 0;padding:12px 20px;border-radius:999px;font-weight:700;font-size:15px;text-decoration:none;' . $style . '">' . sdo_h($label) . '</a>';
    }
    $links = [];
    foreach (($o['footer_links'] ?? []) as $l) { $links[] = '<a href="' . sdo_h($l[1]) . '" style="color:#ffd166;text-decoration:none">' . sdo_h($l[0]) . '</a>'; }
    $intro = nl2br(sdo_linkify($o['intro'] ?? ''));
    $note = !empty($o['note']) ? '<p style="margin:18px 0 0;color:#5c6178;font-size:13px;line-height:1.5">' . nl2br(sdo_linkify($o['note'])) . '</p>' : '';
    return '<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>' . sdo_h($o['title'] ?? 'ShelterDayOut') . '</title></head>'
    . '<body style="margin:0;padding:0;background:#fffaf2;font-family:Helvetica,Arial,sans-serif">'
    . '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fffaf2"><tr><td align="center" style="padding:24px 12px">'
    . '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#ffffff;border:2px solid #eadfce;border-radius:18px;overflow:hidden">'
    // header: logo + wordmark, linked to the site
    . '<tr><td style="padding:18px 24px;border-bottom:4px solid #ffd166"><a href="' . $site . '" style="text-decoration:none">'
    . '<img src="' . $site . '/assets/email/logo.png" width="40" height="40" alt="" style="vertical-align:middle;border:0">'
    . '<span style="vertical-align:middle;font-size:24px;font-weight:800;color:#2a9d8f;margin-left:8px">Shelter</span><span style="vertical-align:middle;font-size:24px;font-weight:800;color:#ff7a59">DayOut</span></a>'
    . '<div style="font-size:12px;color:#5c6178;margin-top:4px">' . sdo_h($o['kicker'] ?? 'Sent from ShelterDayOut.com') . '</div></td></tr>'
    // body
    . '<tr><td style="padding:24px">'
    . '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>'
    . '<td style="vertical-align:top"><h1 style="margin:0 0 10px;font-size:24px;line-height:1.25;color:#2b2d42">' . sdo_h($o['title'] ?? '') . '</h1>'
    . '<p style="margin:0;color:#2b2d42;font-size:15px;line-height:1.55">' . $intro . '</p></td>'
    . '<td width="96" style="vertical-align:top;padding-left:12px"><img src="' . $site . '/assets/email/dog.png" width="96" height="96" alt="" style="border:0;display:block"></td>'
    . '</tr></table>'
    . ($rows ? '<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:18px;border:2px solid #f1e6d6;border-radius:12px;border-collapse:separate">' . $rows . '</table>' : '')
    . $msg
    . ($btns ? '<div style="margin-top:20px">' . $btns . '</div>' : '')
    . $note
    . '</td></tr>'
    // footer
    . '<tr><td style="background:#2b2d42;color:#cfd2e0;padding:18px 24px;font-size:13px;line-height:1.6">'
    . '<b style="color:#ffffff">Lead source: <a href="' . $site . '" style="color:#ffffff">ShelterDayOut.com</a></b>, the free nationwide directory of shelter day-out, field trip and sleepover programs.<br>'
    . implode(' &nbsp;&middot;&nbsp; ', $links) . '<br>'
    . 'A free program of <a href="https://charitygood.org" style="color:#cfd2e0">Charity Good</a>. Sister site: <a href="https://shelteradoption.com" style="color:#cfd2e0">ShelterAdoption.com</a>'
    . '<br><span style="color:#9aa0b8">Charity Good, 121 South Tejon Street, Suite 900, Colorado Springs, CO 80903</span>'
    . '</td></tr></table></td></tr></table></body></html>';
}

/** Send text + HTML together. */
function sdo_mail(string $to, string $subject, string $text, string $html, string $replyTo = '', string $cc = '', string $from = 'hello@shelterdayout.com'): bool {
    $from = in_array($from, ['hello@shelterdayout.com', 'hello@shelteradoption.com'], true) ? $from : 'hello@shelterdayout.com';
    $brand = $from === 'hello@shelteradoption.com' ? 'ShelterAdoption' : 'ShelterDayOut';
    $b = 'sdo_' . bin2hex(random_bytes(8));
    $headers = ["From: $brand <$from>", 'MIME-Version: 1.0', 'Content-Type: multipart/alternative; boundary="' . $b . '"'];
    if ($replyTo !== '') { $headers[] = 'Reply-To: ' . $replyTo; }
    if ($cc !== '') { $headers[] = 'Cc: ' . $cc; }
    $body = "--$b\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
          . "--$b\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html))
          . "--$b--\r\n";
    $subject = '=?UTF-8?B?' . base64_encode(str_replace(["\r", "\n"], ' ', $subject)) . '?=';
    return @mail($to, $subject, $body, implode("\r\n", $headers), '-f' . $from);
}
}
