"""SEO extras shared by both sites: share images, website badges, the national report and the monthly
"new programs" pages. Called from build.py and build_adopt.py."""
import csv
import io
import json
import shutil
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HISTORY = ROOT / "data" / "program_history.json"


# ---------- share images ----------
def og_title(title, brand):
    t = title.rsplit(" | ", 1)[0] if title.endswith(brand) else title
    return t.strip()


def write_og(dist, ogmap, brand, domain, accent):
    (dist / "assets").mkdir(parents=True, exist_ok=True)
    shutil.copy(ROOT / "src" / "og" / "DejaVuSans-Bold.ttf", dist / "assets" / "og-bold.ttf")
    shutil.copy(ROOT / "src" / "og" / "DejaVuSans.ttf", dist / "assets" / "og-regular.ttf")
    (dist / "assets" / "og.json").write_text(json.dumps(ogmap, separators=(",", ":"), sort_keys=True))
    php = (ROOT / "src" / "og" / "og.php").read_text()
    php = php.replace("'__BRAND__'", json.dumps(brand)).replace("'__DOMAIN__'", json.dumps(domain)).replace("'__ACCENT__'", json.dumps(accent))
    (dist / "og.php").write_text(php)
    (dist / "BingSiteAuth.xml").write_text(BING_AUTH)


# ---------- website badge ----------
def badge_svg(line1, line2, accent):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="240" height="64" viewBox="0 0 240 64" role="img" aria-label="{line1} {line2}">
<rect width="240" height="64" rx="14" fill="{accent}"/>
<g fill="#ffd166"><ellipse cx="34" cy="38" rx="11" ry="9.5"/><ellipse cx="22" cy="25" rx="4.2" ry="5.4"/><ellipse cx="30" cy="20" rx="4.2" ry="5.4"/><ellipse cx="39" cy="20" rx="4.2" ry="5.4"/><ellipse cx="47" cy="25" rx="4.2" ry="5.4"/></g>
<text x="62" y="27" font-family="Verdana,Arial,Helvetica,sans-serif" font-size="12" fill="#fff">{line1}</text>
<text x="62" y="47" font-family="Verdana,Arial,Helvetica,sans-serif" font-size="19" font-weight="bold" fill="#fff">{line2}</text>
</svg>
"""


def build_badge_page(m, path, crumbs, listing_prefix, line1, line2, accent, h1, intro):
    """m = the site module (needs SITE, BRAND, DIST, page, write, esc, crumbs_ld or similar)."""
    (m.DIST / "assets").mkdir(parents=True, exist_ok=True)
    (m.DIST / "assets" / "badge.svg").write_text(badge_svg(line1, line2, accent))
    site = m.SITE
    js = """<script>(function(){var q=new URLSearchParams(location.search).get('listing')||'';q=/^[a-z0-9-]{2,120}$/.test(q)?q:'';
var u='SITE'+(q?'PREFIX'+q+'/':'/');var code='<a href="'+u+'"><img src="SITE/assets/badge.svg" alt="ALT" width="240" height="64"></a>';
var t=document.getElementById('bcode');t.value=code;document.getElementById('blink').href=u;
document.getElementById('bcopy').addEventListener('click',function(){t.select();try{navigator.clipboard.writeText(t.value)}catch(e){document.execCommand('copy')}this.textContent='Copied';});
if(!q)document.getElementById('bnote').style.display='';})();</script>""".replace("SITE", site).replace("PREFIX", listing_prefix).replace("ALT", f"{line1} {line2}")
    body = f"""<div class="crumbs">{crumbs}</div>
