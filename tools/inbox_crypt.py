#!/usr/bin/env python3
"""Inbox task helper: read the encrypted hello@ queue and write encrypted replies (openssl CLI only, no extra packages).

  decrypt:  python3 tools/inbox_crypt.py decrypt <task_private.pem> <queue.enc>          -> prints the queue JSON
  encrypt:  python3 tools/inbox_crypt.py encrypt <server_pub.pem> <replies.json> <out.enc>

Format (matches src/forms/_inbox.php): {"k": base64 RSA-OAEP(SHA-1) wrapped AES key, "iv": hex, "d": base64 AES-256-CBC}.
The queue and replies only ever travel through the public repo in this encrypted form."""
import base64, json, os, subprocess, sys, tempfile


def run(args, data=None):
    return subprocess.run(args, input=data, capture_output=True, check=True).stdout


def decrypt(priv, blob):
    j = json.loads(blob)
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(base64.b64decode(j["k"])); wk = f.name
    try:
        key = run(["openssl", "pkeyutl", "-decrypt", "-inkey", priv, "-pkeyopt", "rsa_padding_mode:oaep", "-in", wk])
    finally:
        os.unlink(wk)
    return run(["openssl", "enc", "-d", "-aes-256-cbc", "-K", key.hex(), "-iv", j["iv"]], base64.b64decode(j["d"]))


def encrypt(pub, plain):
    key, iv = os.urandom(32), os.urandom(16)
    wk = run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", pub, "-pkeyopt", "rsa_padding_mode:oaep"], key)
    ct = run(["openssl", "enc", "-aes-256-cbc", "-K", key.hex(), "-iv", iv.hex()], plain)
    return json.dumps({"k": base64.b64encode(wk).decode(), "iv": iv.hex(), "d": base64.b64encode(ct).decode()})


if __name__ == "__main__":
    if sys.argv[1] == "decrypt":
        sys.stdout.write(decrypt(sys.argv[2], open(sys.argv[3]).read()).decode())
    elif sys.argv[1] == "encrypt":
        data = open(sys.argv[3], "rb").read()
        json.loads(data)  # must be valid JSON
        open(sys.argv[4], "w").write(encrypt(sys.argv[2], data))
    else:
        sys.exit(__doc__)
