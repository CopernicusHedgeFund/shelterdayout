#!/usr/bin/env python3
"""Check every outside link on both sites (shelter/program pages, events, guides, and the vet data files).
Writes data/linkcheck.json: {"checked": N, "bad": {url: {"code": .., "err": .., "where": [pages]}}}.
'Bad' = DNS failure, connection refused/timeout, SSL failure, or HTTP 404/410/5xx after a GET retry.
HTTP 401/403/429 and bot challenges are NOT counted as bad: those sites load fine in a browser."""
import json, re, sys, socket, ssl, concurrent.futures as cf, urllib.request, urllib.error, glob, time, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
SKIP = re.compile(r"^(mailto:|tel:|javascript:)|//(www\.)?(shelterdayout|shelteradoption)\.com|fonts\.(googleapis|gstatic)|openstreetmap\.org|geonames\.org")

where = collections.defaultdict(set)
for d in ("dist", "dist_adopt"):
    for f in (ROOT / d).rglob("*.html"):
        rel = d + "/" + str(f.relative_to(ROOT / d))
        for u in re.findall(r'href="(https?://[^"]+)"', f.read_text(errors="ignore")):
            u = u.replace("&amp;", "&")
            if not SKIP.search(u):
                where[u].add(rel)
for f in (ROOT / "dist" / "find-a-vet" / "data").glob("*.json"):
    for v in json.loads(f.read_text()):
        if v.get("w"):
            where[v["w"]].add("vets/" + f.name)
urls = sorted(where)
print("checking", len(urls), "urls", flush=True)

ctx = ssl.create_default_context()


def fetch(u, method):
    req = urllib.request.Request(u, method=method, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
        return r.status


def check(u):
    last = None
    for method in ("HEAD", "GET", "GET"):
        try:
            return u, fetch(u, method), None
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 405, 406, 429, 999):
                if method == "HEAD":
                    last = (e.code, None); continue
                return u, e.code, None          # alive, just blocks bots
            last = (e.code, None)
            if e.code in (404, 410) and method == "GET":
                return u, e.code, None
        except Exception as e:
            last = (None, type(e).__name__ + ": " + str(getattr(e, "reason", e))[:120])
        time.sleep(1)
    return u, last[0], last[1]


bad = {}
with cf.ThreadPoolExecutor(48) as ex:
    for n, (u, code, err) in enumerate(ex.map(check, urls), 1):
        ok = code is not None and (200 <= code < 400 or code in (401, 403, 405, 406, 429, 999))
        if not ok:
            bad[u] = {"code": code, "err": err, "where": sorted(where[u])[:5]}
        if n % 500 == 0:
            print(n, "done,", len(bad), "bad", flush=True)
out = {"checked": len(urls), "bad_count": len(bad), "bad": bad, "generated": time.strftime("%Y-%m-%dT%H:%MZ", time.gmtime())}
(ROOT / "data" / "linkcheck.json").write_text(json.dumps(out, indent=1, sort_keys=True))
print("checked", len(urls), "bad", len(bad))
