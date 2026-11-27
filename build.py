#!/usr/bin/env python3
"""ShelterDayOut static site builder.

Reads data/listings.json (+ data/optins.json) and writes the full site to dist/.
Re-run any time the data changes; the monthly update task does exactly that.
"""
import html
import collections
import hashlib
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote
import sys
import seo

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
    # Per-state sweep files (data/sweep/XX.json) hold the full, revised list for that state and replace it.
    sweep_dir = ROOT / "data" / "sweep"
    if sweep_dir.exists():
        for f in sorted(sweep_dir.glob("*.json")):
            st = f.stem.upper()
            try:
                state_rows = json.loads(f.read_text())
            except Exception as e:
                print("WARNING: skipping bad sweep file", f, e)
                continue
            if isinstance(state_rows, list) and state_rows and all(r.get("state") == st for r in state_rows):
                rows = [r for r in rows if r["state"] != st] + state_rows
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
        # a website field must hold one address: keep the first, and encode stray spaces
        u = (r.get("url") or "").split(";")[0].strip()
        r["url"] = u.replace(" ", "%20")
        # dead links (found by the weekly link check) are hidden until the monthly refresh fixes them
        if is_dead(r.get("url")):
            r["url"] = ""
        if is_dead(r.get("source")):
            r["source"] = ""
        for e in r.get("events", []):
            if is_dead(e.get("url")):
                e["url"] = ""
        r["map"] = map_url(r["org"], r["city"], r["state"])
        r["phone"], r["tel"] = clean_phone(r.get("phone", ""))
        r["requests"] = bool(r.get("email_main") or r.get("email_program") or optins.get(slug)) or r["status"] == NOPROG
    rows.sort(key=lambda r: (r["state"], STATUS_ORDER[r["status"]], r["city"], r["org"]))
    return rows, optins


CSS = """
#nores[hidden]{display:none!important}
#nores ul{margin:.4em 0 .2em;padding-left:1.2em}
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


OG = {}


def page(title, desc, body, path, extra_head="", canonical=True):
    title = seo.fit_title(title, BRAND); desc = seo.fit_desc(desc)
    url = SITE + path
    if canonical:
        OG[path] = seo.og_title(title, BRAND)
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
<meta property="og:image" content="{SITE}/og.php?p={quote(path, safe='/')}">
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
<nav class="main"><a href="/#find">Find an outing</a><a href="/events/">Adoption events</a><a href="/cats/">Cats</a><a href="/guides/">Guides</a><a href="/find-a-vet/">Find a vet</a><a href="/for-shelters/">For shelters</a><a href="https://shelteradoption.com/" rel="noopener">Adopt</a></nav>
</div></header>
<main><div class="wrap">
{body}
{PAWROW}
</div></main>
<footer class="site"><div class="wrap">
<div class="logo">{LOGO}<span>Shelter<b>DayOut</b></span></div>
<p><a href="/guides/">All guides</a><a href="/rent-a-dog/">Rent or borrow a dog</a><a href="/shelter-dog-sleepovers/">Shelter dog sleepovers</a><a href="/hike-with-a-shelter-dog/">Hike with a shelter dog</a><a href="/doggy-day-out/">Doggy day out</a><a href="/foster-a-dog-for-a-day/">Foster a dog for a day</a><a href="/volunteer-at-an-animal-shelter/">Volunteer at a shelter</a><a href="/cities/">Browse by city</a><a href="/events/">Adoption events</a></p>
<p><a href="/about/">About</a><a href="/how-it-works/">How it works</a><a href="/cats/">Cats</a><a href="/for-shelters/">For shelters</a><a href="/suggest/">Suggest a shelter</a><a href="/report/">National report</a><a href="/new-programs/">New programs</a><a href="/for-shelters/badge/">Website badge</a><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
<p>{BRAND} is a free directory. We don't run outings or handle bookings; each shelter sets its own rules. Listings are checked monthly, but details change, so confirm with the shelter before you go.</p>
<p>Ready to adopt? <a href="https://shelteradoption.com/" rel="noopener">ShelterAdoption</a>, our sister site, lists every shelter near you plus upcoming adoption events.</p>
<p class="fine">Some shelter locations: &copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License. Distances use <a href="https://www.geonames.org/" rel="noopener">GeoNames</a> city data (CC BY 4.0).</p>
<p>{BRAND} is a program of <a href="https://charitygood.org" rel="noopener">Charity Good</a>. &copy; {date.today().year} Charity Good. All rights reserved. Scraping or copying this site's content is not allowed; see <a href="/terms/#no-scraping">Terms</a>.</p>
</div></footer>
<script>(function(){{try{{var d={{p:location.pathname,r:document.referrer,w:innerWidth}},s=function(e){{d.e=e;var b=JSON.stringify(d);if(navigator.sendBeacon)navigator.sendBeacon('/api/hit.php',new Blob([b],{{type:'application/json'}}));else fetch('/api/hit.php',{{method:'POST',body:b,keepalive:true}});}};s(0);var once=function(){{s(1);['scroll','click','touchstart','keydown','mousemove'].forEach(function(t){{removeEventListener(t,once,true)}})}};['scroll','click','touchstart','keydown','mousemove'].forEach(function(t){{addEventListener(t,once,{{capture:true,passive:true}})}})}}catch(e){{}}}})();</script>
</body>
</html>
"""


def source_html(r):
    """Source line on a listing: only real news or government pages, each its own link (fields can hold several, separated by ';')."""
    skip = ("adoptapet.com", "petfinder.com", "facebook.com", "yelp.", "shelterlist", "causeiq")
    urls = [u.strip() for u in (r.get("source") or "").split(";") if u.strip().startswith("http") and not any(x in u for x in skip) and not is_dead(u.strip())]
    if not urls:
        return ""
    links = ", ".join(f'<a href="{esc(u)}" rel="noopener nofollow" target="_blank">{"state record" if ".gov" in u else "news coverage"}</a>' for u in urls[:3])
    return f'<p class="animal">Source: {links}</p>'


def write(path, content):
    p = DIST / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    if len(content.encode()) > 900_000:  # GoDaddy's server returns 500 for HTML pages over about 1 MB
        raise SystemExit(f"Page too big for the host ({len(content.encode()):,} bytes, limit 900,000): {path}")
    if str(p).endswith('.html'):
        content = seo.add_tracer(content, 'SDO', path)
    p.write_text(content)


def row_html(r, show_state=True):
    loc = f"{esc(r['city'])}, {r['state']}" if show_state else esc(r["city"])
    types = " ".join(r["types"])
    ll = coords(r["city"], r["state"])
    return f"""<tr data-ll="{(str(ll[0]) + ',' + str(ll[1])) if ll else ''}" data-state="{r['state']}" data-animals="{esc(r['animals'])}" data-types="{types}" data-status="{esc(r['status'])}" data-q="{esc((r['org']+' '+r['city']+' '+r['state_name']+' '+r['program']).lower())}">
<td class="org"><a href="/listings/{r['slug']}/">{esc(r['org'])}{seo.tracer("SDO", "/listings/" + r["slug"] + "/")}</a><div class="prog">{esc(r['program'])}</div></td>
<td>{loc}</td>
<td>{''.join(ICONS[t] for t in r['types'])}{esc(r['offers'])}<div class="animal">{esc(r['animals'])}</div></td>
<td>{badge(r['status'])}</td>
</tr>"""


