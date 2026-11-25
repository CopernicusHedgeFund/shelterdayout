#!/usr/bin/env python3
"""ShelterDayOut static site builder.

Reads data/listings.json (+ data/optins.json) and writes the full site to dist/.
Re-run any time the data changes; the monthly update task does exactly that.
"""
import html
import json
import re
import shutil
from datetime import date, datetime
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
    "No program yet": "No program yet",
}
NOPROG = "No program yet"
STATUS_ORDER = {"Open to public": 0, "Needs check": 1, "Volunteers only": 2, "Paused": 3, "No program yet": 9}
STATUS_HELP = {
    "Open to public": "Anyone who meets the shelter's rules can sign up.",
    "Volunteers only": "Open to the shelter's trained volunteers. Many shelters make it easy to become one.",
    "Paused": "The shelter says this program is on hold right now.",
    "Needs check": "We couldn't fully confirm the current details. Contact the shelter before you go.",
    "No program yet": "This shelter doesn't run a day-out program that we know of. You can still send a request: once a month we tell each shelter how many people want to take their dogs out, and pass along your details.",
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
        r["requests"] = bool(r.get("email_main") or r.get("email_program") or optins.get(slug)) or r["status"] == NOPROG
    rows.sort(key=lambda r: (r["state"], STATUS_ORDER[r["status"]], r["city"], r["org"]))
    return rows, optins


CSS = """
:root{--ink:#2b2d42;--muted:#5c6178;--line:#eadfce;--bg:#fffaf2;--accent:#ff7a59;--accent-d:#e55d3c;--teal:#2a9d8f;--sun:#ffd166;--mint:#e6f6f0;--card:#fff}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.6 "Nunito",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif}
a{color:var(--teal);font-weight:700}
a:hover{color:#1f7a6f}
h1,h2,h3{font-family:"Fredoka","Nunito",sans-serif;font-weight:600;line-height:1.15;margin:0 0 .45em;color:var(--ink)}
h1{font-size:2.5rem}h2{font-size:1.65rem;margin-top:1.6em}h3{font-size:1.2rem}
.wrap{max-width:1080px;margin:0 auto;padding:0 20px}
header.site{background:#fff;border-bottom:3px solid var(--sun)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;min-height:66px;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:8px;font-family:"Fredoka",sans-serif;font-weight:600;font-size:1.5rem;color:var(--ink);text-decoration:none}
.logo b{color:var(--accent);font-weight:600}
.logo svg{width:34px;height:34px}
nav.main a{color:var(--ink);text-decoration:none;margin-left:6px;font-weight:700;font-size:.97rem;padding:7px 12px;border-radius:999px}
nav.main a:hover{background:var(--mint);color:var(--teal)}
main{padding:24px 0 56px}
.lede{font-size:1.15rem;color:var(--muted);max-width:640px}
.hero{display:grid;grid-template-columns:1.05fr 1fr;gap:28px;align-items:center;padding:14px 0 6px}
.hero img{width:100%;height:auto;display:block}
.hero h1 .hl{color:var(--accent)}
.pills{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 0}
.pills span{background:#fff;border:2px solid var(--line);border-radius:999px;padding:4px 12px;font-size:.88rem;font-weight:700;color:var(--muted)}
.search{background:#fff;border:2px solid var(--line);border-radius:20px;padding:18px;margin:22px 0 8px;box-shadow:0 6px 0 #f3e6d2}
.search .row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.search label{font-size:.82rem;color:var(--muted);display:block;margin-bottom:4px;font-weight:700}
.search input[type=text],.search select{font:inherit;font-size:.98rem;padding:10px 12px;border:2px solid #e2d6c3;border-radius:12px;background:#fff;min-width:150px}
.search input[type=text]:focus,.search select:focus{outline:none;border-color:var(--teal)}
.search input[type=text]{width:100%;min-width:220px}
.search .row>div:first-child{flex:1 1 260px}
.search .chk{font-size:.95rem;color:var(--ink);display:flex;align-items:center;gap:8px;margin:0;font-weight:700}
.search .row2{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-top:12px}
.search .sbtn{border:0;cursor:pointer;font-size:1rem;padding:12px 28px}
@media(max-width:640px){.search .sbtn{width:100%}}
.count{color:var(--muted);font-size:.95rem;margin:14px 4px 8px;font-weight:700}
table.list{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:2px solid var(--line);border-radius:18px;overflow:hidden}
table.list th{text-align:left;font-size:.76rem;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:800;padding:12px 14px;background:#fff3e2}
table.list td{padding:14px;border-top:2px solid #f6eee1;vertical-align:top}
table.list tbody tr:hover{background:#fffbf4}
table.list .org a{font-size:1.04rem;text-decoration:none;color:var(--ink)}
table.list .org a:hover{color:var(--accent)}
table.list .prog{color:var(--muted);font-size:.92rem}
.badge{display:inline-block;font-size:.78rem;font-weight:800;padding:3px 10px;border-radius:999px;white-space:nowrap}
.b-open{color:#1d6b4f;background:#d8f3e6}
.b-vol{color:#9a4f12;background:#ffe7cf}
.b-check{color:#7a6410;background:#fff2bf}
.b-paused{color:#555;background:#eee}
.tagline{font-weight:800;color:var(--teal);margin:6px 0 0}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:8px 0 26px}
.stats div{background:#fff;border:2px solid #f3e9da;border-radius:16px;padding:14px 10px;text-align:center}
.stats b{display:block;font-family:Fredoka,sans-serif;font-size:1.9rem;color:var(--accent);line-height:1.1}
.stats span{font-size:.88rem;color:var(--muted);font-weight:700}
@media(max-width:640px){.stats{grid-template-columns:repeat(2,1fr)}.stats b{font-size:1.5rem}}
.faq{background:#fff;border:2px solid #f3e9da;border-radius:14px;padding:12px 16px;margin:8px 0}
.faq summary{font-weight:800;cursor:pointer}
.faq p{margin:8px 0 0}
.citylinks a{display:inline-block;margin:0 10px 8px 0;font-weight:700}
.evlist{padding-left:18px}
.evlist li{margin:6px 0}
.b-none{color:#4a4e69;background:#ebe9f5}
.noprog{margin-top:34px}
.noprog ul{list-style:none;padding:0;margin:10px 0;display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}
.noprog li{background:#fff;border:2px solid #f3e9da;border-radius:14px;padding:12px 14px}
.noprog li b{display:block}
.noprog li span{color:var(--muted);font-size:.9rem}
.animal{font-size:.88rem;color:var(--muted)}
.ico{display:inline-block;vertical-align:-4px;width:20px;height:20px;margin-right:4px}
.states{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px;margin-top:12px}
.states a{display:flex;align-items:center;gap:10px;padding:12px 14px;border-radius:14px;background:#fff;border:2px solid var(--line);text-decoration:none;color:var(--ink)}
.states a:hover{border-color:var(--accent);transform:translateY(-2px)}
.states a.none{opacity:.55}
.states svg{flex:0 0 22px;width:22px;height:22px}
.states span{display:block;color:var(--muted);font-size:.82rem;font-weight:700}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:18px;margin-top:10px}
.steps div{background:#fff;border:2px solid var(--line);border-radius:20px;padding:20px}
.steps .num{display:flex;width:52px;height:52px;border-radius:50%;align-items:center;justify-content:center;margin-bottom:10px}
.steps .num svg{width:30px;height:30px}
.steps b{font-family:"Fredoka",sans-serif;font-weight:600;font-size:1.2rem;display:block;margin-bottom:4px}
.band{background:var(--teal);color:#fff;border-radius:24px;padding:28px;margin:40px 0 0;display:flex;gap:24px;align-items:center;flex-wrap:wrap;position:relative;overflow:hidden}
.band h2{color:#fff;margin:0 0 6px}
.band p{margin:0}
.band .paws{position:absolute;right:-10px;bottom:-10px;opacity:.18;width:180px}
.btn{display:inline-block;background:var(--accent);color:#fff!important;text-decoration:none;padding:12px 20px;border:0;border-radius:999px;font:inherit;font-weight:800;cursor:pointer;box-shadow:0 4px 0 var(--accent-d);transition:transform .1s}
.btn:hover{transform:translateY(-2px)}
.btn:active{transform:translateY(2px);box-shadow:0 2px 0 var(--accent-d)}
.btn.alt{background:#fff;color:var(--teal)!important;box-shadow:0 4px 0 #cfe9e4;border:2px solid var(--teal)}
.band .btn{background:var(--sun);color:var(--ink)!important;box-shadow:0 4px 0 #e0b23f}
dl.facts{display:grid;grid-template-columns:160px 1fr;gap:10px 16px;margin:18px 0;background:#fff;border:2px solid var(--line);border-radius:18px;padding:18px}
dl.facts dt{color:var(--muted);font-size:.9rem;font-weight:700}
dl.facts dd{margin:0}
.note{background:#fff8e1;border-radius:14px;padding:12px 16px;margin:18px 0;border:2px dashed #f0d58a}
.crumbs{font-size:.9rem;color:var(--muted);margin-bottom:10px}
.crumbs a{color:var(--muted);font-weight:600}
form.std{background:#fff;border:2px solid var(--line);border-radius:20px;padding:22px;max-width:660px}
form.std label{display:block;font-size:.92rem;margin:12px 0 4px;font-weight:700}
form.std input,form.std select,form.std textarea{width:100%;font:inherit;padding:10px 12px;border:2px solid #e2d6c3;border-radius:12px;background:#fff}
form.std input:focus,form.std select:focus,form.std textarea:focus{outline:none;border-color:var(--teal)}
form.std textarea{min-height:110px}
form.std .hp{position:absolute;left:-5000px}
form.std .fine{font-size:.84rem;color:var(--muted);margin-top:12px}
.prose{max-width:740px}
.art{max-width:420px;width:100%;height:auto;display:block;margin:6px 0 10px}
.paw-divider{display:flex;gap:14px;justify-content:center;margin:34px 0 4px;opacity:.5}
.paw-divider svg{width:20px;height:20px}
footer.site{background:var(--ink);color:#cfd2e0;padding:30px 0;font-size:.92rem}
footer.site a{color:#fff;margin-right:16px;font-weight:700}
footer.site .logo{color:#fff;margin-bottom:10px}
.hide,table.list tr.hide{display:none!important}
@media (max-width:820px){
 .hero{grid-template-columns:1fr}
 .hero img{max-width:460px;margin:0 auto}
}
@media (max-width:700px){
 h1{font-size:1.9rem}
 nav.main{display:flex;flex-wrap:wrap;gap:2px}
 nav.main a{margin:0;padding:6px 10px}
 table.list thead{display:none}
 table.list,table.list tbody,table.list tr,table.list td{display:block;width:100%}
 table.list tr{border-top:2px solid #f6eee1}
 table.list tr:first-child{border-top:0}
 table.list td{border:0;padding:4px 14px}
 table.list td:first-child{padding-top:14px}
 table.list td:last-child{padding-bottom:14px}
 dl.facts{grid-template-columns:1fr}
 dl.facts dt{margin-top:6px}
}
"""


PAW = '<svg viewBox="0 0 24 24" aria-hidden="true"><g fill="currentColor"><ellipse cx="12" cy="16" rx="5.5" ry="4.5"/><circle cx="5.5" cy="10" r="2.4"/><circle cx="9.5" cy="6" r="2.4"/><circle cx="14.5" cy="6" r="2.4"/><circle cx="18.5" cy="10" r="2.4"/></g></svg>'
ICONS = {
 "day": '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="5" fill="#ffd166"/><g stroke="#f4a259" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/><line x1="5" y1="5" x2="6.4" y2="6.4"/><line x1="17.6" y1="17.6" x2="19" y2="19"/><line x1="5" y1="19" x2="6.4" y2="17.6"/><line x1="17.6" y1="6.4" x2="19" y2="5"/></g></svg>',
 "sleep": '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 15A8 8 0 0 1 9 5a8 8 0 1 0 10 10z" fill="#7b8cde"/><circle cx="17" cy="5" r="1.2" fill="#ffd166"/><circle cx="21" cy="9" r="1" fill="#ffd166"/></svg>',
 "hike": '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 20 L9 8 L13 14 L16 10 L22 20Z" fill="#4fae86"/><path d="M9 8 L10.6 10.7 L7.4 10.7Z" fill="#fff"/></svg>',
 "visit": '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 9h12v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5z" fill="#ff7a59"/><path d="M16 11h2a2 2 0 0 1 0 4h-2" stroke="#ff7a59" stroke-width="2" fill="none"/><path d="M8 3c0 2 2 2 2 4M12 3c0 2 2 2 2 4" stroke="#c9a27e" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>',
}
LOGO = '<svg viewBox="0 0 40 40" aria-hidden="true"><circle cx="20" cy="20" r="20" fill="#ff7a59"/><g fill="#fff"><ellipse cx="20" cy="25" rx="7" ry="6"/><circle cx="11.5" cy="17" r="3"/><circle cx="16.5" cy="11.5" r="3"/><circle cx="23.5" cy="11.5" r="3"/><circle cx="28.5" cy="17" r="3"/></g></svg>'
PAWROW = '<div class="paw-divider" style="color:#e2c9a4">' + PAW*5 + '</div>'


def badge(status):
    cls = {"Open to public": "b-open", "Volunteers only": "b-vol", "Needs check": "b-check", "Paused": "b-paused", "No program yet": "b-none"}[status]
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
<meta property="og:image" content="{SITE}/assets/og.png">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fredoka:wght@500;600&family=Nunito:wght@400;600;700;800&display=swap">
<link rel="stylesheet" href="/assets/site.css">
{extra_head}
</head>
<body>
<header class="site"><div class="wrap">
<a class="logo" href="/">{LOGO}<span>Shelter<b>DayOut</b></span></a>
<nav class="main"><a href="/#find">Find an outing</a><a href="/cats/">Cats</a><a href="/find-a-vet/">Find a vet</a><a href="/for-shelters/">For shelters</a></nav>
</div></header>
<main><div class="wrap">
{body}
{PAWROW}
</div></main>
<footer class="site"><div class="wrap">
<div class="logo">{LOGO}<span>Shelter<b>DayOut</b></span></div>
<p><a href="/rent-a-dog/">Rent or borrow a dog</a><a href="/shelter-dog-sleepovers/">Shelter dog sleepovers</a><a href="/hike-with-a-shelter-dog/">Hike with a shelter dog</a><a href="/cities/">Browse by city</a><a href="/events/">Adoption events</a></p>
<p><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/cats/">Cats</a><a href="/for-shelters/">For shelters</a><a href="/suggest/">Suggest a shelter</a><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
<p>{BRAND} is a free directory. We don't run outings or handle bookings; each shelter sets its own rules. Listings are checked monthly, but details change, so confirm with the shelter before you go.</p>
<p class="fine">Some shelter locations: &copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License.</p>
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
<td>{''.join(ICONS[t] for t in r['types'])}{esc(r['offers'])}<div class="animal">{esc(r['animals'])}</div></td>
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
 var f=document.getElementById('sform'),res=document.getElementById('results');
 if(f){f.addEventListener('submit',function(e){e.preventDefault();run();if(q)q.blur();if(res){res.scrollIntoView({behavior:'smooth',block:'start'});}});}
 var u=new URLSearchParams(location.search);
 if(u.get('q')&&q){q.value=u.get('q');}
 if(u.get('state')&&st){st.value=u.get('state').toUpperCase();}
 if(u.get('animal')){an.value=u.get('animal');}
 if(u.get('type')){ty.value=u.get('type');}
 if(u.get('public')){pub.checked=true;}
 run();
})();
</script>"""


def filters(with_state=True, states_present=()):
    state_sel = ""
    if with_state:
        opts = "".join(f'<option value="{k}">{v}</option>' for k, v in STATES.items() if k in states_present)
        state_sel = f'<div><label for="f-state">State</label><select id="f-state" name="state"><option value="">All states</option>{opts}</select></div>'
    search_box = '<div style="flex:1"><label for="q">City, shelter or program</label><input type="text" id="q" name="q" enterkeyhint="search" placeholder="e.g. Austin, Pasadena Humane, sleepover"></div>' if with_state else ""
    return f"""<form class="search" id="sform" action="" method="get" role="search">
