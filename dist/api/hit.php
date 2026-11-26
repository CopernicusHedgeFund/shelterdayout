<?php
// Cookie-free visit counter (same design as AltMountain's). Stores the page, referring site, device type, browser family
// and a daily anonymous visitor code. No IP address or cookie is stored; the visitor code is a one-way hash that changes daily.
// e=0: page loaded. e=1: the visitor scrolled, clicked, touched or typed (a person, not a program) -> separate "people" log.
require __DIR__ . '/_lib.php';
header('Cache-Control: no-store'); header('X-Robots-Tag: noindex');
if ($_SERVER['REQUEST_METHOD'] !== 'POST') { http_response_code(204); exit; }
$ua = $_SERVER['HTTP_USER_AGENT'] ?? '';
if ($ua === '' || preg_match('/bot|crawl|spider|slurp|preview|headless|lighthouse|monitor|curl|wget|python|scrapy|facebookexternalhit|bingpreview/i', $ua)) { http_response_code(204); exit; }
$in = json_decode(substr((string)file_get_contents('php://input'), 0, 2000), true);
if (!is_array($in)) { http_response_code(204); exit; }
$site = sdo_site();
$path = substr(preg_replace('/[^\w\/.\-%~]/', '', parse_url((string)($in['p'] ?? '/'), PHP_URL_PATH) ?: '/'), 0, 200);
$ref = preg_replace('/^www\./', '', strtolower((string)parse_url((string)($in['r'] ?? ''), PHP_URL_HOST)));
if (in_array($ref, ['shelterdayout.com', 'shelteradoption.com'], true) && $ref === strtolower(preg_replace('/^www\./', '', (string)($_SERVER['HTTP_HOST'] ?? '')))) $ref = '';
$ref = substr(preg_replace('/[^a-z0-9.\-]/', '', $ref), 0, 80);
$dev = ((int)($in['w'] ?? 0)) > 0 && ((int)$in['w']) < 760 ? 'm' : 'd';
$tz = new DateTimeZone('America/Denver');
$day = (new DateTime('now', $tz))->format('Y-m-d');          // files by Denver day
$vid = substr(hash('sha256', $day . '|' . sdo_secret() . '|' . ($_SERVER['REMOTE_ADDR'] ?? '') . '|' . $ua), 0, 12);
$os = preg_match('/Windows/', $ua) ? 'Windows' : (preg_match('/iPhone|iPad/', $ua) ? 'iOS' : (preg_match('/Android/', $ua) ? 'Android' : (preg_match('/Macintosh/', $ua) ? 'Mac' : (preg_match('/Linux|X11/', $ua) ? 'Linux' : 'other'))));
$br = preg_match('/Edg\//', $ua) ? 'Edge' : (preg_match('/Firefox\//', $ua) ? 'Firefox' : (preg_match('/Chrome\//', $ua) ? 'Chrome' : (preg_match('/Safari\//', $ua) ? 'Safari' : 'other')));
$sub = empty($in['e']) ? 'hits' : 'hits_people';
$dir = sdo_private() . "/$sub/$site";
if (!is_dir($dir)) @mkdir($dir, 0700, true);
$t = (new DateTime('now', $tz))->format('H:i:s');
file_put_contents("$dir/$day.log", "$t\t$vid\t$path\t$ref\t$dev\t$br $os\n", FILE_APPEND | LOCK_EX);
http_response_code(204);
