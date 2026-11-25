#!/usr/bin/env python3
"""ShelterDayOut static site builder.

Reads data/listings.json (+ data/optins.json) and writes the full site to dist/.
Re-run any time the data changes; the monthly update task does exactly that.
"""
import html
import json
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
SITE = "https://shelterdayout.com"
BRAND = "ShelterDayOut"
CONTACT = "hello@shelterdayout.com"

STATES = {"AL":"Alabama","AK":"Alaska","AZ":"Arizona","AR":"Arkansas","CA":"California","CO":"Colorado","CT":"Connecticut","DE":"Delaware","DC":"District of Columbia","FL":"Florida","GA":"Georgia","HI":"Hawaii","ID":"Idaho","IL":"Illinois","IN":"Indiana","IA":"Iowa","KS":"Kansas","KY":"Kentucky","LA":"Louisiana","ME":"Maine","MD":"Maryland","MA":"Massachusetts","MI":"Michigan","MN":"Minnesota","MS":"Mississippi","MO":"Missouri","MT":"Montana","NE":"Nebraska","NV":"Nevada","NH":"New Hampshire","NJ":"New Jersey","NM":"New Mexico","NY":"New York","NC":"North Carolina","ND":"North Dakota","OH":"Ohio","OK":"Oklahoma","OR":"Oregon","PA":"Pennsylvania","RI":"Rhode Island","SC":"South Carolina","SD":"South Dakota","TN":"Tennessee","TX":"Texas","UT":"Utah","VT":"Vermont","VA":"Virginia","WA":"Washington","WV":"West Virginia","WI":"Wisconsin","WY":"Wyoming"}
STATUS_LABEL = {
    "Open to public": "Open to the public",
    "Volunteers only": "Volunteers only",
    "Paused": "Paused",
    "Needs check": "Unconfirmed",
}
STATUS_ORDER = {"Open to public": 0, "Needs check": 1, "Volunteers only": 2, "Paused": 3}
STATUS_HELP = {
    "Open to public": "Anyone who meets the shelter's rules can sign up.",
    "Volunteers only": "Open to the shelter's trained volunteers. Many shelters make it easy to become one.",
    "Paused": "The shelter says this program is on hold right now.",
    "Needs check": "We couldn't fully confirm the current details. Contact the shelter before you go.",
}
TYPE_LABEL = {"day": "Day trip", "sleep": "Sleepover", "hike": "Hike or walk", "visit": "Visit"}


def esc(s):
    return html.escape(s or "", quote=True)


def slugify(s):
    s = s.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def tag_types(offers):
    o = offers.lower()
    t = []
    if re.search(r"day trip|outing|afternoon|field trip|date", o):
        t.append("day")
    if re.search(r"sleepover|overnight|night|staycation|weekend|foster", o):
        t.append("sleep")
    if re.search(r"hike|walk|run", o):
        t.append("hike")
    if re.search(r"visit|lounge|caf", o):
        t.append("visit")
    return t or ["day"]


def load():
    rows = json.loads((ROOT / "data" / "listings.json").read_text())
    optins_path = ROOT / "data" / "optins.json"
    optins = json.loads(optins_path.read_text()) if optins_path.exists() else {}
    seen = set()
    for r in rows:
        slug = slugify(f"{r['org']} {r['city']}")
        while slug in seen:
            slug += "-2"
        seen.add(slug)
        r["slug"] = slug
        r["types"] = tag_types(r["offers"])
        r["state_name"] = STATES[r["state"]]
        r["state_slug"] = slugify(STATES[r["state"]])
        r["requests"] = bool(r.get("email_main") or r.get("email_program") or optins.get(slug))
    rows.sort(key=lambda r: (r["state"], STATUS_ORDER[r["status"]], r["city"], r["org"]))
    return rows, optins


