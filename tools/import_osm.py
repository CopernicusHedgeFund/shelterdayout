"""Merge data/osm_shelters.json into data/listings.json as 'No program yet' shelters.
Skips shelters already listed (fuzzy name match in the same state) and non-dog/cat facilities."""
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
osm = json.loads((ROOT / "data" / "osm_shelters.json").read_text())["shelters"]
L = json.loads((ROOT / "data" / "listings.json").read_text())
SKIP = re.compile(r"wildlife|raptor|equine|horse|donkey|burro|bird|avian|parrot|reptile|turtle|tortoise|rabbit|bunny|guinea pig|ferret|farm animal|goat|pig sanctuary|livestock|bat |bats$|aquarium|marine|seal|zoo|veterinar|animal hospital|clinic|grooming|boarding|kennel club|daycare|day care|pet store|petsmart|petco|thrift|resale|store|office|admin", re.I)
STOP = r"\b(the|inc|of|and|a|city|county|animal|animals|services|service|shelter|center|centre|society|humane|spca|care|control|adoption|pet|pets|rescue|league|department|dept|regional|friends|for|facility)\b"
def norm(s):
    s = s.lower().replace("&", "and"); s = re.sub(r"\(.*?\)", " ", s); s = re.sub(STOP, " ", s)
    return re.sub(r"[^a-z0-9]+", "", s)
def tidy_url(u):
    u = (u or "").strip().split(";")[0].strip()
    if u and not u.startswith("http"): u = "https://" + u
    return u
def tidy_email(e):
    e = (e or "").strip().split(";")[0].strip().lower()
    return e if re.match(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", e) else ""
existing = {}
for r in L:
    existing.setdefault(r["state"], []).append((norm(r["org"]), r["city"].lower(), r))
added = skipped = filtered = 0
for s in osm:
    name = re.sub(r"\s+", " ", s["name"]).strip()
    if SKIP.search(name) or not s.get("city"):
        filtered += 1; continue
    n = norm(name); st = s["state"]; city = s["city"].strip()
    dup = None
    for en, ec, r in existing.get(st, []):
        if n and en and (n == en or (min(len(n), len(en)) >= 5 and (n in en or en in n))):
            dup = r; break
        if not n and not en and ec == city.lower():
            dup = r; break
    if dup:
        # enrich an existing no-program entry with contact details we didn't have
        if dup["status"] == "No program yet":
            dup["url"] = dup.get("url") or tidy_url(s.get("website"))
            dup["email_main"] = dup.get("email_main") or tidy_email(s.get("email"))
        skipped += 1; continue
    row = {"state": st, "city": city, "org": name, "program": "No day-out program yet", "status": "No program yet",
           "animals": "Dogs and cats", "offers": "", "url": tidy_url(s.get("website")), "notes": "", "checked": "November 2026",
           "email_program": "", "email_main": tidy_email(s.get("email")), "phone": s.get("phone", ""),
           "source_list": "OpenStreetMap contributors (ODbL)", "osm": s.get("osm", "")}
    L.append(row); existing.setdefault(st, []).append((n, city.lower(), row)); added += 1
(ROOT / "data" / "listings.json").write_text(json.dumps(L, indent=1))
print(f"added {added}, already listed {skipped}, filtered {filtered}, total {len(L)}")
