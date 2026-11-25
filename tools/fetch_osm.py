"""Download US places of one OSM amenity type (animal_shelter or veterinary) from OpenStreetMap
(ODbL, (c) OpenStreetMap contributors) in a single Overpass request, fill missing city/state offline.
Usage: python tools/fetch_osm.py animal_shelter data/osm_shelters.json"""
import json, sys, time, urllib.request, urllib.parse
import reverse_geocoder as rg

amenity, outfile = sys.argv[1], sys.argv[2]
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
             "https://overpass.kumi.systems/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
UA = "ShelterDayOut/1.0 (hello@shelterdayout.com; nonprofit directory)"
STATE_CODES = {"Alabama":"AL","Alaska":"AK","Arizona":"AZ","Arkansas":"AR","California":"CA","Colorado":"CO","Connecticut":"CT","Delaware":"DE","District of Columbia":"DC","Washington, D.C.":"DC","Florida":"FL","Georgia":"GA","Hawaii":"HI","Idaho":"ID","Illinois":"IL","Indiana":"IN","Iowa":"IA","Kansas":"KS","Kentucky":"KY","Louisiana":"LA","Maine":"ME","Maryland":"MD","Massachusetts":"MA","Michigan":"MI","Minnesota":"MN","Mississippi":"MS","Missouri":"MO","Montana":"MT","Nebraska":"NE","Nevada":"NV","New Hampshire":"NH","New Jersey":"NJ","New Mexico":"NM","New York":"NY","North Carolina":"NC","North Dakota":"ND","Ohio":"OH","Oklahoma":"OK","Oregon":"OR","Pennsylvania":"PA","Rhode Island":"RI","South Carolina":"SC","South Dakota":"SD","Tennessee":"TN","Texas":"TX","Utah":"UT","Vermont":"VT","Virginia":"VA","Washington":"WA","West Virginia":"WV","Wisconsin":"WI","Wyoming":"WY"}
CODES = set(STATE_CODES.values())
q = f'[out:json][timeout:900];area["ISO3166-1"="US"][admin_level=2]->.us;nwr["amenity"="{amenity}"](area.us);out center tags;'
data = None
for attempt in range(12):
    url = ENDPOINTS[attempt % len(ENDPOINTS)]
    try:
        print("try", url, file=sys.stderr)
        req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=960) as r:
            data = json.loads(r.read().decode()); break
    except Exception as e:
        print("retry", attempt, url, e, file=sys.stderr); time.sleep(30 + 30 * attempt)
if not data:
    raise SystemExit("overpass failed")
els = [e for e in data.get("elements", []) if e.get("tags", {}).get("name")]
coords = [((e.get("lat") or e.get("center", {}).get("lat")), (e.get("lon") or e.get("center", {}).get("lon"))) for e in els]
geo = rg.search([c for c in coords if c[0] is not None], mode=1) if coords else []
gi = iter(geo)
out = []
for e, (lat, lon) in zip(els, coords):
    t = e["tags"]; g = next(gi) if lat is not None else {}
    st = (t.get("addr:state") or "").strip().upper()
    if st not in CODES:
        st = STATE_CODES.get(g.get("admin1", ""), "")
    if not st or (g and g.get("cc") not in ("US", None) and not t.get("addr:state")):
        continue
    city = (t.get("addr:city") or "").strip() or g.get("name", "")
    out.append({"state": st, "name": t["name"].strip(), "city": city,
                "street": " ".join(x for x in [t.get("addr:housenumber", ""), t.get("addr:street", "")] if x).strip(),
                "zip": t.get("addr:postcode", ""), "website": t.get("website") or t.get("contact:website") or "",
                "email": t.get("email") or t.get("contact:email") or "", "phone": t.get("phone") or t.get("contact:phone") or "",
                "hours": t.get("opening_hours", ""), "emergency": t.get("emergency", ""), "kinds": t.get("animal_shelter", ""),
                "operator": t.get("operator", ""), "operator_type": t.get("operator:type", ""), "lat": lat, "lon": lon,
                "osm": f'{e["type"]}/{e["id"]}'})
json.dump({"source": "OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)",
           "fetched": time.strftime("%Y-%m-%d"), "amenity": amenity, "places": out}, open(outfile, "w"))
print("total", len(out), file=sys.stderr)
