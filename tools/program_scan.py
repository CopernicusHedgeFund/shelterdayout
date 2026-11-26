#!/usr/bin/env python3
"""Look for day-out style programs on the OWN websites of shelters listed as "No program yet".
Same rules as phone_fill.py: robots.txt respected, no directories/Facebook, polite per-site pacing.
Reads the listed page, the site's home page and up to 4 same-site pages whose link looks relevant
(volunteer, programs, foster, get involved, outings...). Saves every keyword hit with the sentence
around it to data/program_scan.json so each one can be checked by hand before anything is published.
It never edits the listings itself."""
import json, re, sys, glob, collections
import concurrent.futures as cf
from urllib.parse import urljoin, urlparse
from html import unescape
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phone_fill as pf

ROOT = pf.ROOT
KEY = re.compile(r"(dog(gy|s)?[- ]?(day|days)[- ]?(out|away|trips?)|day[- ]?out|field[- ]?trips?|day[- ]?trips?|day[- ]?cation|stay[- ]?cation|"
                 r"sleep[- ]?overs?|slumber part(y|ies)|hiking (buddy|buddies|partner)|trail (buddy|buddies|dogs?)|adventure (buddy|buddies|dogs?|club)|"
                 r"rent[- ]?a[- ]?(dog|pet)|borrow[- ]?a[- ]?(dog|buddy|pet)|foster[- ]for[- ]a[- ](day|weekend|night)|dog for a day|doggy date|pup(py)? date|"
                 r"walk(ing)?[- ]buddy|weekend foster|overnight foster|short[- ]term foster|pupventure|out(ing)? program|"
                 r"take a (shelter )?dog (out|for)|cat lounge|kitty lounge)", re.I)
LINK = re.compile(r"volunteer|program|foster|get[- ]?involved|ways[- ]to[- ]help|outing|field|day[- ]?out|sleepover|adventure|hik|buddy|events?|adopt", re.I)


def text_of(html):
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    return re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", body)))


def links(base, html):
    out = []
    host = urlparse(base).netloc
    for m in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        u = urljoin(base, m.group(1)); label = re.sub(r"<[^>]+>", "", m.group(2))
        if urlparse(u).netloc == host and u.startswith("http") and (LINK.search(label) or LINK.search(urlparse(u).path)):
            if not re.search(r"\.(pdf|jpe?g|png|gif|docx?|xlsx?|zip)$", u, re.I):
                out.append(u)
    return list(dict.fromkeys(out))


def scan(url):
    if not url or not url.startswith("http") or pf.BLOCK.search(url):
        return None, "no official url"
    p = urlparse(url)
    gov = bool(pf.GOV.search(p.netloc.lower().split(":")[0]))
    queue = [url] + ([] if gov else [f"{p.scheme}://{p.netloc}/"])
    seen, hits, loaded = set(), [], 0
    while queue and len(seen) < 6:
        u = queue.pop(0)
        if u in seen:
            continue
        seen.add(u)
        r = pf.get(u)
        if not r:
            continue
        loaded += 1
        final, html = r
        t = text_of(html)
        for m in KEY.finditer(t):
            s = max(0, m.start() - 220); e = min(len(t), m.end() + 220)
            hits.append({"page": final, "match": m.group(0), "text": t[s:e]})
            if len(hits) >= 12:
                break
        if len(seen) <= 2:
            for l in links(final, html):
                # on government sites stay near the animal pages
                if gov and not re.search(r"animal|shelter|pet|adopt|dog|cat", l, re.I):
                    continue
                if l not in seen:
                    queue.append(l)
    if not loaded:
        return None, "page did not load"
    # one entry per distinct sentence
    uniq, seen_t = [], set()
    for h in hits:
        k = h["text"][150:330]
        if k not in seen_t:
            seen_t.add(k); uniq.append(h)
    return uniq, "ok"


def main():
    rows = []
    for f in sorted(glob.glob(str(ROOT / "data/sweep/*.json"))):
        for r in json.loads(Path(f).read_text()):
            if (r.get("status") or "") in ("No program yet", "") or (r.get("program") or "").startswith("No day-out"):
                rows.append(r)
    print("shelters to scan:", len(rows), flush=True)
    out, why = [], collections.Counter()
    with cf.ThreadPoolExecutor(32) as ex:
        futs = {ex.submit(scan, r.get("url", "")): r for r in rows}
        for n, fu in enumerate(cf.as_completed(futs), 1):
            r = futs[fu]
            try:
                hits, w = fu.result()
            except Exception as e:
                hits, w = None, "error " + type(e).__name__
            why[w if not hits else "hits"] += 1
            if hits:
                out.append({"state": r["state"], "org": r["org"], "city": r.get("city"), "url": r.get("url"), "hits": hits})
            if n % 250 == 0:
                print(n, "done,", len(out), "with hits", flush=True)
    Path(ROOT / "out").mkdir(exist_ok=True)
    (ROOT / "out/program_scan.json").write_text(json.dumps({"summary": dict(why), "shelters": out}, indent=1, ensure_ascii=False))
    print("done:", dict(why), flush=True)


if __name__ == "__main__":
    main()
