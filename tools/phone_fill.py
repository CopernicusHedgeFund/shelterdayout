#!/usr/bin/env python3
"""Fill blank "phone" fields in data/sweep/*.json from each shelter's OWN website (or its government page).

Rules (same as the sweep): only the shelter's own site / gov page, never directories or Facebook;
respects robots.txt; never guesses. A number is used only when one main number clearly wins:
  - numbers in tel: links and numbers labeled phone/call/main/adoption/shelter score higher
  - numbers labeled fax are dropped
  - ties or no clear winner -> left blank
For government domains only the listed page itself is read (the county homepage number is not the shelter's).
For other domains the listed page, then the site's home and contact page are read.
Writes data/phone_fill_report.json with what was filled and why others were left blank.
Usage: python3 tools/phone_fill.py [STATE ...]"""
import json, re, sys, ssl, time, glob, collections, threading
import concurrent.futures as cf, urllib.request, urllib.error, urllib.robotparser
from urllib.parse import urljoin, urlparse
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; ShelterDayOutBot/1.0; +https://shelterdayout.com/about/)"
UA_BROWSER = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
BLOCK = re.compile(r"facebook\.com|petfinder\.com|adoptapet\.com|yelp\.com|google\.|instagram\.com|shelterluv|rescuegroups|bestfriends\.org", re.I)
GOV = re.compile(r"\.(gov|us|mil)$|\.gov\.|(^|\.)(co|city|county|town|ci)\.[a-z\-]+\.[a-z]{2}\.us$", re.I)
PH = re.compile(r"(?<![\d\-])(?:\+?1[\s.\-]?)?\(?([2-9]\d{2})\)?[\s.\-‐-–]{0,2}([2-9]\d{2})[\s.\-‐-–]{1,2}(\d{4})(?:\s*(?:ext\.?|x|extension)\s*(\d{1,5}))?(?!\d)", re.I)
GOOD = re.compile(r"phone|call|tel\b|main|adopt|shelter|office|contact|reach", re.I)
FAX = re.compile(r"fax", re.I)
BADLBL = re.compile(r"clinic|vet\b|veterinar|emergency after|dispatch|non-emergency|police|sheriff|licens|donat|volunteer coord|lost.?pet hotline", re.I)
ctx = ssl.create_default_context()
_robots, _rlock, _hostlock = {}, threading.Lock(), collections.defaultdict(threading.Lock)


def allowed(u):
    p = urlparse(u); base = f"{p.scheme}://{p.netloc}"
    with _rlock:
        rp = _robots.get(base)
    if rp is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                rp.parse(r.read(200000).decode("utf-8", "ignore").splitlines())
        except Exception:
            rp.parse([])            # no robots.txt -> allowed
        with _rlock:
            _robots[base] = rp
    return rp.can_fetch(UA, u) and rp.can_fetch("*", u)


_why = threading.local()


def get(u):
    _why.last = "page did not load"
    if BLOCK.search(u):
        return None
    if not allowed(u):
        _why.last = "robots.txt says no"
        return None
    with _hostlock[urlparse(u).netloc]:     # one request at a time per site, with a pause
        for ua in (UA_BROWSER,):
            try:
                req = urllib.request.Request(u, headers={"User-Agent": ua, "Accept": "text/html,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"})
                with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                    if "html" not in (r.headers.get("Content-Type") or "html"):
                        return None
                    html = r.read(3_000_000).decode(r.headers.get_content_charset() or "utf-8", "ignore")
                    time.sleep(1)
                    return r.geturl(), html
            except urllib.error.HTTPError as e:
                _why.last = f"page did not load (HTTP {e.code})"
                time.sleep(1)
            except Exception as e:
                _why.last = f"page did not load ({type(e).__name__})"
                time.sleep(1)
    return None


def fmt(a, b, c, x=None):
    s = f"({a}) {b}-{c}"
    return s + (f" ext. {x}" if x else "")