<div class="row">
{search_box}
{state_sel}
<div><label for="f-animal">Animal</label><select id="f-animal" name="animal"><option value="">Dogs and cats</option><option value="Dogs">Dogs</option><option value="Cats">Cats</option></select></div>
<div><label for="f-type">Type</label><select id="f-type" name="type"><option value="">Any</option><option value="day">Day trip</option><option value="sleep">Sleepover or staycation</option><option value="hike">Hike or walk</option><option value="visit">Visit (cat lounge)</option></select></div>
</div>
<div class="row2"><label class="chk"><input type="checkbox" id="f-public" name="public" value="1"> Open to the public only</label>
<button type="submit" class="btn sbtn">Search</button></div>
</form>
<p class="count" id="count" aria-live="polite"></p>"""


def crumbs_ld(items):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]}) + "</script>"


def faq_block(faqs):
    html_ = "".join(f"<details class=\"faq\"><summary>{esc(q)}</summary><p>{a}</p></details>" for q, a in faqs)
    ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r"<[^>]+>", "", a)}} for q, a in faqs]})
    return html_, f'<script type="application/ld+json">{ld}</script>'


HOME_FAQ = [
    ("Can I rent a dog for the day?", "Not from a business, but you can do something better: many animal shelters let you <a href=\"/rent-a-dog/\">borrow an adoptable dog for free</a> for a few hours, a full day or a sleepover. Programs go by names like Doggy Day Out, Dog for a Day, Field Trips and Daycations."),
    ("How much does it cost to take a shelter dog out for the day?", "Almost always nothing. Shelters run these programs to give dogs a break from the kennel and help them get adopted, and most send you off with a leash, an Adopt Me vest and treats."),
    ("Do I have to adopt the dog?", "No. There is no commitment. If you fall in love, you can ask the shelter about adopting, but most people simply bring the dog back at the end of the outing."),
    ("Who can take a shelter dog out?", "Most programs require you to be 18 or older with a photo ID and a signed waiver. Some are open to anyone who walks in; others are for trained volunteers or require booking ahead. Each listing says which."),
    ("Can I have a sleepover with a shelter dog?", "Yes, many shelters offer overnights, weekend sleepovers or multi-day staycations. See <a href=\"/shelter-dog-sleepovers/\">shelter dog sleepovers near you</a>."),
    ("Is there a dog day out program near me?", "Search the directory above by city or state, or <a href=\"/cities/\">browse by city</a>. We list programs in all 50 states and check them every month. If your shelter doesn't run one yet, you can still send a request."),
]


def build_home(rows, all_rows=None):
    all_rows = all_rows or rows
    all_by = {}
    for r in all_rows:
        all_by[r["state"]] = all_by.get(r["state"], 0) + 1
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    open_n = sum(1 for r in rows if r["status"] == "Open to public")
    state_links = "".join(
        f'<a class="{"" if by_state.get(s) else "none"}" href="/states/{slugify(STATES[s])}/" style="color:#ff7a59">{PAW}<div style="color:#2b2d42">{STATES[s]}<span>{all_by.get(s, 0):,} shelter{"" if all_by.get(s, 0) == 1 else "s"} &middot; {len(by_state.get(s, []))} program{"" if len(by_state.get(s, [])) == 1 else "s"}</span></div></a>'
        for s in sorted(STATES, key=lambda k: STATES[k])
    ).replace("</span></a>", "</span></div></a>")
    n_states = len([k for k in by_state if k != "DC"])
    ld = json.dumps({
        "@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": SITE + "/",
        "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"},
    })
    faq_html, faq_ld = faq_block(HOME_FAQ)
    cc = {}
    for r in rows:
        cc.setdefault((r["city"], r["state"]), 0); cc[(r["city"], r["state"])] += 1
    top = sorted(cc.items(), key=lambda kv: (-kv[1], kv[0]))[:30]
    city_links = " ".join(f'<a href="/cities/{slugify(c + " " + st)}/">{esc(c)}, {st}</a>' for (c, st), _ in sorted(top, key=lambda kv: kv[0]))
    org_ld = json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": SITE + "/",
        "logo": SITE + "/assets/og.png", "email": CONTACT, "parentOrganization": {"@type": "NGO", "name": "Charity Good", "url": "https://charitygood.org"}})
    body = f"""<section class="hero">