CSS = """
:root{--ink:#1f2421;--muted:#5b625e;--line:#d9dcd6;--bg:#fbfaf7;--accent:#2f5d3a;--accent2:#9a5b1e;--soft:#eef2ec}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
a:hover{color:#1d3d25}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:normal;line-height:1.2;margin:0 0 .5em}
h1{font-size:2.1rem}h2{font-size:1.5rem;margin-top:1.6em}h3{font-size:1.15rem}
.wrap{max-width:1040px;margin:0 auto;padding:0 20px}
header.site{border-bottom:1px solid var(--line);background:#fff}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:60px;flex-wrap:wrap}
.logo{font-family:Georgia,serif;font-size:1.35rem;color:var(--ink);text-decoration:none;letter-spacing:.2px}
.logo b{color:var(--accent);font-weight:normal}
nav.main a{color:var(--ink);text-decoration:none;margin-left:18px;font-size:.95rem}
nav.main a:hover{color:var(--accent);text-decoration:underline}
main{padding:28px 0 48px}
.lede{font-size:1.1rem;color:var(--muted);max-width:720px}
.hero{padding:18px 0 8px}
.search{background:#fff;border:1px solid var(--line);padding:16px;margin:18px 0 8px}
.search .row{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-end}
.search label{font-size:.82rem;color:var(--muted);display:block;margin-bottom:4px}
.search input[type=text],.search select{font:inherit;padding:9px 10px;border:1px solid #b9beb6;background:#fff;min-width:150px}
.search input[type=text]{width:100%;min-width:220px}
.search .row>div:first-child{flex:1 1 260px}
.search .chk{font-size:.92rem;color:var(--ink);display:flex;align-items:center;gap:6px;margin:10px 0 0}
.count{color:var(--muted);font-size:.92rem;margin:14px 0 6px}
table.list{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line)}
table.list th{text-align:left;font-size:.78rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:600;padding:10px 12px;border-bottom:1px solid var(--line);background:#f4f5f1}
table.list td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}
table.list tr:last-child td{border-bottom:0}
table.list .org a{font-weight:600;text-decoration:none}
table.list .org a:hover{text-decoration:underline}
table.list .prog{color:var(--muted);font-size:.92rem}
.badge{display:inline-block;font-size:.76rem;padding:2px 7px;border:1px solid;white-space:nowrap}
.b-open{color:#245c31;border-color:#9cc3a4;background:#eef6ef}
.b-vol{color:#8a4b12;border-color:#e0bb92;background:#fbf2e8}
.b-check{color:#6b5d10;border-color:#d9cd8a;background:#fbf8e6}
.b-paused{color:#555;border-color:#bbb;background:#f1f1f1}
.animal{font-size:.85rem;color:var(--muted)}
.states{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:0;border-top:1px solid var(--line);border-left:1px solid var(--line);background:#fff;margin-top:10px}
.states a{display:block;padding:14px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);text-decoration:none;color:var(--ink)}
.states a:hover{background:var(--soft)}
.states span{display:block;color:var(--muted);font-size:.88rem}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;margin-top:8px}
.steps div{border-top:3px solid var(--accent);padding-top:10px}
.steps b{font-family:Georgia,serif;font-weight:normal;font-size:1.1rem;display:block;margin-bottom:4px}
.band{background:var(--soft);border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:26px 0;margin:36px 0 0}
.btn{display:inline-block;background:var(--accent);color:#fff!important;text-decoration:none;padding:10px 16px;border:0;font:inherit;cursor:pointer}
.btn:hover{background:#244a2e}
.btn.alt{background:#fff;color:var(--accent)!important;border:1px solid var(--accent)}
dl.facts{display:grid;grid-template-columns:150px 1fr;gap:8px 16px;margin:18px 0;background:#fff;border:1px solid var(--line);padding:16px}
dl.facts dt{color:var(--muted);font-size:.9rem}
dl.facts dd{margin:0}
.note{background:#fff;border-left:3px solid var(--accent2);padding:10px 14px;margin:16px 0}
.crumbs{font-size:.88rem;color:var(--muted);margin-bottom:10px}
.crumbs a{color:var(--muted)}
form.std{background:#fff;border:1px solid var(--line);padding:18px;max-width:640px}
form.std label{display:block;font-size:.9rem;margin:12px 0 4px}
form.std input,form.std select,form.std textarea{width:100%;font:inherit;padding:9px 10px;border:1px solid #b9beb6;background:#fff}
form.std textarea{min-height:110px}
form.std .hp{position:absolute;left:-5000px}
form.std .fine{font-size:.82rem;color:var(--muted);margin-top:12px}
.prose{max-width:740px}
footer.site{border-top:1px solid var(--line);background:#fff;padding:24px 0;font-size:.9rem;color:var(--muted)}
footer.site a{color:var(--muted);margin-right:16px}
.hide{display:none}
@media (max-width:700px){
 h1{font-size:1.65rem}
 nav.main a{margin:0 14px 0 0}
 table.list thead{display:none}
 table.list,table.list tbody,table.list tr,table.list td{display:block;width:100%}
 table.list tr{border-bottom:1px solid var(--line)}
 table.list td{border:0;padding:4px 12px}
 table.list td:first-child{padding-top:12px}
 table.list td:last-child{padding-bottom:12px}
 dl.facts{grid-template-columns:1fr}
 dl.facts dt{margin-top:6px}
}
"""


def badge(status):
    cls = {"Open to public": "b-open", "Volunteers only": "b-vol", "Needs check": "b-check", "Paused": "b-paused"}[status]
    return f'<span class="badge {cls}">{esc(STATUS_LABEL[status])}</span>'


