"""Find ShelterDayOut / ShelterAdoption tracer marks in copied text.
Usage: python3 tools/find_tracer.py file [more files]   (or pipe text on stdin)
Each mark is 16 invisible characters between two word-joiners (U+2060). It encodes
an 8-hex id = sha1(site + path)[:8]; this script names the exact page or record."""
import re, sys, json, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import seo
ZW = seo._ZW
def decode(text):
    text = text.replace("\\u200b", "​").replace("\\u200c", "‌").replace("\\u200d", "‍").replace("\\u2062", "⁢").replace("\\u2060", "⁠")
    out = []
    for m in re.finditer("⁠([" + ZW + "]{16})⁠", text):
        n = 0
        for c in m.group(1):
            n = (n << 2) | ZW.index(c)
        out.append(f"{n:08x}")
    return out
def index():
    root = pathlib.Path(__file__).resolve().parent.parent
    idx = {}
    for d, site in (("dist", "SDO"), ("dist_adopt", "SA")):
        for f in (root / d).rglob("index.html"):
            rel = str(f.parent.relative_to(root / d))
            p = "/" if rel == "." else "/" + rel + "/"
            idx[seo.tracer_id(site, p)] = site + " " + p
        for k in seo.__dict__.get("STATE_CODES", []):
            pass
    for st in ["AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","PR"]:
        idx[seo.tracer_id("RPT", "/report/" + st)] = "SDO report CSV row " + st
    return idx
texts = [pathlib.Path(a).read_text(errors="ignore") for a in sys.argv[1:]] or [sys.stdin.read()]
found = [t for x in texts for t in decode(x)]
idx = index() if found else {}
for t in sorted(set(found)):
    print(t, "->", idx.get(t, "unknown"))
print(f"{len(found)} mark(s) found")