<div>
<h1>Take a shelter dog out <span class="hl">for the day.</span></h1>
<p class="lede">Hike, grab a pup cup, or host a sleepover with an adoptable dog, or spend time with shelter cats. It's free, it helps animals get adopted, and every listing is checked monthly.</p>
<p class="tagline">The nationwide database of shelter day-out programs, updated monthly.</p>
<div class="pills"><span>{ICONS['day']}Day trips</span><span>{ICONS['sleep']}Sleepovers</span><span>{ICONS['hike']}Hikes</span><span>{ICONS['visit']}Cat lounges</span></div>
<p style="margin-top:18px"><a class="btn" href="#find">Find an outing near you</a></p>
</div>
<img src="/assets/hero.svg" alt="A happy shelter dog in an Adopt Me bandana and a cat on an outdoor adventure" width="560" height="380">
</section>
<div class="stats">
<div><b>{len(all_rows):,}</b><span>shelters listed</span></div>
<div><b>{len(rows):,}</b><span>day-out &amp; cat programs</span></div>
<div><b>{len({r["state"] for r in all_rows if r["state"] != "DC"})}</b><span>states{" + DC" if any(r["state"] == "DC" for r in all_rows) else ""} covered</span></div>
<div><b>Monthly</b><span>updated {date.today().strftime("%B %Y")}</span></div>
</div>
<section id="find">
{filters(True, by_state.keys())}
{table(rows)}
</section>
<h2>Browse by state</h2>
<div class="states">{state_links}</div>
<p class="animal" style="margin-top:8px">{len(all_rows):,} shelters listed nationwide, including {len(rows):,} with day-out or cat programs in {n_states} states and Washington, DC. We search every state each month and add new programs as shelters launch them. <a href="/suggest/">Know a shelter we're missing?</a></p>
<h2>How it works</h2>
<div class="steps">
<div><span class="num" style="background:#ffe7cf">{ICONS['hike'].replace('class="ico"','')}</span><b>1. Find a program</b>Search by city or state. {open_n} programs listed here are open to the public.</div>
<div><span class="num" style="background:#d8f3e6">{PAW.replace('currentColor','#2a9d8f')}</span><b>2. Sign up with the shelter</b>Each listing links to the shelter's own sign-up page, rules and hours. Shelters make the match.</div>
<div><span class="num" style="background:#fff2bf">{ICONS['day'].replace('class="ico"','')}</span><b>3. Enjoy the day</b>Take the dog for a hike, a coffee or a nap on your couch. The photos you share help them get adopted.</div>
</div>
<h2>Questions people ask</h2>
{faq_html}
<h2>Popular cities</h2>
<p class="citylinks">{city_links}</p>
<div class="band"><div style="flex:1 1 360px"><h2>Run a shelter?</h2><p>Get listed for free, update your details, or choose where outing requests go.</p></div><a class="btn" href="/for-shelters/">For shelters</a></div>
{FILTER_JS}"""
    write("/", page(
        "Borrow a Shelter Dog for the Day: Dog Day Out & Sleepover Programs Near You | ShelterDayOut",
        f"Want to rent a dog for the day? Borrow an adoptable shelter dog free for a day trip, hike or sleepover. {len(all_rows):,} shelters nationwide, checked monthly.",
        body, "/", f'<script type="application/ld+json">{ld}</script><script type="application/ld+json">{org_ld}</script>{faq_ld}'))


def noprog_section(others, name):
    if not others:
        return ""
    items = "".join(
        f'<li><b><a href="/listings/{r["slug"]}/">{esc(r["org"])}</a></b><span>{esc(r["city"])}</span>'
        + (f'<br><a href="/request/?listing={r["slug"]}">Request an outing</a>' if r["requests"] else "")
        + "</li>" for r in sorted(others, key=lambda r: (r["city"], r["org"])))
    return f"""<section class="noprog"><h2>Other shelters in {name}</h2>