def page(title, desc, body, path, extra_head="", canonical=True):
    url = SITE + path
    can = f'<link rel="canonical" href="{url}">' if canonical else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
{can}
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{BRAND}">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
{extra_head}
</head>
<body>
<header class="site"><div class="wrap">
<a class="logo" href="/">Shelter<b>DayOut</b></a>
<nav class="main"><a href="/#find">Find an outing</a><a href="/cats/">Cats</a><a href="/how-it-works/">How it works</a><a href="/for-shelters/">For shelters</a></nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
<p><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/cats/">Cats</a><a href="/for-shelters/">For shelters</a><a href="/suggest/">Suggest a shelter</a><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
<p>{BRAND} is a free directory. We don't run outings or handle bookings; each shelter sets its own rules. Listings are checked monthly, but details change, so confirm with the shelter before you go.</p>
<p>{BRAND} is a program of <a href="https://charitygood.org" rel="noopener">Charity Good</a>. &copy; {date.today().year} Charity Good</p>
</div></footer>
</body>
</html>
"""


def write(path, content):
    p = DIST / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def row_html(r, show_state=True):
    loc = f"{esc(r['city'])}, {r['state']}" if show_state else esc(r["city"])
    types = " ".join(r["types"])
    return f"""<tr data-state="{r['state']}" data-animals="{esc(r['animals'])}" data-types="{types}" data-status="{esc(r['status'])}" data-q="{esc((r['org']+' '+r['city']+' '+r['state_name']+' '+r['program']).lower())}">
<td class="org"><a href="/listings/{r['slug']}/">{esc(r['org'])}</a><div class="prog">{esc(r['program'])}</div></td>
<td>{loc}</td>
<td>{esc(r['offers'])}<div class="animal">{esc(r['animals'])}</div></td>
<td>{badge(r['status'])}</td>
</tr>"""


def table(rows, show_state=True):
    body = "\n".join(row_html(r, show_state) for r in rows)
    return f"""<table class="list" id="results">
<thead><tr><th>Shelter and program</th><th>Location</th><th>What you can do</th><th>Who can go</th></tr></thead>
<tbody>
{body}
</tbody></table>"""


FILTER_JS = """<script>
(function(){
 var q=document.getElementById('q'),st=document.getElementById('f-state'),an=document.getElementById('f-animal'),ty=document.getElementById('f-type'),pub=document.getElementById('f-public'),cnt=document.getElementById('count');
 var rows=[].slice.call(document.querySelectorAll('#results tbody tr'));
 function run(){
  var t=(q&&q.value||'').trim().toLowerCase(),s=st?st.value:'',a=an.value,y=ty.value,p=pub.checked,n=0;
  rows.forEach(function(r){
   var ok=true;
   if(t&&r.dataset.q.indexOf(t)<0)ok=false;
   if(s&&r.dataset.state!==s)ok=false;
   if(a&&r.dataset.animals.indexOf(a)<0)ok=false;
   if(y&&r.dataset.types.split(' ').indexOf(y)<0)ok=false;
   if(p&&r.dataset.status!=='Open to public')ok=false;
   r.classList.toggle('hide',!ok); if(ok)n++;
  });
  cnt.textContent=n+(n===1?' program':' programs');
 }
 [q,st,an,ty,pub].forEach(function(el){if(el){el.addEventListener('input',run);el.addEventListener('change',run);}});
 var u=new URLSearchParams(location.search);
 if(u.get('q')&&q){q.value=u.get('q');}
 if(u.get('state')&&st){st.value=u.get('state').toUpperCase();}
 if(u.get('animal')){an.value=u.get('animal');}
 run();
})();
</script>"""


def filters(with_state=True, states_present=()):
    state_sel = ""
    if with_state:
        opts = "".join(f'<option value="{k}">{v}</option>' for k, v in STATES.items() if k in states_present)
        state_sel = f'<div><label for="f-state">State</label><select id="f-state"><option value="">All states</option>{opts}</select></div>'
    search_box = '<div style="flex:1"><label for="q">City, shelter or program</label><input type="text" id="q" placeholder="e.g. Austin, Pasadena Humane, sleepover"></div>' if with_state else ""
    return f"""<div class="search">
<div class="row">
{search_box}
{state_sel}
<div><label for="f-animal">Animal</label><select id="f-animal"><option value="">Dogs and cats</option><option value="Dogs">Dogs</option><option value="Cats">Cats</option></select></div>
<div><label for="f-type">Type</label><select id="f-type"><option value="">Any</option><option value="day">Day trip</option><option value="sleep">Sleepover or staycation</option><option value="hike">Hike or walk</option><option value="visit">Visit (cat lounge)</option></select></div>
</div>
<label class="chk"><input type="checkbox" id="f-public"> Open to the public only</label>
</div>
<p class="count" id="count"></p>"""


def build_home(rows):
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    open_n = sum(1 for r in rows if r["status"] == "Open to public")
    state_links = "".join(
        f'<a href="/states/{slugify(STATES[s])}/">{STATES[s]}<span>{len(by_state.get(s, []))} program{"" if len(by_state.get(s, [])) == 1 else "s"}</span></a>'
        for s in sorted(STATES, key=lambda k: STATES[k])
    )
    n_states = len([k for k in by_state if k != "DC"])
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": SITE + "/",
        "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"},
    })
    body = f"""<section class="hero">
