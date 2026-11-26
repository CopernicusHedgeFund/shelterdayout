<?php
// GitHub Actions identity tokens: lets a workflow of THIS repository prove itself to the server with no stored secret.
// The workflow asks GitHub for a short-lived signed token for a named audience and posts it; the server checks GitHub's
// signature, the repository, the audience, and that the caller is one of the named workflow files on the main branch.
// Used by api/traffic.php (traffic.yml).
function gh_oidc_check(string $jwt, string $aud, array $workflows): bool {
    try { return _gh_oidc_check($jwt, $aud, $workflows); } catch (Throwable $e) { return false; }
}
function _gh_oidc_check(string $jwt, string $aud, array $workflows): bool {
    $p = explode('.', $jwt); if (count($p) !== 3) return false;
    $b64 = fn($x) => base64_decode(strtr($x, '-_', '+/') . str_repeat('=', (4 - strlen($x) % 4) % 4));
    $hd = json_decode($b64($p[0]), true); $cl = json_decode($b64($p[1]), true);
    if (!is_array($hd) || !is_array($cl) || ($hd['alg'] ?? '') !== 'RS256') return false;
    if (($cl['iss'] ?? '') !== 'https://token.actions.githubusercontent.com' || ($cl['aud'] ?? '') !== $aud) return false;
    if (($cl['repository'] ?? '') !== 'CopernicusHedgeFund/shelterdayout' || (int)($cl['exp'] ?? 0) < time() || (int)($cl['nbf'] ?? 0) > time() + 60) return false;
    $ref = (string)($cl['job_workflow_ref'] ?? ''); $okw = false;
    foreach ($workflows as $w) if ($ref === "CopernicusHedgeFund/shelterdayout/.github/workflows/$w@refs/heads/main") $okw = true;
    if (!$okw) return false;
    $cache = sdo_private() . '/gh_jwks.json';
    $load = function (bool $fresh) use ($cache) {
        if (!$fresh && is_file($cache) && filemtime($cache) > time() - 86400) return json_decode((string)file_get_contents($cache), true);
        $j = @file_get_contents('https://token.actions.githubusercontent.com/.well-known/jwks', false, stream_context_create(['http' => ['timeout' => 10]]));
        if ($j && json_decode($j, true)) { @file_put_contents($cache, $j); return json_decode($j, true); }
        return null;
    };
    $len = fn($n) => $n < 128 ? chr($n) : (($h = ltrim(pack('N', $n), "\0")) ? chr(0x80 | strlen($h)) . $h : '');
    $int = fn($x) => "\x02" . $len(strlen($x = (ord($x[0]) > 127 ? "\0" : '') . $x)) . $x;
    foreach ([false, true] as $fresh) {
        foreach (($load($fresh)['keys'] ?? []) as $k) {
            if (($k['kid'] ?? '') !== ($hd['kid'] ?? '-') || ($k['kty'] ?? '') !== 'RSA') continue;
            $seq = $int($b64($k['n'])) . $int($b64($k['e'])); $rsa = "\x30" . $len(strlen($seq)) . $seq;
            $bits = "\x03" . $len(strlen($rsa) + 1) . "\0" . $rsa;
            $alg = "\x30\x0d\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x01\x01\x05\x00";
            $der = "\x30" . $len(strlen($alg . $bits)) . $alg . $bits;
            $pem = "-----BEGIN PUBLIC KEY-----\n" . chunk_split(base64_encode($der), 64, "\n") . "-----END PUBLIC KEY-----\n";
            return openssl_verify($p[0] . '.' . $p[1], $b64($p[2]), $pem, OPENSSL_ALGO_SHA256) === 1;
        }
    }
    return false;
}