<p class="animal">These shelters don't run a day-out program that we know of yet. Want to take one of their dogs out? Send a request. Once a month we tell each shelter how many people asked, with a free guide to starting a program.</p>
<ul>{items}</ul></section>"""


def build_states(rows):
    by_state = {}
    for r in rows:
        by_state.setdefault(r["state"], []).append(r)
    for s in STATES:
        allst = by_state.get(s, [])
        lst = [r for r in allst if r["status"] != NOPROG]
        others = [r for r in allst if r["status"] == NOPROG]
        name = STATES[s]
        np_html = noprog_section(others, name)
        if not lst:
            body = f'''<div class="crumbs"><a href="/">Home</a> / {name}</div>
<h1>Shelter dog day trips and sleepovers in {name}</h1>
<p class="lede">We haven't found a public day-out, sleepover or cat program in {name} yet. We check every state each month and add new programs as shelters launch them.</p>
<p><a class="btn" href="/suggest/">Know one? Tell us</a> <a class="btn alt" href="/for-shelters/">Run a shelter in {name}?</a></p>
<p class="animal" style="margin-top:16px">Many shelters will still let you walk dogs or socialize cats as a volunteer. Ask your local shelter about volunteering or short-term fostering.</p>
{np_html}'''
            write(f"/states/{slugify(name)}/", page(
                f"Borrow a Shelter Dog in {name}: Day Trips & Sleepovers | {BRAND}",
                f"Looking to rent or borrow a shelter dog for the day in {name}? See shelters in {name} and request a dog day out. Checked monthly.",
                body, f"/states/{slugify(name)}/", crumbs_ld([("Home", "/"), (name, f"/states/{slugify(name)}/")])))
            continue
        open_n = sum(1 for r in lst if r["status"] == "Open to public")
        cities = sorted({r["city"] for r in lst})
        body = f"""<div class="crumbs"><a href="/">Home</a> / {name}</div>