<h1>Take a shelter dog out for the day.</h1>
<p class="lede">Find animal shelters where you can take an adoptable dog on a day trip, a hike or a sleepover, or spend time with shelter cats. It's free, it helps animals get adopted, and every listing is checked monthly.</p>
</section>
<section id="find">
{filters(True, by_state.keys())}
{table(rows)}
</section>
<h2>Browse by state</h2>
<div class="states">{state_links}</div>
<p class="animal" style="margin-top:8px">{len(rows)} programs in {n_states} states and Washington, DC so far. We search every state each month and add new programs as shelters launch them. <a href="/suggest/">Know a shelter we're missing?</a></p>
<h2>How it works</h2>
<div class="steps">
<div><b>1. Find a program</b>Search by city or state. {open_n} programs listed here are open to the public.</div>
<div><b>2. Sign up with the shelter</b>Each listing links to the shelter's own sign-up page, rules and hours. Shelters make the match.</div>
<div><b>3. Enjoy the day</b>Take the dog for a hike, a coffee or a nap on your couch. The photos you share help them get adopted.</div>
</div>
<div class="band"><div class="wrap" style="padding:0">
<h2 style="margin-top:0">Run a shelter?</h2>
<p>Get listed for free, update your details, or start receiving outing requests from people near you. <a class="btn" href="/for-shelters/">For shelters</a></p>
</div></div>
{FILTER_JS}"""
    write("/", page(
        f"{BRAND}: Take a shelter dog out for the day",
        "Find animal shelters where you can take an adoptable dog on a day trip, hike or sleepover, or visit shelter cats. Free directory, checked monthly.",
        body, "/", f'<script type="application/ld+json">{ld}</script>'))


def build_states(rows):
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    for s in STATES:
        lst = by_state.get(s, [])
        name = STATES[s]
        if not lst:
            body = f'''<div class="crumbs"><a href="/">Home</a> / {name}</div>
<h1>Shelter dog day trips and sleepovers in {name}</h1>
<p class="lede">We haven't found a public day-out, sleepover or cat program in {name} yet. We check every state each month and add new programs as shelters launch them.</p>
<p><a class="btn" href="/suggest/">Know one? Tell us</a> <a class="btn alt" href="/for-shelters/">Run a shelter in {name}?</a></p>
<p class="animal" style="margin-top:16px">Many shelters will still let you walk dogs or socialize cats as a volunteer. Ask your local shelter about volunteering or short-term fostering.</p>'''
            write(f"/states/{slugify(name)}/", page(
                f"Shelter Dog Day Trips & Sleepovers in {name} | {BRAND}",
                f"Animal shelter day-out, sleepover and cat programs in {name}. Know one we're missing? Tell us.",
                body, f"/states/{slugify(name)}/"))
            continue
        open_n = sum(1 for r in lst if r["status"] == "Open to public")
        cities = sorted({r["city"] for r in lst})
        body = f"""<div class="crumbs"><a href="/">Home</a> / {name}</div>