<h1>{m.esc(h1)}</h1>
<p class="lede">{intro}</p>
<p><a id="blink" href="{site}/"><img src="/assets/badge.svg" alt="{line1} {line2}" width="240" height="64"></a></p>
<h2>Copy this code</h2>
<p>Paste it anywhere on your website: your adoption page, footer or volunteer page. It links straight to your listing.</p>
<p id="bnote" class="animal" style="display:none">Tip: open this page from your listing (the badge link at the bottom) and the code will link to your own listing instead of our home page.</p>
<textarea id="bcode" rows="4" style="width:100%;font-family:monospace;font-size:14px" readonly></textarea>
<p><button id="bcopy" class="btn" type="button">Copy code</button></p>
<h2>Questions</h2>
<p>The badge is free and optional, and there's nothing to sign up for. Need a different size, or want to update your listing? Email <a href="mailto:{m.CONTACT}">{m.CONTACT}</a>.</p>
{js}"""
    m.write(path, m.page(f"Free Website Badge for Shelters | {m.BRAND}", f"A free {m.BRAND} badge for your shelter's website that links to your listing. Copy and paste the code.", body, path))


# ---------- program history + monthly new-programs pages (ShelterDayOut) ----------
def program_history(progs):
    try:
        h = json.loads(HISTORY.read_text()) if HISTORY.exists() else {}
    except Exception:
        h = {}
    month = date.today().strftime("%Y-%m")
    new = {r["slug"]: month for r in progs if r["slug"] not in h}
    if new:
        h.update(new)
        HISTORY.write_text(json.dumps(dict(sorted(h.items())), indent=0) + "\n")
    return h


def month_name(m):
    return datetime.strptime(m, "%Y-%m").strftime("%B %Y")


def build_new_programs(m, progs):
    h = program_history(progs)
    by = {}
    for r in progs:
        by.setdefault(h.get(r["slug"], date.today().strftime("%Y-%m")), []).append(r)
    months = sorted(by, reverse=True)
    first = min(h.values()) if h else date.today().strftime("%Y-%m")

    def items(rs):
        rs = sorted(rs, key=lambda r: (r["state_name"], r["city"], r["org"]))
        out, cur = "", None
        for r in rs:
            if r["state_name"] != cur:
                out += ("</ul>" if cur else "") + f'<h3>{m.esc(r["state_name"])}</h3><ul class="evlist">'
                cur = r["state_name"]
            out += (f'<li><a href="/listings/{r["slug"]}/">{m.esc(r["program"] or "Day-out program")}</a> at {m.esc(r["org"])} '
                    f'({m.esc(r["city"])}, {r["state"]}){(" · " + m.esc(r["offers"])) if r.get("offers") else ""}</li>')
        return out + ("</ul>" if cur else "")

    def note(mo):
        return (f'<p class="animal">{month_name(first)} is when we started keeping this list, so it includes every program in the directory at that time.</p>'
                if mo == first else "")

    arch = "".join(f'<li><a href="/new-programs/{mo}/">{month_name(mo)}</a>: {len(by[mo]):,} program{"s" if len(by[mo]) != 1 else ""}</li>' for mo in months)
    for mo in months:
        n = len(by[mo])
        p = f"/new-programs/{mo}/"
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/new-programs/">New programs</a> / {month_name(mo)}</div>
<h1>New shelter dog day-out programs: {month_name(mo)}</h1>
<p class="lede">{n:,} shelter day-out, field trip, sleepover and hiking program{"s" if n != 1 else ""} added to {m.BRAND} in {month_name(mo)}, by state. Each one comes from the shelter's own website.</p>
{note(mo)}
{items(by[mo])}
<p>See <a href="/new-programs/">all months</a> or the <a href="/report/">national report</a>.</p>"""
        m.write(p, m.page(f"New Shelter Dog Day-Out Programs, {month_name(mo)}: {n:,} Added | {m.BRAND}",
            f"{n:,} new shelter dog day-out, field trip and sleepover programs added in {month_name(mo)}, listed by state.",
            body, p, m.crumbs_ld([("Home", "/"), ("New programs", "/new-programs/"), (month_name(mo), p)])))
    latest = months[0] if months else None
    body = f"""<div class="crumbs"><a href="/">Home</a> / New programs</div>
<h1>New shelter dog day-out programs</h1>
<p class="lede">Every month we check shelters' own websites for new dog day-out, field trip, sleepover and hiking programs. Here's what we've added, newest first.</p>
<h2>By month</h2><ul>{arch}</ul>
{f"<h2>Added in {month_name(latest)}</h2>{note(latest)}{items(by[latest])}" if latest else ""}
<p>Run a program we're missing? <a href="/suggest/">Tell us</a> and we'll add it.</p>"""
    m.write("/new-programs/", m.page(f"New Shelter Dog Day-Out Programs by Month | {m.BRAND}",
        "New shelter dog day-out, field trip, sleepover and hiking programs added each month, from shelters' own websites.",
        body, "/new-programs/", m.crumbs_ld([("Home", "/"), ("New programs", "/new-programs/")])))
    return months


