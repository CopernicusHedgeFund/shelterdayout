<?php
// Share image for one page: /og.php?p=/listings/some-shelter/
// Only paths listed in assets/og.json get an image (no arbitrary text). Falls back to the site's og.png.
$cfg = ["ShelterDayOut", "shelterdayout.com", "#ff7a59"];
$p = isset($_GET['p']) ? (string)$_GET['p'] : '/';
$map = json_decode((string)@file_get_contents(__DIR__ . '/assets/og.json'), true);
$fallback = function () { header('Location: /assets/og.png', true, 302); exit; };
if (!is_array($map) || !isset($map[$p]) || !function_exists('imagettftext') || !function_exists('imagepng')) $fallback();
$title = (string)$map[$p];
$cache = sys_get_temp_dir() . '/og_' . md5($cfg[1] . '|' . $title . '|v2') . '.png';
header('Content-Type: image/png');
header('Cache-Control: public, max-age=604800');
if (is_file($cache)) { readfile($cache); exit; }

$W = 1200; $H = 630;
$im = imagecreatetruecolor($W, $H);
$hex = function ($h) use ($im) { return imagecolorallocate($im, hexdec(substr($h, 1, 2)), hexdec(substr($h, 3, 2)), hexdec(substr($h, 5, 2))); };
$bg = $hex('#fffaf2'); $ink = $hex('#2b2d42'); $muted = $hex('#5c6178'); $acc = $hex($cfg[2]); $sun = $hex('#ffd166');
imagefilledrectangle($im, 0, 0, $W, $H, $bg);
imagefilledrectangle($im, 0, 0, $W, 18, $acc);
imagefilledrectangle($im, 0, $H - 96, $W, $H, $acc);
// paw print, top right
imagefilledellipse($im, 1080, 150, 92, 80, $sun);
foreach ([[1032, 92], [1064, 72], [1098, 72], [1130, 92]] as $t) imagefilledellipse($im, $t[0], $t[1], 30, 38, $sun);
$bold = __DIR__ . '/assets/og-bold.ttf'; $reg = __DIR__ . '/assets/og-regular.ttf';
imagettftext($im, 34, 0, 72, 104, $acc, $bold, $cfg[0]);
// wrap the title to at most 4 lines, shrinking the font for long titles
$fit = function ($size) use ($title, $bold) {
    $words = preg_split('/\s+/', trim($title)); $lines = []; $cur = '';
    foreach ($words as $w) {
        $try = $cur === '' ? $w : "$cur $w";
        $bb = imagettfbbox($size, 0, $bold, $try);
        if ($bb[2] - $bb[0] > 900 && $cur !== '') { $lines[] = $cur; $cur = $w; } else $cur = $try;
    }
    if ($cur !== '') $lines[] = $cur;
    return $lines;
};
foreach ([56, 50, 44, 38, 32] as $size) { $lines = $fit($size); if (count($lines) <= 4) break; }
if (count($lines) > 4) { $lines = array_slice($lines, 0, 4); $lines[3] .= '…'; }
$lh = (int)($size * 1.32); $y = 190 + $size;
foreach ($lines as $ln) { imagettftext($im, $size, 0, 72, $y, $ink, $bold, $ln); $y += $lh; }
imagettftext($im, 26, 0, 72, $H - 36, $bg, $bold, $cfg[1]);
$tag = 'Free directory · from shelters\' own websites';
$bb = imagettfbbox(22, 0, $reg, $tag);
imagettftext($im, 22, 0, $W - 72 - ($bb[2] - $bb[0]), $H - 38, $bg, $reg, $tag);
ob_start(); imagepng($im, null, 6); $png = ob_get_clean(); imagedestroy($im);
@file_put_contents($cache, $png);
echo $png;