<h1>Shelter dog day trips and sleepovers in {name}</h1>
<p class="lede">{len(lst)} shelter programs in {name}, {open_n} of them open to the public. Cities include {esc(', '.join(cities[:8]))}{'' if len(cities) <= 8 else ' and more'}.</p>
{filters(False)}
{table(lst, show_state=False)}
<p class="animal" style="margin-top:12px">Don't see your shelter? <a href="/suggest/">Suggest one</a>. Shelter staff can <a href="/for-shelters/">claim a listing</a>.</p>
{FILTER_JS}"""
        write(f"/states/{slugify(name)}/", page(
            f"Shelter Dog Day Trips & Sleepovers in {name} | {BRAND}",
            f"{len(lst)} animal shelter programs in {name} where you can take a dog on a day trip or sleepover, or visit shelter cats.",
            body, f"/states/{slugify(name)}/"))


def build_listings(rows):
    for r in rows:
        name = r["org"]
        offers = esc(r["offers"])
        note = f'<p>{esc(r["notes"])}</p>' if r.get("notes") else ""
        req = ""
        if r["requests"]:
            req = f'<a class="btn" href="/request/?listing={r["slug"]}">Request an outing</a> '
        go = f'<a class="btn{" alt" if r["requests"] else ""}" href="{esc(r["url"])}" rel="noopener nofollow" target="_blank">Sign up on the shelter\'s site</a>'
        status_help = STATUS_HELP[r["status"]]
        ld = json.dumps({
            "@context": "https://schema.org", "@type": "AnimalShelter", "name": name,
            "address": {"@type": "PostalAddress", "addressLocality": r["city"], "addressRegion": r["state"], "addressCountry": "US"},
            "url": SITE + f"/listings/{r['slug']}/",
        })
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/states/{r['state_slug']}/">{r['state_name']}</a> / {esc(name)}</div>
<h1>{esc(name)}</h1>
<p class="lede">{esc(r['program'])} &middot; {esc(r['city'])}, {r['state_name']}</p>
<p>{badge(r['status'])} <span class="animal">{esc(status_help)}</span></p>
<dl class="facts">
<dt>Program</dt><dd>{esc(r['program'])}</dd>
<dt>What you can do</dt><dd>{offers}</dd>
<dt>Animals</dt><dd>{esc(r['animals'])}</dd>
<dt>Location</dt><dd>{esc(r['city'])}, {r['state_name']}</dd>
<dt>Last checked</dt><dd>{esc(r['checked'])}</dd>
</dl>
{note}
<p>{req}{go}</p>
<div class="note">Rules, hours and fees are set by the shelter and can change. Always confirm with the shelter before you go. {BRAND} isn't affiliated with this shelter and doesn't arrange outings.</div>
<p class="animal">Is something out of date? <a href="/suggest/?type=report&amp;listing={r['slug']}">Report a problem</a>. Work at this shelter? <a href="/for-shelters/?listing={r['slug']}">Claim this listing</a> to update it or receive outing requests.</p>"""
        write(f"/listings/{r['slug']}/", page(
            f"{name} {r['program']} ({r['city']}, {r['state']}) | {BRAND}",
            f"{r['program']} at {name} in {r['city']}, {r['state_name']}: {r['offers']}. Details, rules and how to sign up.",
            body, f"/listings/{r['slug']}/", f'<script type="application/ld+json">{ld}</script>'))


def build_cats(rows):
    cats = [r for r in rows if "Cats" in r["animals"]]
    body = f"""<h1>Spend time with shelter cats</h1>
<div class="prose">
<p class="lede">Cats don't usually go on outings. New places stress them out. But there are still great ways to give a shelter cat a break and help them get adopted.</p>
<h2>Ways to help shelter cats</h2>
<p><b>Staycations and sleepovers.</b> Some shelters let you take an adult cat home for a night or a few days. The cat gets a quiet break, and the shelter learns how they act in a home.</p>
<p><b>Cat lounges and cafés.</b> Rescue-run lounges let you hang out with adoptable cats and kittens for an hour or more. Your admission helps fund their care.</p>
<p><b>Kitten fostering.</b> In spring and summer, shelters need homes for very young kittens for a few weeks. Ask your local shelter about its foster program.</p>
</div>
<h2>Cat programs we list</h2>
{table(cats)}
<p class="animal" style="margin-top:12px">Know a shelter with a cat program? <a href="/suggest/">Tell us</a>.</p>"""
    write("/cats/", page(
        f"Shelter Cat Sleepovers, Staycations & Cat Lounges | {BRAND}",
        "Ways to spend time with shelter cats: staycations, sleepovers, rescue cat lounges and kitten fostering. Listings checked monthly.",
        body, "/cats/"))


def form_page(path, title, desc, intro, fields, form_type, extra=""):
    body = f"""<h1>{esc(title)}</h1>
<div class="prose">{intro}</div>
<form class="std" method="post" action="/forms/submit.php">
<input type="hidden" name="form" value="{form_type}">
<input type="hidden" name="listing" id="listing" value="">
<div class="hp"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
{fields}
<p style="margin-top:16px"><button class="btn" type="submit">Send</button></p>
<p class="fine">We use what you send only to respond to you and run {BRAND}. See our <a href="/privacy/">privacy policy</a>.</p>
</form>
<script>(function(){{var u=new URLSearchParams(location.search),l=u.get('listing');if(l){{document.getElementById('listing').value=l.replace(/[^a-z0-9-]/g,'');}}var t=u.get('type'),s=document.getElementById('kind');if(t&&s){{s.value=t;}}}})();</script>
{extra}"""
    write(path, page(f"{title} | {BRAND}", desc, body, path))


