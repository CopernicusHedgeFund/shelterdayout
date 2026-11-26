#!/usr/local/bin/php -q
<?php
// cPanel forwarder target: hello@shelterdayout.com -> "Pipe to a Program" -> public_html/shelterdayout.com/forms/_inbox_mail.php
// Must stay executable (755). Never prints anything: any output would bounce the mail back to the sender.
if (PHP_SAPI !== 'cli') { http_response_code(404); exit; }
ob_start();
try { require __DIR__ . '/_inbox.php'; $raw = stream_get_contents(STDIN); if ($raw) inbox_receive($raw); }
catch (Throwable $e) { @file_put_contents(dirname(__DIR__, 3) . '/sdo_private/inbox_error.log', gmdate('c') . ' ' . $e->getMessage() . "\n", FILE_APPEND); }
ob_end_clean();
exit(0);