<h1>Take a shelter dog out for the day in {name}</h1>
<p class="lede">Want to rent or borrow a dog in {name}? These shelters let you take an adoptable dog on a day trip, hike or sleepover for free. {len(lst)} shelter programs in {name}, {open_n} of them open to the public. Cities include {esc(', '.join(cities[:8]))}{'' if len(cities) <= 8 else ' and more'}.</p>
{filters(False)}
{table(lst, show_state=False)}
<p class="animal" style="margin-top:12px">Don't see your shelter? <a href="/suggest/">Suggest one</a>. Shelter staff can <a href="/for-shelters/">claim a listing</a>.</p>
{np_html}
{FILTER_JS}"""
        write(f"/states/{slugify(name)}/", page(
            f"Borrow a Shelter Dog in {name}: {len(lst)} Day Trip & Sleepover Programs | {BRAND}",
            f"Rent or borrow a shelter dog for the day in {name}, free. {len(lst)} programs in {', '.join(cities[:4])} and more, plus {len(others)} other shelters. Checked monthly.",
            body, f"/states/{slugify(name)}/", crumbs_ld([("Home", "/"), (name, f"/states/{slugify(name)}/")])))


def contact_html(r):
    """Public shelter email, assembled in the browser so bots scraping the HTML don't harvest it."""
    em = r.get("email_program") or r.get("email_main")
    if not em or "@" not in em:
        return ""
    user, dom = em.split("@", 1)
    return (f'<dt>Email</dt><dd><span class="em" data-u="{esc(user[::-1])}" data-d="{esc(dom[::-1])}">(enable JavaScript to see)</span>'
            "<script>(function(){var e=document.currentScript.previousElementSibling;var a=e.dataset.u.split('').reverse().join('')+'@'+e.dataset.d.split('').reverse().join('');"
            "e.innerHTML='<a href=\\'mailto:'+a+'\\'>'+a+'</a>';})();</script></dd>")


def build_listings(rows):
    for r in rows:
        name = r["org"]
        offers = esc(r["offers"])
        note = f'<p>{esc(r["notes"])}</p>' if r.get("notes") else ""
        req = ""
        if r["requests"]:
            req = f'<a class="btn" href="/request/?listing={r["slug"]}">Request an outing</a> '
        go = f'<a class="btn{" alt" if r["requests"] else ""}" href="{esc(r["url"])}" rel="noopener nofollow" target="_blank">{"Visit the shelter\'s site" if r["status"] == NOPROG else "Sign up on the shelter\'s site"}</a>'
        if not r.get("url"):
            go = ""
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
{f"<dt>What you can do</dt><dd>{offers}</dd>" if offers else ""}
<dt>Animals</dt><dd>{esc(r['animals'])}</dd>
<dt>Location</dt><dd>{esc(r['city'])}, {r['state_name']}</dd>
{contact_html(r)}<dt>Last checked</dt><dd>{esc(r['checked'])}</dd>
</dl>
{note}
{f'<h2>Upcoming events</h2><ul class="evlist">{events_html(r, upcoming(r))}</ul>' if upcoming(r) else ""}
<p>{req}{go}</p>
{f'<p class="animal">Source: <a href="{esc(r["source"])}" rel="noopener nofollow" target="_blank">news coverage of this program</a></p>' if r.get("source") else ""}
<div class="note">Rules, hours and fees are set by the shelter and can change. Always confirm with the shelter before you go. {BRAND} isn't affiliated with this shelter and doesn't arrange outings.</div>
<p class="animal">Is something out of date? <a href="/suggest/?type=report&amp;listing={r['slug']}">Report a problem</a>. Work at this shelter? <a href="/for-shelters/?listing={r['slug']}">Claim this listing</a> to update it or receive outing requests.</p>"""
        write(f"/listings/{r['slug']}/", page(
            (f"{name} ({r['city']}, {r['state']}): Request a Dog Day Out | {BRAND}" if r["status"] == NOPROG
             else f"{r['program']} at {name}, {r['city']}, {r['state']}: Take a Shelter Dog Out | {BRAND}"),
            (f"{name} in {r['city']}, {r['state_name']} doesn't list a dog day out program yet. Ask them for one: we pass requests to the shelter every month."
             if r["status"] == NOPROG else
             f"Take a shelter dog out with {name} in {r['city']}, {r['state_name']}: {r['offers']}. Free. Rules, hours and how to sign up."),
            body, f"/listings/{r['slug']}/", f'<script type="application/ld+json">{ld}</script>' + "".join(f'<script type="application/ld+json">{json.dumps(event_ld(r, e))}</script>' for e in upcoming(r)) + crumbs_ld([("Home", "/"), (r["state_name"], f"/states/{r['state_slug']}/"), (name, f"/listings/{r['slug']}/")])))


def build_cats(rows):
    cats = [r for r in rows if "Cats" in r["animals"]]
    body = f"""<h1>Spend time with shelter cats</h1>