def build_forms(rows=None):
    form_page("/for-shelters/", "For shelters",
              "List your shelter's day-out, sleepover or cat program on ShelterDayOut for free, update your listing, or receive outing requests.",
              f"""<p class="lede">{BRAND} is a free national directory that sends people to your day-out, field trip, sleepover and cat programs. Listing is free and always will be.</p>
<h2>What you can do</h2>
<p><b>Claim or update your listing.</b> Correct your hours, rules, fees or sign-up link, or ask us to remove it.</p>
<p><b>Choose where outing requests go.</b> People can send outing requests from your listing. They go to your public email (and your program email, if you have one) with the person's contact details. Tell us a better address, or ask us to turn requests off. You approve, match and hand off the animal as you do today, under your own agreements and waivers. We never take bookings or payments.</p>
<p><b>Add a program.</b> Starting a day-out program? Tell us and we'll list it.</p>
<h2>Tell us about your shelter</h2>""",
              """<label for="kind">What would you like to do?</label>
<select id="kind" name="kind"><option value="claim">Claim or update our listing</option><option value="requests">Change where requests go</option><option value="stop">Stop outing requests</option><option value="add">Add our program</option><option value="remove">Remove our listing</option></select>
<label for="org">Shelter or rescue name</label><input id="org" name="org" required maxlength="200">
<label for="city">City and state</label><input id="city" name="city" required maxlength="120">
<label for="name">Your name</label><input id="name" name="name" required maxlength="120">
<label for="role">Your role</label><input id="role" name="role" maxlength="120" placeholder="e.g. Foster coordinator">
<label for="email">Work email (where requests should go)</label><input id="email" name="email" type="email" required maxlength="200">
<label for="phone">Phone (optional)</label><input id="phone" name="phone" maxlength="40">
<label for="message">Program details or changes</label><textarea id="message" name="message" maxlength="4000" placeholder="Program name, what people can do, rules, sign-up link"></textarea>
<label style="display:flex;gap:8px;align-items:flex-start;font-size:.9rem"><input type="checkbox" name="confirm" value="yes" required style="width:auto;margin-top:4px"> I work for or volunteer with this organization and can speak for it.</label>""",
              "shelter")

    form_page("/suggest/", "Suggest a shelter or report a problem",
              "Tell ShelterDayOut about a shelter program we're missing, or report outdated information on a listing.",
              """<p class="lede">Know a shelter with a day-out, sleepover or cat program we're missing? Spot something out of date? Let us know and we'll check it.</p>""",
              """<label for="kind">This is about</label>
<select id="kind" name="kind"><option value="suggest">A shelter or program you're missing</option><option value="report">Out-of-date information on a listing</option><option value="wish">I wish there was a program near me</option></select>
<label for="org">Shelter name (if you know it)</label><input id="org" name="org" maxlength="200">
<label for="city">City and state</label><input id="city" name="city" required maxlength="120">
<label for="message">Details</label><textarea id="message" name="message" required maxlength="4000" placeholder="A link to the program helps us check it faster"></textarea>
<label for="email">Your email (optional, if you'd like a reply)</label><input id="email" name="email" type="email" maxlength="200">""",
              "suggest")

    # Phase 2 request form: shown for listings with a known shelter email.
    req_map = json.dumps({r["slug"]: r["org"] for r in (rows or []) if r["requests"]})
    body = f"""<h1>Request an outing</h1>
<div class="prose"><p class="lede" id="req-intro">Send an outing request straight to the shelter's email. They'll reply to you by email or phone to confirm details and next steps.</p></div>
<form class="std" method="post" action="/forms/submit.php">
<input type="hidden" name="form" value="request">
<input type="hidden" name="listing" id="listing" value="">
<div class="hp"><label>Leave this empty<input type="text" name="website" tabindex="-1" autocomplete="off"></label></div>
<label for="name">Your name</label><input id="name" name="name" required maxlength="120">
<label for="email">Email</label><input id="email" name="email" type="email" required maxlength="200">
<label for="phone">Phone</label><input id="phone" name="phone" maxlength="40">
<label for="when">Preferred date(s)</label><input id="when" name="when" maxlength="200" placeholder="e.g. Saturday Dec 6, morning">
<label for="kind">Type of outing</label><select id="kind" name="kind"><option>Day trip</option><option>Hike or walk</option><option>Sleepover or staycation</option><option>Visit</option></select>
<label for="message">Anything the shelter should know?</label><textarea id="message" name="message" maxlength="3000" placeholder="Your plans for the day, experience with dogs or cats, other pets or kids at home"></textarea>
<label style="display:flex;gap:8px;align-items:flex-start;font-size:.9rem"><input type="checkbox" name="confirm" value="yes" required style="width:auto;margin-top:4px"> I'm 18 or older and understand the shelter decides whether to approve the outing and sets its own rules.</label>
<p style="margin-top:16px"><button class="btn" type="submit">Send request</button></p>
<p class="fine">Your request goes to the shelter you picked, with a copy kept by {BRAND} so we can help if something goes wrong. See our <a href="/privacy/">privacy policy</a>.</p>
</form>
<script>(function(){{var M={req_map};var l=(new URLSearchParams(location.search).get('listing')||'').replace(/[^a-z0-9-]/g,'');document.getElementById('listing').value=l;var t=document.getElementById('req-intro');if(M[l]){{t.textContent='Send an outing request to '+M[l]+'. They will reply to you by email or phone to confirm details and next steps.';}}else{{t.textContent='Pick a shelter from the directory first, then use its Request an outing button.';document.querySelector('form.std').style.display='none';}}}})();</script>"""
    write("/request/", page(f"Request an outing | {BRAND}", "Send an outing request to a participating shelter.", body, "/request/", '<meta name="robots" content="noindex">'))

    thanks = f"""<h1>Thanks, we got it.</h1><p class="lede">Your message was sent. If you asked for a reply, we'll be in touch by email.</p><p><a class="btn" href="/">Back to {BRAND}</a></p>"""
    write("/thanks/", page(f"Thanks | {BRAND}", "Message sent.", thanks, "/thanks/", '<meta name="robots" content="noindex">'))
    oops = f"""<h1>Something went wrong.</h1><p class="lede">Your message couldn't be sent. Please go back and check the form, or email <a href="mailto:{CONTACT}">{CONTACT}</a>.</p>"""
    write("/oops/", page(f"Message not sent | {BRAND}", "Message not sent.", oops, "/oops/", '<meta name="robots" content="noindex">'))