def candidates(html):
    sc = collections.Counter(); labels = {}
    for m in re.finditer(r'href=["\']tel:([^"\']+)["\']', html, re.I):
        mm = PH.search(unescape(m.group(1)).replace("%20", " "))
        if mm:
            k = fmt(*mm.groups()[:3])
            sc[k] += 3
            if not mm.group(4):
                labels[k] = None
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = unescape(re.sub(r"(?s)<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text)
    prev_end = 0
    for m in PH.finditer(text):
        k = fmt(*m.groups()[:3]); ext = m.group(4)
        before = text[max(prev_end, m.start() - 30):m.start()]   # label = text since the previous number
        after = text[m.end():m.end() + 8]
        prev_end = m.end()
        if FAX.search(before[-10:]) or re.match(r"\s*(\(fax|[-\u2013]\s*fax)", after, re.I):
            sc[k] -= 100; continue
        if BADLBL.search(before):
            sc[k] -= 2; continue
        sc[k] += 1 + (2 if GOOD.search(before) else 0)
        if ext and GOOD.search(before):
            labels.setdefault(k, ext)
        elif not ext:
            labels[k] = None          # also listed without an extension -> use the plain number
    return sc, labels


def pick(sc):
    good = [(v, k) for k, v in sc.items() if v >= 2]
    good.sort(reverse=True)
    if not good:
        return None, "no clear number"
    if len(good) > 1 and good[0][0] < good[1][0] * 2:
        return None, "several numbers, none clearly main: " + ", ".join(k for _, k in good[:3])
    return good[0][1], "ok"


def contact_link(base_url, html):
    for m in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        if re.search(r"contact|visit us|location|hours", re.sub(r"<[^>]+>", "", m.group(2)), re.I):
            u = urljoin(base_url, m.group(1))
            if urlparse(u).netloc == urlparse(base_url).netloc:
                return u
    return None


_sitewide, _swlock = {}, threading.Lock()
ANIMAL = re.compile(r"animal|shelter|adopt|pet|humane|spca|kennel", re.I)


def sitewide_numbers(final_url):
    """Numbers printed on a government site's homepage (header/footer switchboards) - not the shelter's line."""
    home = f"{urlparse(final_url).scheme}://{urlparse(final_url).netloc}/"
    with _swlock:
        if home in _sitewide:
            return _sitewide[home]
    r = get(home)
    nums = set(candidates(r[1])[0]) if r else set()
    with _swlock:
        _sitewide[home] = nums
    return nums


def animal_labeled(html):
    """Numbers whose label (text just before) mentions animals/shelter/adoption."""
    body = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"\s+", " ", unescape(re.sub(r"(?s)<[^>]+>", " ", body)))
    out, prev = set(), 0
    for m in PH.finditer(text):
        if ANIMAL.search(text[max(prev, m.start() - 40):m.start()]):
            out.add(fmt(*m.groups()[:3]))
        prev = m.end()
    return out


def find_phone(url):
    if not url or not url.startswith("http") or BLOCK.search(url):
        return None, "no official url"
    host = urlparse(url).netloc.lower()
    gov = bool(GOV.search(host.split(":")[0]))
    pages, seen = [url], set()
    total = collections.Counter(); labels = {}; why = "page did not load"; first_fail = None
    while pages and len(seen) < 3:
        u = pages.pop(0)
        if u in seen:
            continue
        seen.add(u)
        r = get(u)
        if not r:
            if len(seen) == 1:
                first_fail = _why.last
            continue
        final, html = r
        sc, lb = candidates(html)
        labels.update(lb)
        if gov:
            sw = sitewide_numbers(final) - animal_labeled(html)
            for k in list(sc):
                if k in sw:
                    sc[k] = 0
        num, why = pick(sc)
        if num:
            return fmt(*re.match(r"\((\d+)\) (\d+)-(\d+)", num).groups(), labels.get(num)), "ok: " + u
        total.update(sc)
        if gov:
            break                     # never climb to a county/city homepage
        if len(seen) == 1:
            home = f"{urlparse(final).scheme}://{urlparse(final).netloc}/"
            c = contact_link(final, html)
            pages += [x for x in (c, home) if x]
        elif len(seen) == 2 and len(pages) == 0:
            c = contact_link(final, html)
            if c:
                pages.append(c)
    num, why2 = pick(total)
    if num and why != "page did not load":
        return fmt(*re.match(r"\((\d+)\) (\d+)-(\d+)", num).groups(), labels.get(num)), "ok (combined pages): " + url
    return None, why2 if why != "page did not load" else (first_fail or why)


def main():
    args = sys.argv[1:]
    recheck = "--recheck-gov" in args
    states = [a.upper() for a in args if not a.startswith("--")]
    redo = set()
    if recheck:
        old = json.loads((ROOT / "data/phone_fill_report.json").read_text())
        for x in old["filled"]:
            u = x["from"].split(": ", 1)[-1]
            if GOV.search(urlparse(u).netloc.lower().split(":")[0]):
                redo.add((x["state"], x["org"], x["phone"]))
    files = sorted(glob.glob(str(ROOT / "data/sweep/*.json")))
    if states:
        files = [f for f in files if Path(f).stem in states]
    jobs = []
    data = {}
    for f in files:
        rows = json.loads(Path(f).read_text())
        data[f] = rows
        for i, r in enumerate(rows):
            if (Path(f).stem, r.get("org"), r.get("phone")) in redo:
                r["phone"] = ""
            if not (r.get("phone") or "").strip():
                jobs.append((f, i, r.get("url", "")))
    print("blank phones:", len(jobs), flush=True)
    report = {"filled": [], "blank": collections.Counter(), "blank_detail": []}
    with cf.ThreadPoolExecutor(24) as ex:
        futs = {ex.submit(find_phone, u): (f, i, u) for f, i, u in jobs}
        for n, fu in enumerate(cf.as_completed(futs), 1):
            f, i, u = futs[fu]
            try:
                num, why = fu.result()
            except Exception as e:
                num, why = None, "error " + type(e).__name__
            r = data[f][i]
            if num:
                r["phone"] = num
                report["filled"].append({"state": Path(f).stem, "org": r.get("org"), "phone": num, "from": why})
            else:
                key = why.split(":")[0].split(" (")[0]
                report["blank"][key] += 1
                report["blank_detail"].append({"state": Path(f).stem, "org": r.get("org"), "url": u, "why": why})
            if n % 200 == 0:
                print(n, "done,", len(report["filled"]), "filled", flush=True)
    report["blank"] = dict(report["blank"])
    # a number filled here that is also on a DIFFERENT organisation's listing is a shared switchboard: drop it
    allrows = [(f, r) for f in data for r in data[f]]
    owners = collections.defaultdict(set)
    for f, r in allrows:
        if r.get("phone"):
            owners[r["phone"]].add((urlparse(r.get("url") or "").netloc.lower().removeprefix("www."),
                                    (re.findall(r"[a-z]+", (r.get("org") or "").lower().removeprefix("the ")) or [""])[0]))
    new = {(x["state"], x["org"]) for x in report["filled"]}
    dropped = 0
    for f, r in allrows:
        if (Path(f).stem, r.get("org")) in new and len(owners.get(r.get("phone"), ())) > 1:
            report["blank_detail"].append({"state": Path(f).stem, "org": r.get("org"), "url": r.get("url"), "why": "shared number " + r["phone"]})
            report["blank"]["shared number"] = report["blank"].get("shared number", 0) + 1
            r["phone"] = ""; dropped += 1
    report["filled"] = [x for x in report["filled"] if any(Path(f).stem == x["state"] and r.get("org") == x["org"] and r.get("phone") for f, r in allrows)]
    print("dropped shared numbers:", dropped, flush=True)
    for f, rows in data.items():
        Path(f).write_text(json.dumps(rows, indent=1, ensure_ascii=False))
    per = collections.Counter(x["state"] for x in report["filled"])
    report["per_state"] = dict(sorted(per.items()))
    (ROOT / "data/phone_fill_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
    print("filled", len(report["filled"]), "of", len(jobs), "| blank reasons", report["blank"], flush=True)


if __name__ == "__main__":
    main()