def table(rows, show_state=True, lazy_src=None):
    body = "\n".join(row_html(r, show_state) for r in rows)
    if lazy_src:  # home page: rows are loaded only when someone searches
        (DIST / lazy_src.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
        (DIST / lazy_src.lstrip("/")).write_text(json.dumps(body, ensure_ascii=False))
        v = hashlib.md5(body.encode()).hexdigest()[:10]
        return f"""<table class="list" id="results" hidden>
<thead><tr><th>Shelter and program</th><th>Location</th><th>What you can do</th><th>Who can go</th></tr></thead>
<tbody data-src="{lazy_src}?v={v}"></tbody></table>"""
    return f"""<table class="list" id="results">
<thead><tr><th>Shelter and program</th><th>Location</th><th>What you can do</th><th>Who can go</th></tr></thead>
<tbody>
{body}
</tbody></table>"""


NEAR_JS = """<script>
window.sdoAlts=function(pl,t){if(!pl||!pl.alts||!pl.alts.length)return '';var nm=t.replace(/\\b\\w/g,function(m){return m.toUpperCase();});return '<p>Looking for a different '+nm.replace(/[<>&"]/g,'')+'? '+pl.alts.slice(0,8).map(function(a){return '<a href="?q='+encodeURIComponent(t)+'&amp;state='+a+'">'+nm.replace(/[<>&"]/g,'')+', '+a+'</a>';}).join(' &middot; ')+'</p>';};
window.sdoNear=function(t,s,cands,done){
 t=(t||'').toLowerCase().replace(/,?\\s+[a-z]{2}$/,'').replace(/[^a-z .'-]/g,'').trim();
 if(t.length<3){done(null,[]);return;}
 fetch('/assets/places/'+(s||'US')+'.json').then(function(r){return r.json();}).then(function(d){
  var p=null,ps=s;
  var alts=[];
  if(s){p=d[t];}else{for(var k in d){if(d[k][t]){if(!p){p=d[k][t];ps=k;}else{alts.push(k);}}}}
  if(!p){done(null,[]);return;}
  var R=3958.8,rad=Math.PI/180,out=[];
  cands.forEach(function(c){if(!c.ll)return;var a=c.ll[0]*rad,b=p[0]*rad,dl=(c.ll[1]-p[1])*rad;
   var x=Math.sin((c.ll[0]-p[0])*rad/2),y=Math.sin(dl/2),h=x*x+Math.cos(a)*Math.cos(b)*y*y;c.mi=Math.round(2*R*Math.asin(Math.sqrt(h)));if(c.mi<=200)out.push(c);});
  out.sort(function(a,b){return a.mi-b.mi;});
  done({name:t.replace(/\\b\\w/g,function(m){return m.toUpperCase();}),st:ps,alts:alts},out.slice(0,10));
 }).catch(function(){done(null,[]);});
};
</script>"""


FILTER_JS = """<script>
(function(){
 var q=document.getElementById('q'),st=document.getElementById('f-state'),an=document.getElementById('f-animal'),ty=document.getElementById('f-type'),pub=document.getElementById('f-public'),cnt=document.getElementById('count');
 var tb=document.querySelector('#results tbody'),lazy=!!(tb&&tb.dataset.src),loaded=!lazy,tbl=document.getElementById('results');
 var rows=lazy?[]:[].slice.call(document.querySelectorAll('#results tbody tr'));
 function load(){if(loaded||load.busy)return;load.busy=1;fetch(tb.dataset.src).then(function(r){if(!r.ok)throw 0;return r.json();}).then(function(h){tb.innerHTML=h;rows=[].slice.call(tb.querySelectorAll('tr'));loaded=true;run();}).catch(function(){load.busy=0;});}
 function run(){
  var t=(q&&q.value||'').trim().toLowerCase(),s=st?st.value:'',a=an.value,y=ty.value,p=pub.checked,n=0;
  if(lazy){var any=t||s||a||y||p;if(!any){if(tbl)tbl.hidden=true;cnt.textContent='';if(box){box.hidden=true;box.innerHTML='';}return;}if(!loaded){cnt.textContent='Searching\u2026';load();return;}if(tbl)tbl.hidden=false;}
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
  nores(n,t,s,a,y,p);
 }
 // No matching program: show shelters without a program yet that match, the programs in the chosen state, and the state page.
 var box=document.getElementById('nores'),others=null,SN=window.SDO_STATES||{};
 function esc(x){return String(x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
 function nores(n,t,s,a,y,p){
  if(!box)return;
  if(n>0||(!t&&!s)){box.hidden=true;box.innerHTML='';return;}
  var inState=s?rows.filter(function(r){return r.dataset.state===s;}).length:0;
  var html='<p><b>No day-out programs match'+(t?' &ldquo;'+esc(t)+'&rdquo;':'')+(s?' in '+esc(SN[s]||s):'')+' yet.</b></p>';
  var tips=[];
  if(t&&s&&inState)tips.push('<a href="#" data-act="state">See all '+inState+' program'+(inState===1?'':'s')+' in '+esc(SN[s]||s)+'</a>');
  if(a||y||p)tips.push('<a href="#" data-act="clear">Clear the animal, type and public filters</a>');
  if(s)tips.push('<a href="/states/'+esc((SN[s]||'').toLowerCase().replace(/[^a-z0-9]+/g,'-'))+'/">Every shelter in '+esc(SN[s]||s)+'</a>');
  if(tips.length)html+='<ul><li>'+tips.join('</li><li>')+'</li></ul>';
  box.innerHTML=html+'<div id="nores-n"></div><div id="nores-o"></div>';box.hidden=false;
  if(!t)return;
  var show=function(){var m=others.filter(function(o){return (!s||o[3]===s)&&(o[1]+' '+o[2]+' '+o[3]+' '+(SN[o[3]]||'')).toLowerCase().indexOf(t)>=0;}).slice(0,25);
   var el=document.getElementById('nores-o');if(!el||!m.length)return;
   el.innerHTML='<p>Shelters'+(s?' in '+esc(SN[s]||s):'')+' matching &ldquo;'+esc(t)+'&rdquo; that don&rsquo;t run a program yet. Ask them for one:</p><ul>'+m.map(function(o){return '<li><a href="/listings/'+o[0]+'/">'+esc(o[1])+'</a> ('+esc(o[2])+', '+o[3]+') &middot; <a href="/request/?listing='+o[0]+'">Request a day out</a></li>';}).join('')+'</ul>';};
  if(others){show();}else{fetch('/assets/others.json').then(function(r){return r.json();}).then(function(j){others=j;show();}).catch(function(){});}
  var near=function(){if(!window.sdoNear)return;var c=rows.map(function(tr){var l=tr.dataset.ll;var a=tr.querySelector('a');return {name:a?a.textContent:'',url:a?a.getAttribute('href'):'#',loc:(tr.cells[1]?tr.cells[1].textContent.trim():''),st:tr.dataset.state,ll:l?l.split(',').map(Number):null,prog:1};});
   (others||[]).forEach(function(o){if(o[4])c.push({name:o[1],url:'/listings/'+o[0]+'/',st:o[3],cityName:o[2],ll:o[4],prog:0,slug:o[0]});});
   window.sdoNear(t,s,c,function(pl,list){var el=document.getElementById('nores-n');if(!el||!pl||!list.length)return;
    el.innerHTML=window.sdoAlts(pl,t)+'<p><b>Nearest to '+esc(pl.name)+', '+esc(pl.st)+':</b></p><ul>'+list.map(function(x){return '<li><a href="'+x.url+'">'+esc(x.name)+'</a>'+(x.cityName?' ('+esc(x.cityName)+', '+x.st+')':(x.loc?' ('+esc(x.loc)+')':''))+' &middot; about '+x.mi+' miles'+(x.prog?' &middot; <b>has a day-out program</b>':' &middot; <a href="/request/?listing='+x.slug+'">Request a day out</a>')+'</li>';}).join('')+'</ul>';});};
  if(others){near();}else{fetch('/assets/others.json').then(function(r){return r.json();}).then(function(j){others=j;near();}).catch(function(){});}
 }
 if(box)box.addEventListener('click',function(e){var x=e.target.closest('a[data-act]');if(!x)return;e.preventDefault();
  if(x.dataset.act==='state'&&q)q.value='';if(x.dataset.act==='clear'){an.value='';ty.value='';pub.checked=false;}run();});
 [q,st,an,ty,pub].forEach(function(el){if(el){el.addEventListener('input',run);el.addEventListener('change',run);}});
 var f=document.getElementById('sform'),res=document.getElementById('results');
 if(f){f.addEventListener('submit',function(e){e.preventDefault();run();if(q)q.blur();var tgt=(box&&!box.hidden)?box:res;if(tgt){tgt.scrollIntoView({behavior:'smooth',block:'start'});}});}
 var u=new URLSearchParams(location.search);
 if(u.get('q')&&q){q.value=u.get('q');}
 if(u.get('state')&&st){st.value=u.get('state').toUpperCase();}
 if(u.get('animal')){an.value=u.get('animal');}
 if(u.get('type')){ty.value=u.get('type');}
 if(u.get('public')){pub.checked=true;}
 run();
})();
</script>"""


def filters(with_state=True, states_present=(), state_code=""):
    state_sel = ""
    if with_state:
        opts = "".join(f'<option value="{k}">{v}</option>' for k, v in STATES.items() if k in states_present)
        state_sel = f'<div><label for="f-state">State</label><select id="f-state" name="state"><option value="">All states</option>{opts}</select></div>'
    search_box = ('<div style="flex:1"><label for="q">City, shelter or program</label><input type="text" id="q" name="q" enterkeyhint="search" placeholder="e.g. Austin, Pasadena Humane, sleepover"></div>' if with_state
                  else f'<div style="flex:1"><label for="q">City or shelter</label><input type="text" id="q" name="q" enterkeyhint="search" placeholder="Type a city or shelter name"></div>' + (f'<input type="hidden" id="f-state" value="{state_code}">' if state_code else ""))
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
<p class="count" id="count" aria-live="polite"></p>
<div class="note" id="nores" hidden></div>
<script>window.SDO_STATES={json.dumps(STATES)};</script>"""


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


def home_highlights(rows):
    """A short, varied sample of programs open to the public: one per state, states with the most programs first."""
    by = {}
    for r in rows:
        if r["status"] == "Open to public":
            by.setdefault(r["state"], []).append(r)
    picks = [sorted(v, key=lambda r: (-len(r["types"]), r["org"]))[0] for k, v in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0]))][:12]
    if not picks:
        return ""
    cards = "".join(f'<div class="card"><h3><a href="/listings/{r["slug"]}/">{esc(r["program"] or r["org"])}</a></h3>{esc(r["org"])}, {esc(r["city"])}, {r["state"]}<div class="animal">{esc(r["offers"])}</div></div>' for r in picks)
    return f'''<h2>Programs open to the public</h2>
<div class="grid3">{cards}</div>
<p><a href="/new-programs/">New programs this month</a> &middot; <a href="/report/">National report</a> &middot; <a href="/events/">Adoption events</a></p>'''


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
{filters(True, STATES.keys())}
{table(rows, lazy_src="/assets/home-programs.json")}
<p class="animal">Type a city, shelter or program, or pick a state or filter, to see matching programs. Or browse by state below.</p>
</section>
{home_highlights(rows)}
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
<div class="band"><div style="flex:1 1 360px"><h2>Ready to adopt?</h2><p>Our sister site ShelterAdoption lists {len(all_rows):,} animal shelters and humane societies in every state, plus upcoming adoption events.</p></div><a class="btn" href="https://shelteradoption.com/" rel="noopener">Find a shelter to adopt from</a></div>
<h2>Guides</h2>
<div class="grid3">
<div class="card"><h3><a href="/rent-a-dog/">Rent or borrow a dog</a></h3>Why borrowing a shelter dog beats renting one, and how it works.</div>
<div class="card"><h3><a href="/shelter-dog-sleepovers/">Shelter dog sleepovers</a></h3>Host a shelter dog for a night or a weekend.</div>
<div class="card"><h3><a href="/hike-with-a-shelter-dog/">Hike with a shelter dog</a></h3>Trail buddy programs that get dogs outdoors.</div>
</div>
<p><a href="/guides/">See all guides</a></p>
<div class="band"><div style="flex:1 1 360px"><h2>Run a shelter?</h2><p>Get listed for free, update your details, or choose where outing requests go.</p></div><a class="btn" href="/for-shelters/">For shelters</a></div>
{NEAR_JS}{FILTER_JS}"""
    write("/", page(
        "Dog Day Out Near Me: Borrow (or 'Rent') a Shelter Dog for the Day, Free | ShelterDayOut",
        f"Find a doggy day out program near you: rent or borrow a shelter dog for the day, a hike or a sleepover, free. {len(all_rows):,} shelters nationwide, checked monthly.",
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
{filters(False, state_code=s)}
{table(lst, show_state=False)}
<p class="animal" style="margin-top:12px">Don't see your shelter? <a href="/suggest/">Suggest one</a>. Shelter staff can <a href="/for-shelters/">claim a listing</a>.</p>
{np_html}
{NEAR_JS}{FILTER_JS}"""
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


def _miles(a, b):
    import math
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def nearest_programs_html(r, progs, k=3):
    """The k nearest day-out programs to this shelter (excluding itself), with straight-line distance."""
    here = coords(r["city"], r["state"])
    if not here:
        return ""
    near = []
    for p in progs:
        if p["slug"] == r["slug"] or not p.get("_ll"):
            continue
        near.append((_miles(here, p["_ll"]), p))
    near.sort(key=lambda x: x[0])
    near = near[:k]
    if not near:
        return ""
    head = (f"Nearest day-out programs to {esc(r['city'])}" if r["status"] == NOPROG
            else f"Other day-out programs near {esc(r['city'])}")
    items = "".join(
        f'<li><a href="/listings/{p["slug"]}/">{esc(p["org"])}</a> &middot; {esc(p["city"])}, {p["state"]} &middot; '
        f'{"under 1 mile" if d < 1 else f"about {d:,.0f} miles"}'
        f'{" &middot; " + esc(p["offers"]) if p.get("offers") else ""}</li>'
        for d, p in near)
    intro = ("This shelter doesn't list a day-out program yet, but these shelters nearby do:"
             if r["status"] == NOPROG else "More shelters nearby that let you take a dog out:")
    return f'<h2>{head}</h2><p class="animal">{intro}</p><ul class="evlist">{items}</ul>'


def build_listings(rows):
    progs = [p for p in rows if p["status"] != NOPROG]
    for p in progs:
        p["_ll"] = coords(p["city"], p["state"])
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
            **({"telephone": "+1-" + r["tel"][2:5] + "-" + r["tel"][5:8] + "-" + r["tel"][8:12]} if r.get("tel") else {}),
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
{phone_dd(r)}{contact_html(r)}<dt>Last checked</dt><dd>{esc(r['checked'])}</dd>
</dl>
{note}
{f'<h2>Upcoming events</h2><ul class="evlist">{events_html(r, upcoming(r))}</ul>' if upcoming(r) else ""}
<p>{req}{go} {call_btn(r)}</p>
{map_line(r)}
{source_html(r)}
{nearest_programs_html(r, progs)}
<p class="animal">Thinking of adopting? <a href="https://shelteradoption.com/shelters/{r['slug']}/" rel="noopener">See {esc(name)} on ShelterAdoption</a> for its adoptable pets and adoption events.</p>
<div class="note">Rules, hours and fees are set by the shelter and can change. Always confirm with the shelter before you go. {BRAND} isn't affiliated with this shelter and doesn't arrange outings.</div>
<p class="animal">Is something out of date? <a href="/suggest/?type=report&amp;listing={r['slug']}">Report a problem</a>. Work at this shelter? <a href="/for-shelters/?listing={r['slug']}">Claim this listing</a> to update it or receive outing requests, and add our <a href="/for-shelters/badge/?listing={r['slug']}">free website badge</a>.</p>"""
        write(f"/listings/{r['slug']}/", page(
            (f"{name} ({r['city']}, {r['state']}): Request a Dog Day Out | {BRAND}" if r["status"] == NOPROG
             else f"{name} ({r['city']}, {r['state']}): Dog Day Out Program | {BRAND}"),
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
        f"Cat Lounge Near Me: Shelter Cat Lounges, Sleepovers & Staycations | {BRAND}",
        "Find a shelter cat lounge near you, or host a shelter cat for a sleepover or staycation. Rescue cat lounges and kitten fostering, checked monthly.",
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
<label style="display:flex;gap:8px;align-items:flex-start;font-size:.9rem"><input type="checkbox" name="confirm" value="yes" required style="width:auto;margin-top:4px"> <span>I work for or volunteer with this organization and can speak for it, and I agree to the <a href="/terms/">Terms</a> and <a href="/privacy/">Privacy policy</a>.</span></label>""",
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
<label style="display:flex;gap:8px;align-items:flex-start;font-size:.9rem"><input type="checkbox" name="confirm" value="yes" required style="width:auto;margin-top:4px"> <span>I'm 18 or older, I understand the shelter decides whether to approve the outing and sets its own rules, and I agree to the <a href="/terms/">Terms</a> and <a href="/privacy/">Privacy policy</a>, including sending my details to this shelter.</span></label>
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

    write("/terms/", page(f"Terms of Use | {BRAND}", f"Terms of use for {BRAND}.", legal_terms(BRAND, "dayout", CONTACT), "/terms/"))
    write("/privacy/", page(f"Privacy Policy | {BRAND}", f"Privacy policy for {BRAND}.", legal_privacy(BRAND, "dayout", CONTACT), "/privacy/"))

    write("/404.html", page(f"Page not found | {BRAND}", "Page not found.",
        f"""<h1>Page not found</h1><p class="lede">That page doesn't exist or has moved.</p><p><a class="btn" href="/">Find a shelter outing</a></p>""", "/404.html", canonical=False))


def upcoming(r):
    today = date.today().isoformat()
    return sorted([e for e in r.get("events", []) if (e.get("end") or e.get("date", "")) >= today], key=lambda e: e["date"])


def ev_when(e):
    """When an event happens, for display. Events already under way read 'Now through <end>'."""
    today = date.today().isoformat()
    start, end = e.get("date", ""), e.get("end") or ""
    if end and start < today:
        return "Now through " + fmt_date(end)
    if end and end != start:
        return f"{fmt_date(start)} – {fmt_date(end)}"
    return fmt_date(start)


PLACES = None
DEAD = None


def is_dead(u):
    global DEAD
    if DEAD is None:
        f = ROOT / "data" / "dead_links.json"
        DEAD = set(json.loads(f.read_text()).get("dead", [])) if f.exists() else set()
    return bool(u) and u in DEAD


LEGAL_ORG = "Charity Good"
LEGAL_ADDR = "121 South Tejon Street, Suite 900, Colorado Springs, CO 80903"


def legal_terms(brand, kind, contact, sdo="https://shelterdayout.com"):
    """Terms of use shared by both sites. kind: 'dayout' or 'adopt'."""
    upd = date.today().strftime('%B %-d, %Y')
    if kind == "dayout":
        what = ("We list programs run by independent animal shelters and rescues. We don't run outings, sleepovers, visits "
                "or adoptions. Each shelter decides who may take part and sets its own rules, fees, agreements and waivers, "
                "which govern your outing.")
        extra = f"""<h2>Outing requests</h2>
<p>You can send a shelter an outing request through the site. We email your request to the shelter's public contact address and, where it has one, its program address, and keep a copy. Sending a request doesn't guarantee an outing. The shelter alone decides whether to approve it, and we aren't a party to any arrangement between you and a shelter. Requests require you to be 18 or older.</p>
<h2>Animals and safety</h2>
<p>Animals can be unpredictable. You're responsible for following the shelter's instructions and for your own conduct and safety, and that of anyone with you, during any outing or visit.</p>"""
        corr = f'<a href="/for-shelters/">For shelters</a> page'
    else:
        what = ("We list independent animal shelters, humane societies, rescues and animal control agencies and link to their "
                "own websites. We don't place animals, process adoptions, collect fees or speak for any shelter. Each shelter "
                "sets its own adoption policies, fees and requirements.")
        extra = f"""<h2>Adopting</h2>
<p>Adoption decisions, health information and animal histories come from the shelter, not from us. Ask the shelter about an animal's health and behavior before you adopt. Nothing on the site is veterinary, legal or professional advice.</p>"""
        corr = f'<a href="{sdo}/for-shelters/">For shelters</a> page'
    return f"""<h1>Terms of use</h1>
<div class="prose">
<p>Last updated {upd}.</p>
<p>{brand} is a free program of {LEGAL_ORG} (charitygood.org), a Colorado nonprofit corporation and 501(c)(3) public charity ("{LEGAL_ORG}", "we", "us"). By using {brand} (the "site") you agree to these terms. If you don't agree, please don't use the site.</p>
<h2>A free directory, not a service provider</h2>
<p>{brand} is an information directory. {what} Listing a shelter doesn't mean the shelter endorses us or that we endorse it, and we're not affiliated with any listed organization unless its listing says so.</p>
<h2>Where the information comes from</h2>
<p>Listings are factual information (names, cities, websites, public phone numbers and emails, program descriptions and event dates) taken from each shelter's own public website or from government sources, written as short factual summaries. Some locations come from OpenStreetMap (&copy; OpenStreetMap contributors, available under the <a href="https://opendatacommons.org/licenses/odbl/" rel="noopener">Open Database License</a>) and distances use <a href="https://www.geonames.org/" rel="noopener">GeoNames</a> city data (<a href="https://creativecommons.org/licenses/by/4.0/" rel="noopener">CC BY 4.0</a>). We check listings regularly, but details change and may be wrong or out of date. Always confirm with the shelter.</p>
{extra}
<h2>Names and trademarks</h2>
<p>Shelter names, logos and trademarks belong to their owners and are used only to identify each organization. Corrections and removal requests are welcome through the {corr} or by email.</p>
<h2>Acceptable use</h2>
<p>Don't submit false information, impersonate a shelter or another person, spam shelters through our forms, or try to disrupt or break into the site.</p>
<h2 id="no-scraping">No scraping or copying</h2>
<p>{brand}'s directory, including its selection and arrangement of listings, its descriptions and summaries, its program and event research, its guides, reports and graphics, is the work of {LEGAL_ORG}. You may use the site to find shelters and programs for yourself, and you may quote an individual fact or a figure from our reports with credit and a link to the page.</p>
<p>Without our written permission you may not: (a) use any robot, spider, scraper, script, crawler, headless or automated browser, AI agent or similar tool, or any manual process, to copy, download, extract or collect pages, listings or data from the site in bulk; (b) disguise such a tool as an ordinary browser, rotate network addresses or otherwise get around the site's technical limits or blocks; (c) republish, mirror, frame or redistribute the site or a substantial part of it; or (d) use material from the site to build, update or supply another directory, database, list, app, product or service, or to train or improve any artificial intelligence or machine-learning model.</p>
<p>Search engines and other crawlers that identify themselves truthfully and follow the site's <a href="/robots.txt">robots.txt</a> file may index its public pages so people can find them. To ask for permission or a data license, email <a href="mailto:{contact}">{contact}</a>.</p>
<p>Breaking this section ends your permission to use the site. We may block access and seek every remedy available under the law, including court orders, damages, compensation for our losses (including loss of future income, such as lost revenue and donations), and recovery of our costs and attorneys' fees where the law allows. We take this very seriously. We monitor the internet daily for copycat and clone sites, and our pages and data contain hidden tracers that let us identify copied content and find who copied it. We use cutting-edge anti-copying technology and AI to hunt down copiers. If you copy our site or data, we will find out. Information that comes from OpenStreetMap or GeoNames remains available under its own license, and this section doesn't limit any rights you have under those licenses.</p>
<h2>Links to other sites</h2>
<p>We link to shelters' and other organizations' websites for your convenience. We don't control those sites and aren't responsible for their content, policies or practices.</p>
<h2>No warranties</h2>
<p>The site is provided "as is" and "as available", without warranties of any kind, express or implied, including accuracy, completeness, fitness for a particular purpose and non-infringement.</p>
<h2>Limitation of liability</h2>
<p>To the fullest extent the law allows, {LEGAL_ORG} and its directors, officers and volunteers aren't liable for any indirect, incidental, special or consequential damages, or for any injury, loss, damage or dispute arising from an outing, visit, adoption, request, a listed organization's actions, or your use of the site. Our total liability for any claim relating to the site is limited to $100. Because the site is free, these limits are a fair basis for providing it.</p>
<h2>Indemnity</h2>
<p>You agree to hold {LEGAL_ORG} harmless from claims arising from your misuse of the site or your breach of these terms.</p>
<h2>Copyright concerns</h2>
<p>The site's design, text and graphics are &copy; {date.today().year} {LEGAL_ORG}, except data credited above. If you believe something on the site infringes your rights, email <a href="mailto:{contact}">{contact}</a> with the page address and details and we'll review it promptly and remove it if appropriate.</p>
<h2>Governing law</h2>
<p>These terms are governed by the laws of the State of Colorado, without regard to its conflict-of-law rules. Any dispute will be handled in the state or federal courts located in Colorado.</p>
<h2>Changes and contact</h2>
<p>We may update these terms; the date above shows the latest version, and continued use means you accept the update. Questions: <a href="mailto:{contact}">{contact}</a>. Mail: {LEGAL_ORG}, {LEGAL_ADDR}.</p>
</div>"""


def legal_privacy(brand, kind, contact, sdo="https://shelterdayout.com"):
    upd = date.today().strftime('%B %-d, %Y')
    forms = ("If you send a form (an outing request, a shelter suggestion, a correction or a listing claim), we collect what you "
             "enter, such as your name, email, phone and message." if kind == "dayout" else
             f"The site has no forms of its own. Suggestions, corrections and listing claims are sent through our sister site ShelterDayOut and handled under its <a href=\"{sdo}/privacy/\">privacy policy</a>.")
    share = ("If you send an outing request, we email it (your name, contact details, preferred dates and message) to the shelter "
             "you chose so it can reply to you, with a copy to our own inbox. If the shelter doesn't run a program yet, we hold your "
             "request and include it in one monthly note to that shelter. Shelters handle your information under their own policies."
             if kind == "dayout" else "")
    return f"""<h1>Privacy policy</h1>
<div class="prose">
<p>Last updated {upd}.</p>
<p>{brand} is a free program of {LEGAL_ORG} (charitygood.org), a nonprofit. This policy explains what we collect and how we use it.</p>
<h2>What we collect</h2>
<p>You can browse {brand} without an account and without giving us any personal information. {forms}</p>
<p>Our web host keeps standard server logs (such as IP address, browser and pages requested) for security and troubleshooting. To count visits we use our own cookie-free counter: it records the page, the site you came from, your device type and browser family, and a daily anonymous code that can't be traced back to you. It stores no IP address and sets no cookies. The site sets no tracking cookies and uses no advertising trackers.</p>
<h2>Third-party services</h2>
<p>Pages load fonts from Google Fonts, so your browser connects to Google's servers, which receive your IP address under <a href="https://policies.google.com/privacy" rel="noopener">Google's privacy policy</a>. Links to shelters and maps take you to other sites with their own policies.</p>
<h2>How we use and share it</h2>
<p>We use what you send only to respond to you, keep listings accurate and run the site. {share} We don't sell, rent or trade personal information, and we don't share it with advertisers.</p>
<h2>Shelter contact details</h2>
<p>Listings show organizations' public business contact details (website, main phone and public email) as published on their own websites or government pages. To correct or remove a listing's details, email <a href="mailto:{contact}">{contact}</a>.</p>
<h2>Keeping and deleting</h2>
<p>We keep form submissions for up to 24 months and server logs for as long as our host keeps them, then delete them. To see, correct or delete what you sent us, email <a href="mailto:{contact}">{contact}</a> and we'll respond within 30 days, whatever state you live in.</p>
<h2>Security</h2>
<p>The site uses HTTPS, and form data is stored outside the public website. No method of storage or transmission is completely secure.</p>
<h2>Children</h2>
<p>The site isn't directed to children under 13, and we don't knowingly collect their information.{" Outing requests require you to be 18 or older." if kind == "dayout" else ""}</p>
<h2>Changes and contact</h2>
<p>We'll post any changes here with a new date. Questions: <a href="mailto:{contact}">{contact}</a>. Mail: {LEGAL_ORG}, {LEGAL_ADDR}.</p>
</div>"""


def clean_phone(raw):
    """Return (display, tel-link) for a US phone, or ("", "") if it isn't a valid 10-digit number.
    Display is "(555) 555-5555" plus " ext. N" when given; tel uses +1 and a pause before the extension."""
    raw = (raw or "").strip()
    if not raw:
        return "", ""
    m = re.match(r"^(.*?)(?:\s*(?:ext\.?|x|extension)\s*(\d{1,6}))?\s*$", raw, re.I)
    main, ext = m.group(1), m.group(2)
    d = re.sub(r"\D", "", main)
    if len(d) == 11 and d[0] == "1":
        d = d[1:]
    if len(d) != 10 or d[0] in "01":
        return "", ""
    disp = f"({d[:3]}) {d[3:6]}-{d[6:]}" + (f" ext. {ext}" if ext else "")
    tel = f"+1{d}" + (f",{ext}" if ext else "")
    return disp, tel


def phone_dd(r):
    """<dt>/<dd> pair with a tap-to-call link, or "" when no phone."""
    if not r.get("phone"):
        return ""
    return f'<dt>Phone</dt><dd><a href="tel:{r["tel"]}">{esc(r["phone"])}</a></dd>\n'


def call_btn(r):
    return f'<a class="btn alt" href="tel:{r["tel"]}">Call {esc(r["phone"])}</a> ' if r.get("phone") else ""


def map_line(r):
    what = "directions and hours" if r.get("phone") else "directions, hours and phone"
    return f'<p class="animal"><a href="{esc(r["map"])}" rel="noopener nofollow" target="_blank">Find {esc(r["org"])} on the map</a> for {what}.</p>'


def map_url(name, city, state, street=""):
    from urllib.parse import quote_plus
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(" ".join(x for x in (name, street, city, state) if x))


def coords(city, state):
    """Approximate [lat, lon] of a US city from data/us_places.json (GeoNames cities1000, CC BY 4.0), or None."""
    global PLACES
    if PLACES is None:
        f = ROOT / "data" / "us_places.json"
        PLACES = json.loads(f.read_text()) if f.exists() else {}
    st = PLACES.get(state, {})
    c = (city or "").lower().strip()
    for k in (c, re.sub(r"^(city of|town of|village of)\s+", "", c), re.sub(r"\s+(city|township|twp\.?|village|town)$", "", c),
              c.replace("saint ", "st. "), c.replace("st. ", "saint "), c.replace("mount ", "mt. "), c.replace("ft. ", "fort ")):
        if k in st:
            return st[k]
    return None


def write_places(dist):
    f = ROOT / "data" / "us_places.json"
    if not f.exists():
        return
    allp = json.loads(f.read_text())
    (dist / "assets" / "places").mkdir(parents=True, exist_ok=True)
    (dist / "assets" / "places" / "US.json").write_text(json.dumps(allp, separators=(",", ":")))
    for st, d in allp.items():
        (dist / "assets" / "places" / f"{st}.json").write_text(json.dumps(d, separators=(",", ":")))


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
    return "".join(f'<li><b>{ev_when(e)}</b> '
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
        groups += f'<li><b>{ev_when(e)}</b> · <a href="/listings/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}, {r["state"]}): {esc(e["title"])}</li>'
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
            f"Borrow a Shelter Dog in {city}, {st}: Day Out Programs | {BRAND}",
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
        title="Rent a Dog for a Day Near You (or a Puppy): Borrow a Shelter Dog Free | ShelterDayOut",
        desc="Want to rent a dog or puppy for a day? Many shelters let you borrow or foster a dog for a day free: a few hours, a hike or a sleepover. Find one near you.",
        h1="Want to rent a dog for the day? Borrow a shelter dog instead",
        types=None,
        intro="Dog rental businesses are rare and controversial, but hundreds of animal shelters let you borrow a dog for free. You get a hiking buddy or a couch companion for the day; the dog gets a break from the kennel and a better shot at adoption. Shelters call it Doggy Day Out, Dog for a Day, Foster a Dog for a Day, Field Trips, Daycations, Rent-A-Dog or Borrow a Buddy. A few shelters even let you take out puppies.",
        faqs=[("Is borrowing a shelter dog free?", "Yes, almost always. Shelters provide a leash, an Adopt Me vest and often treats and a water bowl."),
              ("What do I need to borrow a dog?", "Usually a photo ID, being 18 or older, and a signed waiver. Some shelters need a short orientation or an online booking first."),
              ("How long can I keep the dog?", "Day trips run from a couple of hours to a full day. Many shelters also offer overnights, weekend sleepovers or week-long staycations.")]),
    "/doggy-day-out/": dict(
        title="Doggy Day Out Near Me: Shelter Dog Day Out Programs in Every State | ShelterDayOut",
        desc="Find a doggy day out program near you: take an adoptable shelter dog out for the day, free. Every dog day out program we know of, checked monthly.",
        h1="Doggy day out programs near you",
        types="day",
        intro="A doggy day out (also called a dog day out, dog for a day, field trip or day trip) lets you check an adoptable dog out of a shelter for a few hours or a full day. You might go for a hike, grab a pup cup or just nap on the couch, and the photos and notes you share help the dog get adopted. It's almost always free.",
        faqs=[("What is a doggy day out program?", "A shelter program that lets the public borrow an adoptable dog for a few hours or a day. The shelter gives you a leash, an Adopt Me vest and often treats; you bring the dog back at the end of the outing."),
              ("Is there a doggy day out near me?", "Search the programs below by state or city. If your local shelter isn't listed, look it up on our home page and send a request: we tell each shelter every month how many people asked."),
              ("How old do you have to be for a dog day out?", "Usually 18 or older with a photo ID, and some shelters ask for a short orientation first. Each listing says what that shelter requires.")]),
    "/foster-a-dog-for-a-day/": dict(
        title="Foster a Dog for a Day (or a Weekend) Near You: Free Shelter Programs | ShelterDayOut",
        desc="Foster a shelter dog for a day, a night or a weekend. Find short-term foster, day trip and sleepover programs near you, free and checked monthly.",
        h1="Foster a dog for a day or a weekend",
        types=None,
        intro="Short-term fostering lets you host a shelter dog for a day, a night or a weekend without a long commitment. Shelters call it Foster for a Day, Dog for a Day, Weekend Foster, Staycation or Sleepover. It gives the dog a break from the kennel and tells the shelter how the dog acts in a home.",
        faqs=[("Can I foster a dog for just one day?", "Yes, many shelters offer day fosters or day trips. Some sign you up on the spot with an ID and waiver; others ask for a short foster application first."),
              ("Can I foster a dog for a weekend?", "Many shelters run weekend fosters or sleepovers. See the programs below, and look for Sleepover or Staycation in the list."),
              ("Does it cost anything to foster a dog for a day?", "Almost never. Shelters usually provide the leash, food and supplies for short fosters.")]),
    "/volunteer-at-an-animal-shelter/": dict(
        title="Volunteer at an Animal Shelter Near You: Dog Walking, Outings & More | ShelterDayOut",
        desc="How to volunteer at an animal shelter near you: dog walking, day trips, sleepovers and cat socializing. Find shelters with volunteer outing programs.",
        h1="Volunteer at an animal shelter near you",
        types=None,
        intro="Volunteering is the most reliable way to spend regular time with shelter animals. Most shelters ask volunteers to fill out an application, attend an orientation and commit to a few shifts a month; many then let trained volunteers walk dogs, take them on day trips or hikes, host sleepovers or socialize cats. The programs below include outings open to volunteers or to the public.",
        faqs=[("How do I start volunteering at an animal shelter?", "Find a shelter near you below, open its website and look for a Volunteer page. Most have an online application, a minimum age (often 16 or 18) and an orientation session."),
              ("Can volunteers walk dogs or take them out?", "Usually yes after training. Many shelters' day-out and hiking programs started as volunteer-only programs and some still are; each listing says who can go."),
              ("Is there a volunteer dog walking program near me?", "Most city, county and nonprofit shelters run one. Search by city on our home page, or ask the shelter about dog walking shifts.")]),
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
        if g["types"] is None and path == "/volunteer-at-an-animal-shelter/":
            lst = [r for r in lst if r["status"] in ("Open to public", "Needs check", "Volunteers only")]
        elif g["types"] is None and path == "/foster-a-dog-for-a-day/":
            lst = [r for r in lst if "Dogs" in r["animals"] and r["status"] in ("Open to public", "Needs check") and ("day" in r["types"] or "sleep" in r["types"])]
        elif g["types"] is None:
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
 function row(v){var site=v.w?'<a href="'+esc(v.w)+'" rel="noopener nofollow" target="_blank">Website</a>':'';var ph=v.p?'<a href="tel:'+esc(v.p.replace(/[^0-9+]/g,''))+'">'+esc(v.p)+'</a>':'';var mp=v.m?'<a href="'+esc(v.m)+'" rel="noopener nofollow" target="_blank">Map &amp; hours</a>':'';site=site+(site&&mp?' \u00b7 ':'')+mp;
  return '<tr><td><b>'+esc(v.n)+'</b>'+(v.e?' <span class="badge b-open">24/7 emergency</span>':'')+(v.l?' <span class="badge b-check">Low-cost / nonprofit</span>':'')+'<br><span class="animal">'+esc(v.a||'')+'</span></td><td>'+esc(v.c)+', '+v.s+(v.z?' '+esc(v.z):'')+'</td><td>'+ph+(ph&&site?'<br>':'')+site+'</td></tr>';}
 var places={};
 function render(list){var t=(q.value||'').trim().toLowerCase(),okf=function(v){return !(em.checked&&!v.e)&&!(lc.checked&&!v.l);},r=list.filter(function(v){if(!okf(v))return false;if(!t)return true;return (v.n+' '+v.c+' '+(v.z||'')).toLowerCase().indexOf(t)>=0;});
  cnt.textContent=r.length+(r.length===1?' vet':' vets')+(t?' matching \u201c'+esc(t)+'\u201d':'')+(r.length>300?' (showing first 300, narrow your search)':'');out.innerHTML=r.slice(0,300).map(row).join('');
  // nearest clinics to a typed town (Vail -> Edwards, Avon, Eagle...)
  var s=st.value,tt=t.replace(/,?\\s+[a-z]{2}$/,'').trim();if(!s||tt.length<3)return;
  var go=function(pl){var p=pl[tt];if(!p)return;var R=3958.8,rad=Math.PI/180,seen={};r.forEach(function(v){seen[v.n+v.a]=1;});
   var near=list.filter(function(v){return v.g&&okf(v)&&!seen[v.n+v.a];}).map(function(v){var x=Math.sin((v.g[0]-p[0])*rad/2),y=Math.sin((v.g[1]-p[1])*rad/2),h=x*x+Math.cos(v.g[0]*rad)*Math.cos(p[0]*rad)*y*y;return [Math.round(2*R*Math.asin(Math.sqrt(h))),v];}).filter(function(a){return a[0]<=100;}).sort(function(a,b){return a[0]-b[0];}).slice(0,15);
   if(!near.length)return;
   cnt.textContent=(r.length?cnt.textContent+' \u00b7 ':'')+'nearest '+near.length+' vets to '+tt.replace(/\\b\\w/g,function(m){return m.toUpperCase();})+' below';
   out.innerHTML+=near.map(function(a){return row(a[1]).replace('</b>','</b> <span class="badge b-none">about '+a[0]+' mi</span>');}).join('');};
  if(places[s])go(places[s]);else fetch('/assets/places/'+s+'.json').then(function(x){return x.json();}).then(function(d){places[s]=d;go(d);}).catch(function(){});}
 function load(){var s=st.value;if(!s){cnt.textContent='Pick a state to search vets.';out.innerHTML='';return;}
  if(cache[s])return render(cache[s]);cnt.textContent='Loading...';fetch('/find-a-vet/data/'+s+'.json').then(function(r){return r.json();}).then(function(d){cache[s]=d;render(d);});}
 st.addEventListener('change',load);[q,em,lc].forEach(function(e){e.addEventListener('input',load);e.addEventListener('change',load);});
 document.getElementById('vform').addEventListener('submit',function(e){e.preventDefault();load();});
 var u=new URLSearchParams(location.search);if(u.get('state'))st.value=u.get('state').toUpperCase();if(u.get('q'))q.value=u.get('q');load();
})();
</script>"""


def build_vets(dist=None, page_fn=None, write_fn=None, brand=None, crumbs_fn=None, suggest="/suggest/"):
    """Find-a-vet section. Called with no arguments for ShelterDayOut; build_adopt.py passes its own folder and page helpers."""
    dist = dist or DIST; page_fn = page_fn or page; write_fn = write_fn or write; brand = brand or BRAND; crumbs_fn = crumbs_fn or crumbs_ld
    src = ROOT / "data" / "osm_vets.json"
    if not src.exists():
        return
    raw = json.loads(src.read_text())["places"]
    # Clinics added by the vet sweeps (state licensing lists and clinics' own sites), one file per state; skip ones OSM already has.
    def _vkey(n, c):
        return re.sub(r"[^a-z0-9]", "", re.sub(r"\b(the|inc|llc|pc|pllc|dvm|veterinary|vet|animal|hospital|clinic|center|of)\b", "", n.lower())) + "|" + c.lower().strip()
    seen = {_vkey(v["name"], v.get("city") or "") for v in raw}
    phones = {re.sub(r"\D", "", v.get("phone") or "")[-10:] for v in raw if v.get("phone")}
    for f in sorted((ROOT / "data" / "vets_extra").glob("*.json")):
        try:
            extra = json.loads(f.read_text())
        except Exception:
            continue
        for v in extra:
            if not v.get("name") or not v.get("city") or not v.get("state"):
                continue
            k = _vkey(v["name"], v["city"]); ph = re.sub(r"\D", "", v.get("phone") or "")[-10:]
            if k in seen or (len(ph) == 10 and ph in phones):
                continue
            seen.add(k); phones.add(ph)
            raw.append(v)
    try:
        _vplaces = json.loads((ROOT / "data" / "us_places.json").read_text())
    except Exception:
        _vplaces = {}
    lowcost = re.compile(r"low.?cost|nonprofit|non-profit|spay|neuter|humane|spca|community|clinic for|charity|rescue|free", re.I)
    by = {}
    for v in raw:
        if v["state"] not in STATES or not v.get("city"):
            continue
        site = (v.get("website") or "").split(";")[0].strip()
        if site and not site.startswith("http"):
            site = "https://" + site
        if is_dead(site):
            site = ""
        rec = {"n": v["name"], "c": v["city"], "s": v["state"], "z": (v.get("zip") or "")[:5], "a": v.get("street", ""),
               "p": (v.get("phone") or "").split(";")[0].strip(), "w": site, "g": [round(v["lat"], 3), round(v["lon"], 3)] if v.get("lat") and v.get("lon") else _vplaces.get(v["state"], {}).get(v["city"].lower().strip()),
               "e": 1 if v.get("emergency") == "yes" or re.search(r"emergency|24.?7|24 hour", v["name"], re.I) else 0,
               "l": 1 if lowcost.search(v["name"] + " " + v.get("operator", "")) or v.get("operator_type") in ("community", "ngo", "charity") else 0}
        by.setdefault(v["state"], []).append(rec)
    # A chain's bare home page (e.g. thrivepetcare.com for dozens of clinics) isn't this clinic's site: link the map instead.
    from urllib.parse import urlparse
    homes = collections.Counter()
    for lst in by.values():
        for rec in lst:
            if rec["w"] and urlparse(rec["w"]).path in ("", "/"):
                homes[urlparse(rec["w"]).netloc.lower().removeprefix("www.")] += 1
    for lst in by.values():
        for rec in lst:
            if rec["w"] and urlparse(rec["w"]).path in ("", "/") and homes[urlparse(rec["w"]).netloc.lower().removeprefix("www.")] >= 3:
                rec["w"] = ""
            rec["m"] = map_url(rec["n"], rec["c"], rec["s"], rec["a"])
    (dist / "find-a-vet" / "data").mkdir(parents=True, exist_ok=True)
    total = 0
    for stc, lst in by.items():
        lst.sort(key=lambda r: (r["c"], r["n"]))
        total += len(lst)
        (dist / "find-a-vet" / "data" / f"{stc}.json").write_text(json.dumps(lst, separators=(",", ":")))
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
<div class="note">Clinic details come from OpenStreetMap, state veterinary licensing records and clinics' own websites, and can be out of date. Call ahead, especially for emergencies. Know a vet we're missing or see a mistake? <a href="{suggest}">Tell us</a>.</div>
<h2>Browse vets by state</h2><p class="citylinks">{state_links}</p>
{VET_JS}"""
    write_fn("/find-a-vet/", page_fn(f"Find a Vet Near You: {total:,} Veterinary Clinics, Emergency & Low-Cost | {brand}",
        f"Search {total:,} vet clinics across the US by city, ZIP or state. Find 24/7 emergency vets and low-cost or nonprofit clinics. Updated every 3 months.",
        body, "/find-a-vet/"))
    for stc, lst in by.items():
        name = STATES[stc]
        rows_html = "".join(
            f'<tr><td><b>{esc(r["n"])}</b>{" <span class=\"badge b-open\">24/7 emergency</span>" if r["e"] else ""}{" <span class=\"badge b-check\">Low-cost / nonprofit</span>" if r["l"] else ""}</td>'
            f'<td>{esc(r["c"])}</td><td>{esc(r["p"])}{"<br>" if r["p"] and r["w"] else ""}{f"<a href=\"{esc(r["w"])}\" rel=\"noopener nofollow\" target=\"_blank\">Website</a> &middot; " if r["w"] else ""}<a href="{esc(r["m"])}" rel="noopener nofollow" target="_blank">Map &amp; hours</a></td></tr>'
            for r in lst)
        ne = sum(r["e"] for r in lst)
        cities = sorted({r["c"] for r in lst}, key=lambda c: -sum(1 for r in lst if r["c"] == c))[:5]
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/find-a-vet/">Find a vet</a> / {name}</div>
<h1>Vets in {name}</h1>
<p class="lede">{len(lst):,} veterinary clinics in {name}, including {ne} listed as 24/7 emergency. <a href="/find-a-vet/?state={stc}">Search by city or ZIP</a>.</p>
<table class="list"><thead><tr><th>Clinic</th><th>City</th><th>Contact</th></tr></thead><tbody>{rows_html}</tbody></table>
<div class="note">From OpenStreetMap; details can change. Call ahead.</div>"""
        write_fn(f"/find-a-vet/{slugify(name)}/", page_fn(f"Vets in {name}: {len(lst):,} Veterinary Clinics & Emergency Vets | {brand}",
            f"Find a vet in {name}: {len(lst):,} clinics in {', '.join(cities)} and more, including 24/7 emergency and low-cost clinics.",
            body, f"/find-a-vet/{slugify(name)}/", crumbs_fn([("Home", "/"), ("Find a vet", "/find-a-vet/"), (name, f"/find-a-vet/{slugify(name)}/")])))


PREV_LASTMOD = {}
INDEXNOW_KEY = "31de02e2d1ad0d69c5434587a63bcb12"  # public by design: IndexNow verifies ownership by this file at the site root


def remember_lastmod(dist, key):
    f = dist / "lastmod.json"
    try:
        PREV_LASTMOD[key] = json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        PREV_LASTMOD[key] = {}


SITEMAP_SECTIONS = [("listings", "listings"), ("shelters", "shelters"), ("states", "states"), ("cities", "cities"), ("find-a-vet", "vets"), ("events", "events")]


def split_sitemaps(dist, site, key, skip=()):
    """Sitemap index + one sitemap per section, with a lastmod that only changes when the page's main content changes
    (search engines ignore lastmod when it is always today). Hashes are kept in data/lastmod_<key>.json."""
    import hashlib
    # kept inside the built folder (not data/) so parallel sweep runs never get a merge conflict on it;
    # main() reads the previous copy before wiping the folder.
    store = dist / "lastmod.json"
    old = PREV_LASTMOD.get(key, {})
    today = date.today().isoformat()
    new, groups = {}, {}
    for f in sorted(dist.rglob("index.html")):
        rel = str(f.parent.relative_to(dist))
        u = "/" if rel == "." else f"/{rel}/"
        if u in skip:
            continue
        html_ = f.read_text()
        if 'name="robots" content="noindex' in html_:
            continue
        m = re.search(r"<main>(.*?)</main>", html_, re.S)
        body = re.sub(r"(updated|Last updated|checked) [A-Z][a-z]+ \d{4}|\d{4}-\d{2}-\d{2}|&copy; \d{4}", "", m.group(1) if m else html_)
        h = hashlib.sha1(body.encode()).hexdigest()[:16]
        prev = old.get(u)
        lm = prev["d"] if prev and prev.get("h") == h else today
        new[u] = {"h": h, "d": lm}
        top = u.strip("/").split("/")[0]
        sec = next((name for prefix, name in SITEMAP_SECTIONS if top == prefix), "pages")
        groups.setdefault(sec, []).append((u, lm))
    store.write_text(json.dumps(new, separators=(",", ":"), sort_keys=True))
    hdr = '<?xml version="1.0" encoding="UTF-8"?>\n'
    idx = []
    for sec, items in sorted(groups.items()):
        for n in range(0, len(items), 45000):
            chunk = items[n:n + 45000]
            name = f"sitemap-{sec}{'' if n == 0 else '-' + str(n // 45000 + 1)}.xml"
            body = "".join(f"<url><loc>{site}{u}</loc><lastmod>{lm}</lastmod></url>" for u, lm in chunk)
            (dist / name).write_text(hdr + f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</urlset>\n')
            idx.append((name, max(lm for _, lm in chunk)))
    body = "".join(f"<sitemap><loc>{site}/{n}</loc><lastmod>{lm}</lastmod></sitemap>" for n, lm in idx)
    (dist / "sitemap.xml").write_text(hdr + f'<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{body}</sitemapindex>\n')
    # plain list of every URL (handy for IndexNow and for Bing's "submit URLs")
    (dist / "urls.txt").write_text("".join(f"{site}{u}\n" for items in groups.values() for u, _ in items))
    (dist / f"{INDEXNOW_KEY}.txt").write_text(INDEXNOW_KEY)
    return sum(len(v) for v in groups.values())


def build_sitemap():
    return split_sitemaps(DIST, SITE, "dayout", {"/404.html", "/thanks/", "/oops/", "/request/"})


def build_assets(rows, optins):
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "site.css").write_text(CSS.strip() + "\n")
    for f in list((ROOT / "src" / "art").glob("*.svg")) + list((ROOT / "src" / "art").glob("*.png")):
        shutil.copy(f, DIST / "assets" / f.name)
    (DIST / "assets" / "email").mkdir(exist_ok=True)
    for f in (ROOT / "src" / "email").glob("*.png"):
        shutil.copy(f, DIST / "assets" / "email" / f.name)
    (DIST / "favicon.svg").write_text(
        LOGO.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '))
    (DIST / "robots.txt").write_text(f"# Bulk copying or scraping of this site is not allowed without written permission: {SITE}/terms/#no-scraping\n# Search engines that follow these rules are welcome.\nUser-agent: *\nAllow: /\nDisallow: /forms/\nDisallow: /api/\nSitemap: {SITE}/sitemap.xml\n")
    today = date.today().isoformat()
    urls = ["/", "/cats/", "/how-it-works/", "/for-shelters/", "/suggest/", "/about/", "/terms/", "/privacy/"]
    urls += sorted({f"/states/{slugify(v)}/" for v in STATES.values()})
    urls += [f"/listings/{r['slug']}/" for r in rows]
    sm = "".join(f"<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    (DIST / "sitemap.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n')
    # Form handler + the listing->shelter map it needs (only opted-in shelters get requests).
    shutil.copytree(ROOT / "src" / "forms", DIST / "forms", dirs_exist_ok=True)
    shutil.copytree(ROOT / "src" / "api", DIST / "api", dirs_exist_ok=True)
    lookup = {}
    for r in rows:
        em = r.get("email_main") or (optins.get(r["slug"], {}) or {}).get("email", "")
        lookup[r["slug"]] = {"org": r["org"], "city": r["city"], "state": r["state"], "email_main": em, "email_program": r.get("email_program", ""), "noprog": r["status"] == NOPROG, "url": r.get("url", ""), "source": r.get("source", "")}
    (DIST / "forms" / "listings.json").write_text(json.dumps(lookup))
    (DIST / "forms" / "optins.json").write_text(json.dumps(optins))
    write_places(DIST)
    (DIST / "assets" / "others.json").write_text(json.dumps([[r["slug"], r["org"], r["city"], r["state"], coords(r["city"], r["state"])] for r in rows if r["status"] == NOPROG], separators=(",", ":")))
    (DIST / ".htaccess").write_text(
        "ErrorDocument 404 /404.html\nOptions -Indexes\n"
        "<IfModule mod_rewrite.c>\nRewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n"
        "RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]\nRewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]\n</IfModule>\n"
        "# The account's main .htaccess blocks every .csv (private lead files); allow only the public report download.\n"
        "<Files \"programs-by-state.csv\">\n<IfModule mod_authz_core.c>\nRequire all granted\n</IfModule>\n</Files>\n")


def main():
    remember_lastmod(DIST, "dayout")
    remember_lastmod(ROOT / "dist_adopt", "adopt")
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
    me = sys.modules[__name__]
    seo.build_guides_hub(me, [(p, g["h1"], g["desc"]) for p, g in GUIDES.items()],
        [("/report/", "National report", "Exact counts of shelter day-out programs by state and type, updated monthly."),
         ("/new-programs/", "New programs by month", "Day-out, sleepover and hiking programs we've added each month."),
         ("/how-it-works/", "How it works", "How listings are checked and how outing requests reach shelters."),
         ("https://shelteradoption.com/guides/", "Adoption guides", "Ready to adopt? Our sister site's guides to adopting a dog or cat.")],
        "Guides to dog day outs, sleepovers and shelter volunteering",
        "Everything you need to take a shelter dog out for the day, host a sleepover, hike with a shelter dog or volunteer.")
    seo.build_new_programs(me, progs)
    seo.build_report(me, rows)
    seo.build_badge_page(me, "/for-shelters/badge/", '<a href="/">Home</a> / <a href="/for-shelters/">For shelters</a> / Website badge',
        "/listings/", "Find us on", "ShelterDayOut", "#ff7a59", "A free ShelterDayOut badge for your website",
        "Listed on ShelterDayOut? Add this badge to your shelter's website so visitors can find your day-out program, send outing requests and see your listing.")
    seo.write_og(DIST, OG, BRAND, "shelterdayout.com", "#ff7a59")
    build_sitemap()
    n = sum(1 for _ in DIST.rglob("*.html"))
    print(f"Built {len(progs)} programs + {len(rows)-len(progs)} other shelters, {n} pages into {DIST}")
    import build_adopt  # sister site shelteradoption.com, same data
    build_adopt.main(rows)


if __name__ == "__main__":
    main()