def build_static_pages(rows):
    open_n = sum(1 for r in rows if r["status"] == "Open to public")
    write("/how-it-works/", page(f"How Shelter Dog Day Trips Work | {BRAND}",
        "What a shelter dog day trip or sleepover is, how to sign up, what to bring, and tips for a great outing.",
        f"""<h1>How shelter dog day trips work</h1>
<div class="prose">
<p class="lede">More and more shelters let people take adoptable dogs out for a few hours or a night. The dogs get a break from the kennel, and you help them get seen by future families.</p>
<h2>What is a day out?</h2>
<p>A day out (also called a field trip, daycation or doggy day out) is a short outing with a shelter dog: a walk, a hike, a coffee run or an afternoon on your couch. Many shelters also offer sleepovers or weekend staycations.</p>
<h2>How to sign up</h2>
<p>Find a program on {BRAND}, then follow the link to the shelter's own page. Most ask you to fill out a short form, show an ID, and sign an agreement. Some take walk-ins; others need a reservation. The shelter picks a dog that fits your plans.</p>
<h2>Who can go?</h2>
<p>Programs marked <b>Open to the public</b> ({open_n} so far) welcome anyone who meets the shelter's rules, usually 18 or older. <b>Volunteers only</b> programs are for the shelter's trained volunteers, and many shelters make it easy to become one.</p>
<h2>Tips for a great outing</h2>
<p>Bring water and a bowl, keep the dog on leash, skip dog parks, and take lots of photos. Share them and tag the shelter: good photos are one of the best ways to help a dog find a home. If you fall in love, ask about adopting.</p>
<h2>What about cats?</h2>
<p>Cats usually prefer to stay put, so cat programs look different: staycations at home, lounge visits and kitten fostering. See <a href="/cats/">cat programs</a>.</p>
</div>""", "/how-it-works/"))

    write("/about/", page(f"About {BRAND}", f"{BRAND} is a free national directory of shelter day-out, sleepover and cat programs.",
        f"""<h1>About {BRAND}</h1>
<div class="prose">
<p class="lede">{BRAND} is a free directory of animal shelter programs that let people take dogs out for the day, host a sleepover, or spend time with shelter cats.</p>
<p>Studies of these programs find that outings help dogs get adopted, and they're good for people too. But every shelter runs its program differently, with its own sign-up page, and they're hard to find. {BRAND} gathers them in one place.</p>
<h2>How we keep it accurate</h2>
<p>We build listings from shelters' own public pages and check every listing each month. Each listing shows when it was last checked and whether it's open to the public, volunteers only, or unconfirmed. Shelters can <a href="/for-shelters/">claim their listing</a> to keep it current.</p>
<h2>What we don't do</h2>
<p>We don't run outings, take bookings or handle payments. Shelters decide who can take an animal out and set their own rules and agreements. When you send an outing request, we email it to the shelter so they can reply to you directly.</p>
<h2>Contact</h2>
<p><a href="mailto:{CONTACT}">{CONTACT}</a></p>
</div>""", "/about/"))

    write("/terms/", page(f"Terms of Use | {BRAND}", f"Terms of use for {BRAND}.",
        f"""<h1>Terms of use</h1>
<div class="prose">
<p>Last updated {date.today().strftime('%B %-d, %Y')}.</p>
<p>{BRAND} is a program of Charity Good (charitygood.org) ("Charity Good", "we", "us"). By using {BRAND} (the "site") you agree to these terms.</p>
<h2>A directory, not a service provider</h2>
<p>{BRAND} is an information directory. We list programs run by independent animal shelters and rescues. We are not affiliated with them unless a listing says so, and we don't run outings, sleepovers, visits or adoptions. Each shelter decides who may participate and sets its own rules, fees, agreements and waivers, which govern your outing.</p>
<h2>Information may change</h2>
<p>We check listings regularly, but program details change and may be wrong or out of date. Always confirm details with the shelter. The site is provided "as is" without warranties of any kind.</p>
<h2>Outing requests</h2>
<p>You can send a shelter an outing request through the site. We email your request to the shelter's public contact address and, where it has one, its program address. Sending a request doesn't guarantee an outing. The shelter alone decides whether to approve it. We aren't a party to any arrangement between you and a shelter.</p>
<h2>Your responsibility</h2>
<p>Animals can be unpredictable. You're responsible for following the shelter's instructions and for your own conduct and safety during any outing. To the fullest extent the law allows, {BRAND} isn't liable for any injury, loss, damage or dispute arising from an outing, visit, request or your use of the site.</p>
<h2>Acceptable use</h2>
<p>Don't submit false information, impersonate a shelter, spam shelters through request forms, or copy the site's content in bulk by automated means.</p>
<h2>Shelters</h2>
<p>Shelters may ask us to correct or remove their listing at any time through the <a href="/for-shelters/">For shelters</a> page.</p>
<h2>Changes and contact</h2>
<p>We may update these terms; the date above shows the latest version. Questions: <a href="mailto:{CONTACT}">{CONTACT}</a>.</p>
</div>""", "/terms/"))

    write("/privacy/", page(f"Privacy Policy | {BRAND}", f"Privacy policy for {BRAND}.",
        f"""<h1>Privacy policy</h1>
<div class="prose">
<p>Last updated {date.today().strftime('%B %-d, %Y')}.</p>
<p>{BRAND} is a program of Charity Good (charitygood.org). This policy explains what we collect on the site and how we use it.</p>
<h2>What we collect</h2>
<p>You can browse {BRAND} without giving us any personal information. If you send a form, we collect what you enter, such as your name, email, phone and message. Our web host keeps standard server logs (like IP address and pages visited) for security and basic traffic counts.</p>
<h2>How we use it</h2>
<p>We use form details only to respond to you, update listings, and run the site. If you send an outing request, we send it to the shelter you chose so they can contact you, and keep a copy in case there's a problem. Shelters handle your information under their own policies.</p>
<h2>What we don't do</h2>
<p>We don't sell or rent personal information, and we don't use advertising trackers.</p>
<h2>Keeping and deleting</h2>
<p>We keep form messages only as long as needed to run the site. To see or delete what you sent us, email <a href="mailto:{CONTACT}">{CONTACT}</a>.</p>
<h2>Children</h2>
<p>The site isn't directed to children under 13, and outing requests require you to be 18 or older.</p>
</div>""", "/privacy/"))

    write("/404.html", page(f"Page not found | {BRAND}", "Page not found.",
        f"""<h1>Page not found</h1><p class="lede">That page doesn't exist or has moved.</p><p><a class="btn" href="/">Find a shelter outing</a></p>""", "/404.html", canonical=False))