# ---------- national report (ShelterDayOut) ----------
TYPE_NAMES = [("day", "Day trips and outings"), ("sleep", "Sleepovers and short-term fosters"), ("hike", "Hikes, walks and runs"), ("visit", "Visits, lounges and cafés")]


def pct(a, b):
    return f"{a / b * 100:.2f}%" if b else "0.00%"


def build_report(m, rows):
    NOPROG = m.NOPROG
    progs = [r for r in rows if r["status"] != NOPROG]
    month = month_name(date.today().strftime("%Y-%m"))
    st = {}
    for r in rows:
        s = st.setdefault(r["state"], {"shelters": 0, "programs": 0, "open": 0, "vol": 0})
        s["shelters"] += 1
        if r["status"] != NOPROG:
            s["programs"] += 1
            s["open"] += r["status"] == "Open to public"
            s["vol"] += r["status"] == "Volunteers only"
    status = {}
    for r in progs:
        status[r["status"]] = status.get(r["status"], 0) + 1
    types = {k: sum(1 for r in progs if k in (r.get("types") or [])) for k, _ in TYPE_NAMES}
    cats = sum(1 for r in progs if "cat" in (r.get("animals") or "").lower())
    n_states = sum(1 for s in st.values() if s["programs"])
    # CSV
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["state", "state_name", "shelters_listed", "day_out_programs", "open_to_public", "volunteers_only", "share_with_program"])
    for k in sorted(st, key=lambda k: m.STATES[k]):
        s = st[k]
        w.writerow([k, m.STATES[k], s["shelters"], s["programs"], s["open"], s["vol"], pct(s["programs"], s["shelters"])])
    (m.DIST / "report").mkdir(parents=True, exist_ok=True)
    (m.DIST / "report" / "programs-by-state.csv").write_text(buf.getvalue())
    trs = "".join(f'<tr><td><a href="/states/{m.slugify(m.STATES[k])}/">{m.STATES[k]}</a></td><td>{s["shelters"]:,}</td><td>{s["programs"]:,}</td><td>{s["open"]:,}</td><td>{pct(s["programs"], s["shelters"])}</td></tr>'
                  for k, s in sorted(st.items(), key=lambda kv: (-kv[1]["programs"], m.STATES[kv[0]])))
    stat_li = "".join(f"<li><b>{status[k]:,}</b> {k.lower()}</li>" for k in ["Open to public", "Volunteers only", "Needs check", "Paused"] if status.get(k))
    type_li = "".join(f"<li><b>{types[k]:,}</b> {nm.lower()} ({pct(types[k], len(progs))} of programs)</li>" for k, nm in TYPE_NAMES)
    ld = json.dumps({"@context": "https://schema.org", "@type": "Dataset",
                     "name": "Shelter dog day-out programs in the United States",
                     "description": f"Counts of animal shelters and shelter dog day-out, field trip, sleepover and hiking programs by U.S. state, from {m.BRAND}'s directory, {month}.",
                     "url": m.SITE + "/report/", "dateModified": date.today().isoformat(), "isAccessibleForFree": True,
                     "license": m.SITE + "/terms/#no-scraping",
                     "creator": {"@type": "Organization", "name": m.BRAND, "url": m.SITE + "/", "parentOrganization": {"@type": "NGO", "name": "Charity Good", "url": "https://charitygood.org"}},
                     "spatialCoverage": "United States", "variableMeasured": ["shelters listed", "day-out programs", "open to public", "volunteers only"],
                     "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": m.SITE + "/report/programs-by-state.csv"}]})
    body = f"""<div class="crumbs"><a href="/">Home</a> / Report</div>
<h1>Shelter dog day-out programs in the U.S.: {month} report</h1>
<p class="lede">How many animal shelters let the public take a dog out for the day, a hike or a sleepover? Here are the exact counts from our national directory, refreshed every month.</p>
<h2>Key numbers</h2>
<ul>
<li><b>{len(rows):,}</b> animal shelters, humane societies and SPCAs listed</li>
<li><b>{len(progs):,}</b> day-out, field trip, sleepover or hiking programs found ({pct(len(progs), len(rows))} of shelters listed)</li>
<li>Programs found in <b>{n_states}</b> of {len(m.STATES)} jurisdictions (the 50 states plus D.C.)</li>
<li><b>{cats:,}</b> programs that include cats</li>
</ul>
<h2>Programs by status</h2><ul>{stat_li}</ul>
<p class="animal">"Needs check" means we found a program but couldn't confirm it's still running on the shelter's website this month.</p>
<h2>Programs by type</h2><ul>{type_li}</ul>
<p class="animal">Many programs offer more than one kind of outing, so these add up to more than the total.</p>
<h2>By state</h2>
<div style="overflow-x:auto"><table class="facts-table" style="width:100%;border-collapse:collapse">
<thead><tr><th align="left">State</th><th align="left">Shelters listed</th><th align="left">Programs</th><th align="left">Open to public</th><th align="left">Share with a program</th></tr></thead>
<tbody>{trs}</tbody></table></div>
<p><a class="btn alt" href="/report/programs-by-state.csv">Download the state totals (CSV)</a></p>
<h2>How we count</h2>
<p>We build the directory from shelters' own websites and public government pages, and re-check listings every month. A shelter counts as having a program when its own site describes a day-out, field trip, sleepover, hiking or similar outing program. Shelters we haven't found a program for are still listed, and visitors can ask them to start one. New this month? See <a href="/new-programs/">new programs</a>.</p>
<h2>Using this data</h2>
<p>You're welcome to quote these figures in articles and research. Please credit "{m.BRAND} (Charity Good)" with a link to this page. The CSV is provided for citing these state totals; copying or republishing the directory itself isn't allowed (see our <a href="/terms/#no-scraping">Terms</a>). Press questions: <a href="mailto:{m.CONTACT}">{m.CONTACT}</a>.</p>"""
    m.write("/report/", m.page(f"Shelter Dog Day-Out Programs in the U.S.: {month} Report | {m.BRAND}",
        f"{len(progs):,} shelter dog day-out, field trip and sleepover programs across {len(rows):,} U.S. animal shelters: exact counts by state and type, updated monthly.",
        body, "/report/", f'<script type="application/ld+json">{ld}</script>' + m.crumbs_ld([("Home", "/"), ("Report", "/report/")])))


BING_AUTH = '<?xml version="1.0"?>\n<users>\n\t<user>112FE28D876C615348E72ECA77A3A442</user>\n</users>\n'


def build_guides_hub(m, guides, more, h1, intro):
    def cards(items):
        return "".join(f'<div class="card"><h3><a href="{u}"{" rel=\"noopener\"" if u.startswith("http") else ""}>{m.esc(t)}</a></h3>{m.esc(d)}</div>' for u, t, d in items)
    ld = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": h1,
                     "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": m.SITE + u, "name": t} for i, (u, t, _) in enumerate(guides)]})
    body = f"""<div class="crumbs"><a href="/">Home</a> / Guides</div>
<h1>{m.esc(h1)}</h1>
<p class="lede">{m.esc(intro)}</p>
<div class="grid3">{cards(guides)}</div>
<h2>More from {m.BRAND}</h2>
<div class="grid3">{cards(more)}</div>"""
    m.write("/guides/", m.page(f"{h1} | {m.BRAND}", intro, body, "/guides/",
        f'<script type="application/ld+json">{ld}</script>' + m.crumbs_ld([("Home", "/"), ("Guides", "/guides/")])))
