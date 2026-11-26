<?php
// Shared helpers for the ShelterDayOut / ShelterAdoption counters. Private data lives outside every web root.
function sdo_private(): string {
    $p = dirname(__DIR__, 3) . '/sdo_private';
    if (!is_dir($p)) @mkdir($p, 0700, true);
    return $p;
}
function sdo_secret(): string {
    $f = sdo_private() . '/counter_secret.txt';
    if (!is_file($f)) @file_put_contents($f, bin2hex(random_bytes(24)), LOCK_EX);
    return (string)@file_get_contents($f);
}
function sdo_site(): string {
    $h = strtolower(preg_replace('/^www\./', '', (string)($_SERVER['HTTP_HOST'] ?? '')));
    return $h === 'shelteradoption.com' ? 'adopt' : 'dayout';
}