def build_assets(rows, optins):
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "site.css").write_text(CSS.strip() + "\n")
    (DIST / "favicon.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" fill="#2f5d3a"/>'
        '<circle cx="10" cy="11" r="3" fill="#fff"/><circle cx="16" cy="8.5" r="3" fill="#fff"/><circle cx="22" cy="11" r="3" fill="#fff"/>'
        '<ellipse cx="16" cy="20" rx="7" ry="6" fill="#fff"/></svg>')
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /forms/\nSitemap: {SITE}/sitemap.xml\n")
    today = date.today().isoformat()
    urls = ["/", "/cats/", "/how-it-works/", "/for-shelters/", "/suggest/", "/about/", "/terms/", "/privacy/"]
    urls += sorted({f"/states/{slugify(v)}/" for v in STATES.values()})
    urls += [f"/listings/{r['slug']}/" for r in rows]
    sm = "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    # Form handler + the listing->shelter map it needs (only opted-in shelters get requests).
    shutil.copytree(ROOT / "src" / "forms", DIST / "forms", dirs_exist_ok=True)
    lookup = {}
    for r in rows:
        em = r.get("email_main") or (optins.get(r["slug"], {}) or {}).get("email", "")
        lookup[r["slug"]] = {"org": r["org"], "city": r["city"], "state": r["state"], "email_main": em, "email_program": r.get("email_program", "")}
    (DIST / "forms" / "listings.json").write_text(json.dumps(lookup))
    (DIST / "forms" / "optins.json").write_text(json.dumps(optins))
    (DIST / ".htaccess").write_text(
        "ErrorDocument 404 /404.html\nOptions -Indexes\n"
        "<IfModule mod_rewrite.c>\nRewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n"
        "RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]\nRewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]\n</IfModule>\n"
        "")


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    rows, optins = load()
    build_assets(rows, optins)
    build_home(rows)
    build_states(rows)
    build_listings(rows)
    build_cats(rows)
    build_forms(rows)
    build_static_pages(rows)
    n = sum(1 for _ in DIST.rglob("*.html"))
    print(f"Built {len(rows)} listings, {n} pages into {DIST}")


if __name__ == "__main__":
    main()
