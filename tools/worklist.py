"""Monthly check worklist: one line per listing, oldest-checked first, with the direct pages to open.

Usage: python3 tools/worklist.py TX OK      (states)   [--limit 200] [--json]
Each entry shows: state | org | city | checked_on | phone | email_main | events_url | programs_url | contact_url | url
Sweeps record events_url / programs_url / contact_url / checked_on on every visit, so the next monthly run
goes straight to the right pages instead of hunting through each site again.
"""
import json, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
args = [a for a in sys.argv[1:] if not a.startswith("--")]
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 0
as_json = "--json" in sys.argv
rows = []
for st in [a.upper() for a in args if not a.isdigit()]:
    f = root / "data" / "sweep" / f"{st}.json"
    if not f.exists():
        print(f"no data for {st}", file=sys.stderr); continue
    for i, r in enumerate(json.load(open(f))):
        rows.append({"state": st, "index": i, "org": r["org"], "city": r["city"],
                     "checked_on": r.get("checked_on", ""), "phone": r.get("phone", ""),
                     "email_main": r.get("email_main", ""), "events_url": r.get("events_url", ""),
                     "programs_url": r.get("programs_url", ""), "contact_url": r.get("contact_url", ""),
                     "url": r.get("url", ""), "status": r["status"],
                     "events": len(r.get("events", []))})
rows.sort(key=lambda x: (x["checked_on"] or "0000"))
if limit:
    rows = rows[:limit]
if as_json:
    print(json.dumps(rows, indent=1))
else:
    for x in rows:
        print(" | ".join(str(x[k]) for k in ("state", "org", "city", "checked_on", "phone", "email_main",
                                              "events_url", "programs_url", "contact_url", "url")))
    print(f"{len(rows)} listings", file=sys.stderr)
