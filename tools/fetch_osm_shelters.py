"""Download US animal shelters from OpenStreetMap (ODbL, (c) OpenStreetMap contributors) via Overpass.
Writes data/osm_shelters.json. Run by .github/workflows/osm.yml (monthly + on demand)."""
import json, math, time, urllib.request, urllib.parse, sys

STATES = "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
ENDPOINTS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
UA = "ShelterDayOut/1.0 (hello@shelterdayout.com; nonprofit shelter directory)"
SKIP_TYPES = {"wildlife", "horse", "bird", "farm_animal", "livestock", "reptile", "bat"}

def overpass(q):
    for attempt in range(6):
        url = ENDPOINTS[attempt % len(ENDPOINTS)]
        try:
            req = urllib.request.Request(url, data=urllib.parse.urlencode({"data": q}).encode(), headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            print("retry", attempt, e, file=sys.stderr); time.sleep(20 * (attempt + 1))
    raise SystemExit("overpass failed")

def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))

out = []
for st in STATES:
    area = f'area["ISO3166-2"="US-{st}"]->.a;'
    data = overpass(f'[out:json][timeout:200];{area}nwr["amenity"="animal_shelter"](area.a);out center tags;')
    places = overpass(f'[out:json][timeout:200];{area}node["place"~"^(city|town|village)$"](area.a);out;')
    pl = [(e["lat"], e["lon"], e["tags"].get("name", "")) for e in places.get("elements", []) if e.get("tags", {}).get("name")]
    n = 0
    for e in data.get("elements", []):
        t = e.get("tags", {})
        name = (t.get("name") or "").strip()
        if not name:
            continue
        kinds = {k.strip() for k in t.get("animal_shelter", "").split(";") if k.strip()}
        if kinds and kinds <= SKIP_TYPES:
            continue
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        city = t.get("addr:city", "").strip()
        if not city and lat is not None and pl:
            city = min(pl, key=lambda p: hav(lat, lon, p[0], p[1]))[2]
        out.append({"state": st, "name": name, "city": city, "website": t.get("website") or t.get("contact:website") or "",
                    "email": t.get("email") or t.get("contact:email") or "", "phone": t.get("phone") or t.get("contact:phone") or "",
                    "kinds": sorted(kinds), "operator": t.get("operator", ""), "lat": lat, "lon": lon,
                    "osm": f'{e["type"]}/{e["id"]}'})
        n += 1
    print(st, n, file=sys.stderr)
    time.sleep(5)
json.dump({"source": "OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright)",
           "fetched": time.strftime("%Y-%m-%d"), "shelters": out}, open("data/osm_shelters.json", "w"), indent=0)
print("total", len(out))
