"""Merge a raw shelter list (data/all_shelters_raw.json: {state_slug: ["Name | City, ST", ...]})
into data/listings.json as "No program yet" entries, skipping shelters already listed."""
import json, re
from pathlib import Path
ROOT = Path(__file__).parent
raw = json.loads((ROOT / "data" / "all_shelters_raw.json").read_text())
L = json.loads((ROOT / "data" / "listings.json").read_text())

def norm(s):
    s = s.lower().replace("&", "and")
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"\b(the|inc|of|and|city|county|animal|animals|services|service|shelter|center|centre|society|humane|spca|care|control|adoption|pet|pets|rescue|league|department|dept)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)

existing = {}
for r in L:
    existing.setdefault(r["state"], []).append((norm(r["org"]), r["city"].lower()))

added = 0; skipped = 0
for slug, items in raw.items():
    for it in items:
        m = re.match(r"^(.*)\s\|\s(.*),\s*([A-Z]{2})$", it.strip())
        if not m:
            continue
        name, city, st = m.group(1).strip(), m.group(2).strip().title(), m.group(3)
        if st not in {"DC"} and len(st) != 2:
            continue
        n = norm(name)
        dup = False
        for en, ec in existing.get(st, []):
            if n and en and (n == en or (len(n) > 4 and (n in en or en in n)) ) :
                dup = True; break
        if dup:
            skipped += 1; continue
        L.append({"state": st, "city": city, "org": name, "program": "No day-out program yet",
                  "status": "No program yet", "animals": "Dogs and cats", "offers": "",
                  "url": "", "notes": "", "checked": "November 2026", "email_program": "", "email_main": ""})
        existing.setdefault(st, []).append((n, city.lower()))
        added += 1
(ROOT / "data" / "listings.json").write_text(json.dumps(L, indent=1))
print("added", added, "skipped as already listed", skipped, "total", len(L))