<img class="art" src="/assets/cats.svg" alt="Two shelter cats, one in a cardboard box and one playing with yarn" width="420" height="260">
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
    req_map = json.dumps({r["slug"]: [r["org"], 1 if r["status"] == NOPROG else 0] for r in (rows or []) if r["requests"]})
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
<p class="fine">Your request goes to the shelter you picked (right away if it runs a program, or in our monthly note if it doesn't), with a copy kept by {BRAND} so we can help if something goes wrong. See our <a href="/privacy/">privacy policy</a>.</p>
</form>
<script>(function(){{var M={req_map};var l=(new URLSearchParams(location.search).get('listing')||'').replace(/[^a-z0-9-]/g,'');document.getElementById('listing').value=l;var t=document.getElementById('req-intro');if(M[l]&&M[l][1]){{t.textContent=M[l][0]+' does not run a day-out program yet. Send your request and we will add it to a monthly note telling them how many people want to take their dogs out, with your name and contact details so they can reach you if they start one.';}}else if(M[l]){{t.textContent='Send an outing request to '+M[l][0]+'. They will reply to you by email or phone to confirm details and next steps.';}}else{{t.textContent='Pick a shelter from the directory first, then use its Request an outing button.';document.querySelector('form.std').style.display='none';}}}})();</script>"""
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


def upcoming(r):
    today = date.today().isoformat()
    return sorted([e for e in r.get("events", []) if (e.get("end") or e.get("date", "")) >= today], key=lambda e: e["date"])


def fmt_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%a, %b %-d, %Y")
    except Exception:
        return d


def event_ld(r, e):
    return {"@context": "https://schema.org", "@type": "Event", "name": e["title"], "startDate": e["date"],
            "endDate": e.get("end") or e["date"], "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
            "eventStatus": "https://schema.org/EventScheduled",
            "location": {"@type": "Place", "name": e.get("place") or r["org"], "address": {"@type": "PostalAddress", "addressLocality": r["city"], "addressRegion": r["state"], "addressCountry": "US"}},
            "organizer": {"@type": "Organization", "name": r["org"], "url": r.get("url") or SITE},
            "url": e.get("url") or r.get("url") or SITE, "isAccessibleForFree": True}


def events_html(r, evs):
    return "".join(f'<li><b>{fmt_date(e["date"])}{(" – " + fmt_date(e["end"])) if e.get("end") and e["end"] != e["date"] else ""}</b> '
                   f'{f"<a href=\"{esc(e["url"])}\" rel=\"noopener nofollow\" target=\"_blank\">{esc(e["title"])}</a>" if e.get("url") else esc(e["title"])}'
                   f'{(" · " + esc(e["place"])) if e.get("place") else ""}</li>' for e in evs)


def build_events(rows):
    allev = []
    for r in rows:
        for e in upcoming(r):
            allev.append((e["date"], r, e))
    allev.sort(key=lambda x: x[0])
    groups, cur = "", None
    for d, r, e in allev:
        m = d[:7]
        if m != cur:
            groups += ("</ul>" if cur else "") + f'<h2>{datetime.strptime(m, "%Y-%m").strftime("%B %Y")}</h2><ul class="evlist">'
            cur = m
        groups += f'<li><b>{fmt_date(e["date"])}</b> · <a href="/listings/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}, {r["state"]}): {esc(e["title"])}</li>'
    if cur:
        groups += "</ul>"
    ld = "".join(f'<script type="application/ld+json">{json.dumps(event_ld(r, e))}</script>' for _, r, e in allev[:200])
    body = f"""<h1>Upcoming shelter adoption events</h1>
<p class="lede">{len(allev)} upcoming adoption events, open houses and fee-waived days at shelters nationwide. Dates come from each shelter's own website; confirm with the shelter before you go.</p>
{groups or '<p>No upcoming events listed right now. Check back soon.</p>'}"""
    write("/events/", page(f"Shelter Adoption Events Near You: {len(allev)} Upcoming Dates | {BRAND}",
        f"Upcoming pet adoption events, open houses and fee-waived adoption days at {len({id(r) for _, r, _ in allev})} shelters nationwide. Updated monthly.",
        body, "/events/", ld))
    return allev


def build_cities(progs):
    by = {}
    for r in progs:
        by.setdefault((r["city"], r["state"]), []).append(r)
    idx = []
    for (city, st), lst in sorted(by.items(), key=lambda kv: (STATES[kv[0][1]], kv[0][0])):
        slug = slugify(city + " " + st)
        sname = STATES[st]
        idx.append((sname, city, st, slug, len(lst)))
        types = sorted({TYPE_LABEL[t].lower() for r in lst for t in r["types"]})
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/states/{slugify(sname)}/">{sname}</a> / {esc(city)}</div>
<h1>Take a shelter dog out for the day in {esc(city)}, {st}</h1>
<p class="lede">Looking to rent or borrow a dog in {esc(city)}? {len(lst)} local shelter program{"s" if len(lst) != 1 else ""} let{"" if len(lst) != 1 else "s"} you take an adoptable dog out for free: {", ".join(types)}.</p>
{table(lst, show_state=False)}
<p class="animal" style="margin-top:12px">More nearby: see every program in <a href="/states/{slugify(sname)}/">{sname}</a>. New to this? Read <a href="/how-it-works/">how shelter dog day trips work</a>.</p>"""
        write(f"/cities/{slug}/", page(
            f"Rent or Borrow a Dog in {city}, {st}: Shelter Dog Day Out Programs | {BRAND}",
            f"Borrow a shelter dog for the day in {city}, {sname}, free: {len(lst)} program{'s' if len(lst) != 1 else ''} for {', '.join(types)}. Rules, hours and sign-up links.",
            body, f"/cities/{slug}/", crumbs_ld([("Home", "/"), (sname, f"/states/{slugify(sname)}/"), (city, f"/cities/{slug}/")])))
    groups = ""
    cur = None
    for sname, city, st, slug, n in idx:
        if sname != cur:
            groups += ("</p>" if cur else "") + f'<h2>{sname}</h2><p class="citylinks">'
            cur = sname
        groups += f'<a href="/cities/{slug}/">{esc(city)}</a>'
    groups += "</p>"
    write("/cities/", page(f"Shelter Dog Day Out Programs by City | {BRAND}",
        f"Find a shelter dog day trip, hike or sleepover program in {len(idx)} US cities. Free to join, checked monthly.",
        f'<h1>Find a shelter dog day out by city</h1><p class="lede">{len(idx)} cities with shelters that let you take a dog out for the day.</p>{groups}', "/cities/"))


GUIDES = {
    "/rent-a-dog/": dict(
        title="Rent a Dog for the Day? Borrow a Shelter Dog Free Instead | ShelterDayOut",
        desc="Want to rent a dog for a day? Many shelters let you borrow an adoptable dog free for a few hours, a hike or a sleepover. Find a program near you.",
        h1="Want to rent a dog for the day? Borrow a shelter dog instead",
        types=None,
        intro="Dog rental businesses are rare and controversial, but hundreds of animal shelters let you borrow a dog for free. You get a hiking buddy or a couch companion for the day; the dog gets a break from the kennel and a better shot at adoption. Shelters call it Doggy Day Out, Dog for a Day, Field Trips, Daycations, Rent-A-Dog or Borrow a Buddy.",
        faqs=[("Is borrowing a shelter dog free?", "Yes, almost always. Shelters provide a leash, an Adopt Me vest and often treats and a water bowl."),
              ("What do I need to borrow a dog?", "Usually a photo ID, being 18 or older, and a signed waiver. Some shelters need a short orientation or an online booking first."),
              ("How long can I keep the dog?", "Day trips run from a couple of hours to a full day. Many shelters also offer overnights, weekend sleepovers or week-long staycations.")]),
    "/shelter-dog-sleepovers/": dict(
        title="Shelter Dog Sleepovers Near You: Overnight & Weekend Programs | ShelterDayOut",
        desc="Host a shelter dog for a night, a weekend or a staycation. Find shelter dog sleepover programs near you, free and checked monthly.",
        h1="Have a sleepover with a shelter dog",
        types="sleep",
        intro="A night or a weekend in a home lets a shelter dog decompress and shows the shelter how they act in a house. Programs go by names like Slumber Party, Pawjama Party, Staycation, Sleepover Buddies and Weekend Warrior.",
        faqs=[("Do I need to be a foster to host a sleepover?", "Some shelters sign you up as a one-night foster on the spot; others ask you to complete a short foster application first. Each listing explains."),
              ("Can I bring the dog home if I have other pets?", "Shelters usually ask you to keep the visiting dog separated from resident pets unless they have done a meet and greet.")]),
    "/hike-with-a-shelter-dog/": dict(
        title="Hike With a Shelter Dog: Trail Buddy & Field Trip Programs | ShelterDayOut",
        desc="Take an adoptable shelter dog hiking or for a long walk. Find shelter trail buddy and field trip programs near you, free and checked monthly.",
        h1="Take a shelter dog hiking",
        types="hike",
        intro="Shelter dogs love the trail as much as you do. These programs let you take an adoptable dog for a hike, a run or a long walk, then share photos that help them get adopted.",
        faqs=[("Can anyone hike with a shelter dog?", "Many programs are open to the public with an ID and waiver; some trail programs are for trained volunteers. Each listing says who can go."),
              ("Where can I take the dog?", "Usually anywhere dogs are allowed on leash. Most shelters ask you to avoid dog parks.")]),
}


def build_guides(progs):
    for path, g in GUIDES.items():
        lst = [r for r in progs if g["types"] is None or g["types"] in r["types"]]
        if g["types"] is None:
            lst = [r for r in lst if r["status"] in ("Open to public", "Needs check") and "Dogs" in r["animals"]]
        faq_html, faq_ld = faq_block(g["faqs"])
        body = f"""<div class="crumbs"><a href="/">Home</a> / {esc(g['h1'])}</div>
<h1>{esc(g['h1'])}</h1>
<div class="prose"><p class="lede">{esc(g['intro'])}</p></div>
<h2>{len(lst)} programs</h2>
{table(lst)}
<h2>Good to know</h2>
{faq_html}"""
        write(path, page(g["title"], g["desc"], body, path, faq_ld + crumbs_ld([("Home", "/"), (g["h1"], path)])))


VET_JS = """<script>
(function(){
 var q=document.getElementById('vq'),st=document.getElementById('vst'),em=document.getElementById('vem'),lc=document.getElementById('vlc'),out=document.getElementById('vout'),cnt=document.getElementById('vcount'),cache={};
 function esc(s){return (s||'').replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
 function row(v){var site=v.w?'<a href="'+esc(v.w)+'" rel="noopener nofollow" target="_blank">Website</a>':'';var ph=v.p?'<a href="tel:'+esc(v.p.replace(/[^0-9+]/g,''))+'">'+esc(v.p)+'</a>':'';
  return '<tr><td><b>'+esc(v.n)+'</b>'+(v.e?' <span class="badge b-open">24/7 emergency</span>':'')+(v.l?' <span class="badge b-check">Low-cost / nonprofit</span>':'')+'<br><span class="animal">'+esc(v.a||'')+'</span></td><td>'+esc(v.c)+', '+v.s+(v.z?' '+esc(v.z):'')+'</td><td>'+ph+(ph&&site?'<br>':'')+site+'</td></tr>';}
 function render(list){var t=(q.value||'').trim().toLowerCase(),r=list.filter(function(v){if(em.checked&&!v.e)return false;if(lc.checked&&!v.l)return false;if(!t)return true;return (v.n+' '+v.c+' '+(v.z||'')).toLowerCase().indexOf(t)>=0;});
  cnt.textContent=r.length+' vets'+(r.length>300?' (showing first 300, narrow your search)':'');out.innerHTML=r.slice(0,300).map(row).join('');}
 function load(){var s=st.value;if(!s){cnt.textContent='Pick a state to search vets.';out.innerHTML='';return;}
  if(cache[s])return render(cache[s]);cnt.textContent='Loading...';fetch('/find-a-vet/data/'+s+'.json').then(function(r){return r.json();}).then(function(d){cache[s]=d;render(d);});}
 st.addEventListener('change',load);[q,em,lc].forEach(function(e){e.addEventListener('input',load);e.addEventListener('change',load);});
 document.getElementById('vform').addEventListener('submit',function(e){e.preventDefault();load();});
 var u=new URLSearchParams(location.search);if(u.get('state'))st.value=u.get('state').toUpperCase();if(u.get('q'))q.value=u.get('q');load();
})();
</script>"""


def build_vets():
    src = ROOT / "data" / "osm_vets.json"
    if not src.exists():
        return
    raw = json.loads(src.read_text())["places"]
    lowcost = re.compile(r"low.?cost|nonprofit|non-profit|spay|neuter|humane|spca|community|clinic for|charity|rescue|free", re.I)
    by = {}
    for v in raw:
        if v["state"] not in STATES or not v.get("city"):
            continue
        site = (v.get("website") or "").split(";")[0].strip()
        if site and not site.startswith("http"):
            site = "https://" + site
        rec = {"n": v["name"], "c": v["city"], "s": v["state"], "z": (v.get("zip") or "")[:5], "a": v.get("street", ""),
               "p": (v.get("phone") or "").split(";")[0].strip(), "w": site,
               "e": 1 if v.get("emergency") == "yes" or re.search(r"emergency|24.?7|24 hour", v["name"], re.I) else 0,
               "l": 1 if lowcost.search(v["name"] + " " + v.get("operator", "")) or v.get("operator_type") in ("community", "ngo", "charity") else 0}
        by.setdefault(v["state"], []).append(rec)
    (DIST / "find-a-vet" / "data").mkdir(parents=True, exist_ok=True)
    total = 0
    for stc, lst in by.items():
        lst.sort(key=lambda r: (r["c"], r["n"]))
        total += len(lst)
        (DIST / "find-a-vet" / "data" / f"{stc}.json").write_text(json.dumps(lst, separators=(",", ":")))
    opts = "".join(f'<option value="{k}">{v} ({len(by.get(k, [])):,})</option>' for k, v in sorted(STATES.items(), key=lambda kv: kv[1]) if by.get(k))
    state_links = " ".join(f'<a href="/find-a-vet/{slugify(STATES[k])}/">{STATES[k]}</a>' for k in sorted(by, key=lambda k: STATES[k]))
    body = f"""<h1>Find a vet near you</h1>
<p class="lede">Search {total:,} veterinary clinics across the US. Filter for 24/7 emergency vets or low-cost and nonprofit clinics. Updated every 3 months.</p>
<form class="search" id="vform"><div class="row">
<div style="flex:1"><label for="vq">City, ZIP or clinic name</label><input id="vq" type="text" placeholder="e.g. Denver, 80202, Banfield" enterkeyhint="search"></div>
<div><label for="vst">State</label><select id="vst"><option value="">Choose a state</option>{opts}</select></div>
</div><div class="row2"><label class="chk"><input type="checkbox" id="vem"> 24/7 emergency only</label><label class="chk"><input type="checkbox" id="vlc"> Low-cost / nonprofit</label><button class="btn sbtn" type="submit">Search</button></div></form>
<p class="count" id="vcount"></p>
<table class="list"><thead><tr><th>Clinic</th><th>Location</th><th>Contact</th></tr></thead><tbody id="vout"></tbody></table>
<div class="note">Clinic details come from OpenStreetMap and can be out of date. Call ahead, especially for emergencies. Know a vet we're missing or see a mistake? <a href="/suggest/">Tell us</a>.</div>
<h2>Browse vets by state</h2><p class="citylinks">{state_links}</p>
{VET_JS}"""
    write("/find-a-vet/", page(f"Find a Vet Near You: {total:,} Veterinary Clinics, Emergency & Low-Cost | {BRAND}",
        f"Search {total:,} vet clinics across the US by city, ZIP or state. Find 24/7 emergency vets and low-cost or nonprofit clinics. Updated every 3 months.",
        body, "/find-a-vet/"))
    for stc, lst in by.items():
        name = STATES[stc]
        rows_html = "".join(
            f'<tr><td><b>{esc(r["n"])}</b>{" <span class=\"badge b-open\">24/7 emergency</span>" if r["e"] else ""}{" <span class=\"badge b-check\">Low-cost / nonprofit</span>" if r["l"] else ""}</td>'
            f'<td>{esc(r["c"])}</td><td>{esc(r["p"])}{"<br>" if r["p"] and r["w"] else ""}{f"<a href=\"{esc(r["w"])}\" rel=\"noopener nofollow\" target=\"_blank\">Website</a>" if r["w"] else ""}</td></tr>'
            for r in lst)
        ne = sum(r["e"] for r in lst)
        cities = sorted({r["c"] for r in lst}, key=lambda c: -sum(1 for r in lst if r["c"] == c))[:5]
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/find-a-vet/">Find a vet</a> / {name}</div>
<h1>Vets in {name}</h1>
<p class="lede">{len(lst):,} veterinary clinics in {name}, including {ne} listed as 24/7 emergency. <a href="/find-a-vet/?state={stc}">Search by city or ZIP</a>.</p>
<table class="list"><thead><tr><th>Clinic</th><th>City</th><th>Contact</th></tr></thead><tbody>{rows_html}</tbody></table>
<div class="note">From OpenStreetMap; details can change. Call ahead.</div>"""
        write(f"/find-a-vet/{slugify(name)}/", page(f"Vets in {name}: {len(lst):,} Veterinary Clinics & Emergency Vets | {BRAND}",
            f"Find a vet in {name}: {len(lst):,} clinics in {', '.join(cities)} and more, including 24/7 emergency and low-cost clinics.",
            body, f"/find-a-vet/{slugify(name)}/", crumbs_ld([("Home", "/"), ("Find a vet", "/find-a-vet/"), (name, f"/find-a-vet/{slugify(name)}/")])))


def build_sitemap():
    today = date.today().isoformat()
    skip = {"/404.html", "/thanks/", "/oops/", "/request/"}
    urls = []
    for f in sorted(DIST.rglob("index.html")):
        u = "/" + str(f.parent.relative_to(DIST)).replace(".", "") + "/"
        u = u.replace("//", "/")
        if u not in skip:
            urls.append(u)
    sm = "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')


def build_assets(rows, optins):
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "site.css").write_text(CSS.strip() + "\n")
    for f in list((ROOT / "src" / "art").glob("*.svg")) + list((ROOT / "src" / "art").glob("*.png")):
        shutil.copy(f, DIST / "assets" / f.name)
    (DIST / "favicon.svg").write_text(
        LOGO.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '))
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
        lookup[r["slug"]] = {"org": r["org"], "city": r["city"], "state": r["state"], "email_main": em, "email_program": r.get("email_program", ""), "noprog": r["status"] == NOPROG, "url": r.get("url", ""), "source": r.get("source", "")}
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
    progs = [r for r in rows if r["status"] != NOPROG]
    build_home(progs, rows)
    build_states(rows)
    build_listings(rows)
    build_cats(progs)
    build_forms(rows)
    build_static_pages(rows)
    build_events(rows)
    build_cities(progs)
    build_guides(progs)
    build_vets()
    build_sitemap()
    n = sum(1 for _ in DIST.rglob("*.html"))
    print(f"Built {len(progs)} programs + {len(rows)-len(progs)} other shelters, {n} pages into {DIST}")


if __name__ == "__main__":
    main()
