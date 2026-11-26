#!/usr/bin/env python3
"""ShelterAdoption.com: sister site of ShelterDayOut, built from the same shelter data.
Run on its own or via build.py (which calls main() at the end). Output: dist_adopt/
"""
import json
import re
import shutil
from datetime import date, datetime
from pathlib import Path

import build as sdo
from build import esc, slugify, STATES, NOPROG, upcoming, fmt_date, ev_when, coords, contact_html, faq_block

ROOT = Path(__file__).parent
DIST = ROOT / "dist_adopt"
SITE = "https://shelteradoption.com"
SDO = "https://shelterdayout.com"
BRAND = "ShelterAdoption"
CONTACT = "hello@shelterdayout.com"

CSS = sdo.CSS.replace("--accent:#ff7a59;--accent-d:#e55d3c", "--accent:#2a9d8f;--accent-d:#1f7a6f").replace(
    "--teal:#2a9d8f", "--teal:#1f7a6f").replace("--bg:#fffaf2", "--bg:#f7fbf9") + """
.adopt-hero{background:linear-gradient(135deg,#e6f6f0,#fff7e6);border-radius:24px;padding:34px 28px;margin:6px 0 18px}
.adopt-hero h1 .hl{color:#e76f51}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin:12px 0}
.card{background:#fff;border:2px solid #dcebe5;border-radius:18px;padding:16px}
.card h3{margin:0 0 6px}
.slist{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.slist li{background:#fff;border:2px solid #dcebe5;border-radius:16px;padding:14px}
.slist li b a{color:var(--ink);text-decoration:none}
.slist li .meta{color:var(--muted);font-size:.92rem}
.slist li .tags{margin-top:6px;font-size:.85rem}
.tagp{display:inline-block;background:#e6f6f0;color:#1d6b4f;border-radius:999px;padding:2px 9px;margin:2px 4px 0 0;font-weight:700}
.tago{background:#fff1e6;color:#9a4f12}
#res .hide,.slist li.hide{display:none!important}

.adopt-hero{display:grid;grid-template-columns:1.05fr 1fr;gap:24px;align-items:center}
.adopt-hero img{width:100%;height:auto;display:block}
@media (max-width:760px){.adopt-hero{grid-template-columns:1fr}.adopt-hero img{max-width:440px;margin:0 auto}}
.card .ic{width:64px;height:64px;display:block;margin-bottom:6px}
.card{transition:transform .15s ease, box-shadow .15s ease}
.card:hover{transform:translateY(-3px);box-shadow:0 8px 20px rgba(42,157,143,.15)}
.paws{display:block;width:100%;max-width:600px;height:34px;margin:22px auto 6px}
.head-art{display:grid;grid-template-columns:1fr 260px;gap:18px;align-items:center}
.head-art img{width:100%;height:auto}
@media (max-width:760px){.head-art{grid-template-columns:1fr}.head-art img{max-width:260px}}
.guide-ic{width:72px;height:72px;float:right;margin:0 0 8px 14px}
"""

LOGO = sdo.LOGO.replace("#ff7a59", "#2a9d8f")


def logo_html():
    return f'{LOGO}<span>Shelter<b>Adoption</b></span>'


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
<a class="logo" href="/">{logo_html()}</a>
<nav class="main"><a href="/#find">Find a shelter</a><a href="/events/">Adoption events</a><a href="/how-to-adopt-a-dog/">How to adopt</a><a href="{SDO}/" rel="noopener">Dog day outs</a></nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
<div class="logo">{logo_html()}</div>
<p><a href="/how-to-adopt-a-dog/">How to adopt a dog</a><a href="/how-to-adopt-a-cat/">How to adopt a cat</a><a href="/adoption-checklist/">Adoption checklist</a><a href="/adoption-fees/">Adoption fees</a><a href="/fee-waived-adoption-events/">Fee-waived events</a><a href="/cities/">Browse by city</a></p>
<p><a href="/puppy-adoption/">Puppy adoption</a><a href="/kitten-adoption/">Kitten adoption</a><a href="/rescue-dogs-near-me/">Rescue dogs</a><a href="/humane-society-near-me/">Humane societies</a><a href="/animal-control-near-me/">Animal control</a></p>
<p><a href="/about/">About</a><a href="/events/">Adoption events</a><a href="{SDO}/suggest/" rel="noopener">Suggest a shelter</a><a href="/terms/">Terms</a><a href="/privacy/">Privacy</a></p>
<p>{BRAND} is a free directory of animal shelters. We don't place animals or handle adoptions; each shelter runs its own adoption process. Listings are checked monthly, but details change, so confirm with the shelter before you go.</p>
<p>Not ready to adopt? <a href="{SDO}/" rel="noopener">ShelterDayOut</a>, our sister site, lists shelters that let you take a dog out for the day.</p>
<p class="fine">Some shelter locations: &copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License. Distances use <a href="https://www.geonames.org/" rel="noopener">GeoNames</a> city data (CC BY 4.0).</p>
<p>{BRAND} is a program of <a href="https://charitygood.org" rel="noopener">Charity Good</a>. &copy; {date.today().year} Charity Good</p>
</div></footer>
<script>(function(){{try{{var d={{p:location.pathname,r:document.referrer,w:innerWidth}},s=function(e){{d.e=e;var b=JSON.stringify(d);if(navigator.sendBeacon)navigator.sendBeacon('/api/hit.php',new Blob([b],{{type:'application/json'}}));else fetch('/api/hit.php',{{method:'POST',body:b,keepalive:true}});}};s(0);var once=function(){{s(1);['scroll','click','touchstart','keydown','mousemove'].forEach(function(t){{removeEventListener(t,once,true)}})}};['scroll','click','touchstart','keydown','mousemove'].forEach(function(t){{addEventListener(t,once,{{capture:true,passive:true}})}})}}catch(e){{}}}})();</script>
</body>
</html>
"""


def write(path, content):
    p = DIST / path.lstrip("/")
    if path.endswith("/"):
        p = p / "index.html"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


def crumbs_ld(items):
    return '<script type="application/ld+json">' + json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE + u} for i, (n, u) in enumerate(items)]}) + "</script>"


def event_ld(r, e):
    d = sdo.event_ld(r, e)
    d["organizer"]["url"] = r.get("url") or SITE
    if not e.get("url") and not r.get("url"):
        d["url"] = SITE + f"/shelters/{r['slug']}/"
    return d


def animals_phrase(r):
    a = r.get("animals") or "Dogs and cats"
    return a.lower()


def has_program(r):
    return r["status"] != NOPROG


def tags(r):
    t = ""
    if upcoming(r):
        t += f'<span class="tagp">{len(upcoming(r))} upcoming event{"s" if len(upcoming(r)) != 1 else ""}</span>'
    if has_program(r):
        t += '<span class="tagp tago">Dog day outs</span>'
    return f'<div class="tags">{t}</div>' if t else ""


def shelter_li(r, show_state=True):
    loc = f"{esc(r['city'])}, {r['state']}" if show_state else esc(r["city"])
    q = esc((r["org"] + " " + r["city"] + " " + r["state_name"] + " " + r["state"]).lower())
    ll = coords(r["city"], r["state"])
    return (f'<li data-ll="{(str(ll[0]) + "," + str(ll[1])) if ll else ""}" data-q="{q}" data-state="{r["state"]}"><b><a href="/shelters/{r["slug"]}/">{esc(r["org"])}</a></b>'
            f'<div class="meta">{loc} &middot; {esc(r.get("animals") or "Dogs and cats")}</div>{tags(r)}</li>')


SEARCH_JS = """<script>
(function(){
 var q=document.getElementById('q'),st=document.getElementById('f-state'),cnt=document.getElementById('count'),f=document.getElementById('sform'),res=document.getElementById('res');
 var items=[].slice.call(document.querySelectorAll('#res li'));
 function run(){var t=(q.value||'').trim().toLowerCase(),s=st?st.value:'',n=0;
  items.forEach(function(li){var ok=(!t||li.dataset.q.indexOf(t)>=0)&&(!s||li.dataset.state===s);li.classList.toggle('hide',!ok);if(ok)n++;});
  cnt.textContent=n.toLocaleString()+(n===1?' shelter':' shelters');near(n,t,s);}
 var box=document.getElementById('nores'),SN=window.SDO_STATES||{};
 function esc(x){return String(x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
 function near(n,t,s){if(!box)return;if(n>0||!t){box.hidden=true;box.innerHTML='';return;}
  box.hidden=false;box.innerHTML='<p><b>No shelters match &ldquo;'+esc(t)+'&rdquo;'+(s?' in '+esc(SN[s]||s):'')+' by name.</b> Looking for the nearest ones&hellip;</p>';
  var c=items.map(function(li){var l=li.dataset.ll;var a=li.querySelector('a');var m=li.querySelector('.meta');return {name:a.textContent,url:a.getAttribute('href'),loc:m?m.textContent.split(' \u00b7 ')[0]:'',ll:l?l.split(',').map(Number):null};});
  window.sdoNear(t,s,c,function(pl,list){
   if(!pl||!list.length){box.innerHTML='<p><b>No shelters match &ldquo;'+esc(t)+'&rdquo;'+(s?' in '+esc(SN[s]||s):'')+'.</b> Try a nearby city or county name'+(s?', or <a href="/states/'+esc((SN[s]||'').toLowerCase().replace(/[^a-z0-9]+/g,'-'))+'/">see every shelter in '+esc(SN[s]||s)+'</a>':'')+'.</p>';return;}
   box.innerHTML='<p><b>Nearest shelters to '+esc(pl.name)+', '+esc(pl.st)+':</b></p><ul>'+list.map(function(x){return '<li><a href="'+x.url+'">'+esc(x.name)+'</a> ('+esc(x.loc)+') &middot; about '+x.mi+' miles</li>';}).join('')+'</ul>';});}
 q.addEventListener('input',run);if(st)st.addEventListener('change',run);
 f.addEventListener('submit',function(e){e.preventDefault();run();q.blur();res.scrollIntoView({behavior:'smooth',block:'start'});});
 var u=new URLSearchParams(location.search);if(u.get('q'))q.value=u.get('q');if(u.get('state')&&st)st.value=u.get('state').toUpperCase();
 run();
})();
</script>"""


def search_form(states_present):
    opts = "".join(f'<option value="{k}">{v}</option>' for k, v in sorted(STATES.items(), key=lambda kv: kv[1]) if k in states_present)
    return f"""<form class="search" id="sform" action="" method="get" role="search">
<div class="row">
<div style="flex:1"><label for="q">City, county or shelter name</label><input type="text" id="q" name="q" enterkeyhint="search" placeholder="e.g. Denver, Maricopa, humane society"></div>
<div><label for="f-state">State</label><select id="f-state" name="state"><option value="">All states</option>{opts}</select></div>
</div>
<div class="row2"><span class="animal">Every shelter links to its own adoptable pets page.</span><button type="submit" class="btn sbtn">Search</button></div>
</form>
<p class="count" id="count" aria-live="polite"></p>
<div class="note" id="nores" hidden></div>
<script>window.SDO_STATES={json.dumps(STATES)};</script>"""


HOME_FAQ = [
    ("How do I adopt a pet from a shelter near me?", "Find a shelter below, look at its adoptable animals on its own website, then visit or apply. Most shelters ask for a photo ID, a short application and a meet-and-greet. See <a href=\"/how-to-adopt-a-dog/\">how to adopt a dog</a> and <a href=\"/how-to-adopt-a-cat/\">how to adopt a cat</a>."),
    ("Where can I see the animals available for adoption?", "On each shelter's own website. Shelters update their adoptable animals daily, so we link straight to them rather than copying listings that go out of date."),
    ("How much does it cost to adopt from a shelter?", "Fees vary by shelter, animal and age. They usually cover spay or neuter, vaccines and a microchip. Many shelters hold <a href=\"/fee-waived-adoption-events/\">reduced-fee or fee-waived adoption events</a>. See <a href=\"/adoption-fees/\">adoption fees</a>."),
    ("Are there adoption events near me?", "Yes. Our <a href=\"/events/\">adoption events calendar</a> lists upcoming adoption days, open houses and fee-waived events taken from shelters' own websites."),
    ("Can I spend time with a shelter dog before adopting?", "Often, yes. Many shelters let you take a dog out for the day or host a sleepover. Our sister site <a href=\"" + SDO + "/\">ShelterDayOut</a> lists those programs."),
    ("Where can I find rescue dogs, puppies or kittens near me?", "City and county shelters, humane societies and SPCAs all have rescue dogs, puppies, cats and kittens. Search by your city above; each shelter's website shows who is available today."),
    ("What's the difference between animal control, a humane society and an SPCA?", "Animal control is usually run by a city or county and takes in strays; many also adopt animals out. Humane societies and SPCAs are usually independent nonprofits, despite the shared names. All of them are listed here."),
    ("Is ShelterAdoption free?", "Yes. It's a free directory run by the nonprofit Charity Good. We don't charge shelters or adopters and we don't handle adoptions."),
]


def build_home(rows):
    by = {}
    for r in rows:
        by.setdefault(r["state"], []).append(r)
    evs = sorted(((e["date"], r, e) for r in rows for e in upcoming(r)), key=lambda x: x[0])
    ev_prev = "".join(f'<li><b>{ev_when(e)}</b> &middot; <a href="/shelters/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}, {r["state"]}): {esc(e["title"])}</li>' for _, r, e in evs[:8])
    state_links = "".join(
        f'<a href="/states/{slugify(STATES[s])}/" style="color:#2a9d8f">{sdo.PAW}<div style="color:#2b2d42">{STATES[s]}<span>{len(by.get(s, [])):,} shelter{"" if len(by.get(s, [])) == 1 else "s"}</span></div></a>'
        for s in sorted(STATES, key=lambda k: STATES[k]))
    faq_html, faq_ld = faq_block(HOME_FAQ)
    ld = json.dumps({"@context": "https://schema.org", "@type": "WebSite", "name": BRAND, "url": SITE + "/",
        "potentialAction": {"@type": "SearchAction", "target": SITE + "/?q={search_term_string}", "query-input": "required name=search_term_string"}})
    org_ld = json.dumps({"@context": "https://schema.org", "@type": "Organization", "name": BRAND, "url": SITE + "/", "logo": SITE + "/assets/og.png",
        "email": CONTACT, "parentOrganization": {"@type": "NGO", "name": "Charity Good", "url": "https://charitygood.org"}})
    lst = "".join(shelter_li(r) for r in sorted(rows, key=lambda r: (r["state_name"], r["city"], r["org"])))
    n_states = len({r["state"] for r in rows if r["state"] != "DC"})
    body = f"""<section class="adopt-hero"><div>
<h1>Animal shelters near you: <span class="hl">adopt a pet.</span></h1>
<p class="lede">Find animal shelters, humane societies and SPCAs in every state, see their adoptable dogs, puppies, cats and kittens, and catch upcoming adoption events and fee-waived days.</p>
<p class="tagline">The nationwide shelter adoption directory, updated monthly.</p>
<p style="margin-top:14px"><a class="btn" href="#find">Find a shelter</a> <a class="btn alt" href="/events/">Adoption events</a></p>
</div><img src="/assets/art/hero.svg" alt="A happy dog and cat in front of their new home, with balloons and an Adopted banner" width="560" height="400"></section>
<div class="stats">
<div><b>{len(rows):,}</b><span>shelters listed</span></div>
<div><b>{len(evs):,}</b><span>upcoming adoption events</span></div>
<div><b>{n_states}</b><span>states{" + DC" if "DC" in by else ""} covered</span></div>
<div><b>Monthly</b><span>updated {date.today().strftime("%B %Y")}</span></div>
</div>
<section id="find">
<h2>Find a shelter</h2>
{search_form(STATES.keys())}
<ul class="slist" id="res">{lst}</ul>
</section>
{f'<h2>Upcoming adoption events</h2><ul class="evlist">{ev_prev}</ul><p><a href="/events/">See all {len(evs):,} adoption events</a></p>' if evs else ""}
<img class="paws" src="/assets/art/paws.svg" alt="" width="600" height="40">
<h2>Browse shelters by state</h2>
<div class="states">{state_links}</div>
<img class="paws" src="/assets/art/paws.svg" alt="" width="600" height="40">
<h2>Before you adopt</h2>
<div class="grid3">
<div class="card"><img class="ic" src="/assets/art/puppy.svg" alt="" width="64" height="64"><h3><a href="/how-to-adopt-a-dog/">How to adopt a dog</a></h3>What shelters ask for, how meet-and-greets work, and the first week home.</div>
<div class="card"><img class="ic" src="/assets/art/kitten.svg" alt="" width="64" height="64"><h3><a href="/how-to-adopt-a-cat/">How to adopt a cat</a></h3>Picking the right cat, bonded pairs, and settling in.</div>
<div class="card"><img class="ic" src="/assets/art/checklist.svg" alt="" width="64" height="64"><h3><a href="/adoption-checklist/">Adoption checklist</a></h3>What to bring to the shelter and what to have ready at home.</div>
<div class="card"><img class="ic" src="/assets/art/home.svg" alt="" width="64" height="64"><h3><a href="{SDO}/" rel="noopener">Take a dog out first</a></h3>Many shelters let you borrow a dog for a day or a sleepover. ShelterDayOut lists them.</div>
</div>
<h2>Questions people ask</h2>
{faq_html}
{sdo.NEAR_JS}{SEARCH_JS}"""
    write("/", page(f"Animal Shelters Near Me: Adopt a Dog or Cat ({len(rows):,} Shelters) | {BRAND}",
        f"Find an animal shelter or humane society near you and adopt a dog, puppy, cat or kitten. {len(rows):,} shelters and SPCAs in every state, plus adoption events.",
        body, "/", f'<script type="application/ld+json">{ld}</script><script type="application/ld+json">{org_ld}</script>{faq_ld}'))
    return evs


def build_states(rows):
    by = {}
    for r in rows:
        by.setdefault(r["state"], []).append(r)
    for s, name in STATES.items():
        lst = sorted(by.get(s, []), key=lambda r: (r["city"], r["org"]))
        path = f"/states/{slugify(name)}/"
        cities = []
        for r in lst:
            if r["city"] not in cities:
                cities.append(r["city"])
        evs = sorted(((e["date"], r, e) for r in lst for e in upcoming(r)), key=lambda x: x[0])
        ev_html = "".join(f'<li><b>{ev_when(e)}</b> &middot; <a href="/shelters/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}): {esc(e["title"])}</li>' for _, r, e in evs)
        progs = [r for r in lst if has_program(r)]
        hs = [r for r in lst if re.search(r"humane|spca", r["org"], re.I)]
        sfaq_html, sfaq_ld = faq_block([
            (f"How many animal shelters are in {name}?", f"We list {len(lst):,} animal shelters, humane societies and SPCAs in {name}" + (f", in {len(cities)} cities and towns." if cities else ".") + " The list is checked every month."),
            (f"Where can I adopt a dog or cat in {name}?", "At any shelter below. Each one links to its own adoptable animals page, which it updates daily." + (f" {len(hs)} of them are humane societies or SPCAs." if hs else "")),
            (f"Are there adoption events in {name}?", (f"Yes: {len(evs)} upcoming adoption events are listed above, taken from the shelters' own websites." if evs else f"None are listed right now. Check back soon, or see adoption events nationwide on our events page."))]) if lst else ("", "")
        ilist = json.dumps({"@context": "https://schema.org", "@type": "ItemList", "name": f"Animal shelters in {name}", "numberOfItems": len(lst),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": SITE + f"/shelters/{r['slug']}/", "name": r["org"]} for i, r in enumerate(lst[:100])]})
        body = f"""<div class="crumbs"><a href="/">Home</a> / {name}</div>
<h1>Animal shelters &amp; humane societies in {name}</h1>
<p class="lede">{len(lst):,} animal shelter{"s" if len(lst) != 1 else ""}, humane societies and SPCAs in {name}{(" including " + ", ".join(esc(c) for c in cities[:5])) if cities else ""}. Each links to its own adoptable dogs and cats.</p>
{f'<h2>Upcoming adoption events in {name}</h2><ul class="evlist">{ev_html}</ul>' if ev_html else ""}
<h2>Shelters</h2>
{('<ul class="slist">' + "".join(shelter_li(r, False) for r in lst) + "</ul>") if lst else f'<p>We don\'t have shelters listed in {name} yet. <a href="{SDO}/suggest/">Suggest one</a>.</p>'}
{f'<p class="animal" style="margin-top:14px">{len(progs)} of these shelters let you take a dog out for the day before adopting. <a href="{SDO}/states/{slugify(name)}/" rel="noopener">See dog day out programs in {name}</a>.</p>' if progs else ""}
<img class="paws" src="/assets/art/paws.svg" alt="" width="600" height="40">
<h2>Questions about adopting in {name}</h2>
{sfaq_html}
<p class="citylinks"><a href="/puppy-adoption/#{s}">Puppy adoption in {name}</a> <a href="/kitten-adoption/#{s}">Kitten adoption in {name}</a> <a href="/humane-society-near-me/#{s}">Humane societies in {name}</a> <a href="/animal-control-near-me/#{s}">Animal control in {name}</a></p>
<div class="note">Shelters update their adoptable animals daily on their own websites. Confirm hours and requirements with the shelter before you visit.</div>"""
        write(path, page(f"Animal Shelters & Humane Societies in {name}: Adopt a Dog, Puppy or Cat | {BRAND}",
            f"Adopt a dog, puppy, cat or kitten in {name}: {len(lst):,} animal shelters, humane societies and SPCAs{(' in ' + ', '.join(cities[:4]) + ' and more') if cities else ''}, plus upcoming adoption events.",
            body, path, crumbs_ld([("Home", "/"), (name, path)]) + sfaq_ld + (f'<script type="application/ld+json">{ilist}</script>' if lst else "")))


def build_shelters(rows):
    for r in rows:
        path = f"/shelters/{r['slug']}/"
        evs = upcoming(r)
        ev_html = sdo.events_html(r, evs)
        visit = f'<a class="btn" href="{esc(r["url"])}" rel="noopener nofollow" target="_blank">See adoptable pets on their website</a>' if r.get("url") else ""
        dayout = ""
        if has_program(r):
            dayout = f"""<div class="card" style="margin-top:16px"><h3>Try a day out first</h3><p>{esc(r['org'])} runs <b>{esc(r['program'])}</b>{(': ' + esc(r['offers'])) if r.get('offers') else ''}. It's a great way to get to know a dog before you adopt.</p><p><a href="{SDO}/listings/{r['slug']}/" rel="noopener">Program details on ShelterDayOut</a></p></div>"""
        ld = [{"@context": "https://schema.org", "@type": "AnimalShelter", "name": r["org"],
               "address": {"@type": "PostalAddress", "addressLocality": r["city"], "addressRegion": r["state"], "addressCountry": "US"},
               "url": r.get("url") or SITE + path}]
        ld += [event_ld(r, e) for e in evs]
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/states/{r['state_slug']}/">{r['state_name']}</a> / {esc(r['org'])}</div>
<h1>{esc(r['org'])}</h1>
<p class="lede">Adopt {esc(animals_phrase(r))} in {esc(r['city'])}, {r['state_name']}.</p>
<dl class="facts">
<dt>Animals</dt><dd>{esc(r.get('animals') or 'Dogs and cats')}</dd>
<dt>Location</dt><dd>{esc(r['city'])}, {r['state_name']}</dd>
{f'<dt>Website</dt><dd><a href="{esc(r["url"])}" rel="noopener nofollow" target="_blank">{esc(re.sub(r"^https?://(www\.)?", "", r["url"]).split("/")[0])}</a></dd>' if r.get("url") else ""}
{contact_html(r)}<dt>Last checked</dt><dd>{esc(r.get('checked', ''))}</dd>
</dl>
<p>{visit}</p>
<p class="animal"><a href="{esc(r['map'])}" rel="noopener nofollow" target="_blank">Find {esc(r['org'])} on the map</a> for directions, hours and phone.</p>
{f'<h2>Upcoming adoption events</h2><ul class="evlist">{ev_html}</ul>' if evs else ""}
{dayout}
<h2>How adoption usually works here</h2>
<p>Browse the animals on the shelter's website, then visit or apply. Most shelters ask for a photo ID, a short application and a meet-and-greet, and the fee usually covers spay or neuter, vaccines and a microchip. Read our <a href="/adoption-checklist/">adoption checklist</a> before you go.</p>
<div class="note">{BRAND} isn't affiliated with this shelter and doesn't handle adoptions. Hours, fees and requirements are set by the shelter and can change, so confirm before you visit.</div>
<p class="animal">Something out of date? <a href="{SDO}/suggest/?type=report&amp;listing={r['slug']}" rel="noopener">Report a problem</a>.</p>"""
        write(path, page(f"{r['org']} ({r['city']}, {r['state']}): Adopt a Dog, Puppy or Cat | {BRAND}",
            f"Adopt {animals_phrase(r)} from {r['org']} in {r['city']}, {r['state_name']}. See adoptable pets, contact details{', upcoming adoption events' if evs else ''} and how to adopt.",
            body, path, "".join(f'<script type="application/ld+json">{json.dumps(x)}</script>' for x in ld)
            + crumbs_ld([("Home", "/"), (r["state_name"], f"/states/{r['state_slug']}/"), (r["org"], path)])))


def build_events(rows):
    allev = sorted(((e["date"], r, e) for r in rows for e in upcoming(r)), key=lambda x: x[0])
    groups, cur = "", None
    for d, r, e in allev:
        m = d[:7]
        if m != cur:
            groups += ("</ul>" if cur else "") + f'<h2>{datetime.strptime(m, "%Y-%m").strftime("%B %Y")}</h2><ul class="evlist">'
            cur = m
        groups += (f'<li data-state="{r["state"]}"><b>{ev_when(e)}</b> &middot; '
                   f'<a href="/shelters/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}, {r["state"]}): '
                   f'{f"<a href=\"{esc(e["url"])}\" rel=\"noopener nofollow\" target=\"_blank\">{esc(e["title"])}</a>" if e.get("url") else esc(e["title"])}'
                   f'{(" · " + esc(e["place"])) if e.get("place") else ""}</li>')
    if cur:
        groups += "</ul>"
    sts = sorted({r["state"] for _, r, _ in allev}, key=lambda k: STATES[k])
    opts = "".join(f'<option value="{s}">{STATES[s]}</option>' for s in sts)
    js = """<script>(function(){var s=document.getElementById('evst');s.addEventListener('change',function(){var v=s.value;
document.querySelectorAll('.evlist li').forEach(function(li){li.style.display=(!v||li.dataset.state===v)?'':'none';});});})();</script>"""
    ld = "".join(f'<script type="application/ld+json">{json.dumps(event_ld(r, e))}</script>' for _, r, e in allev[:300])
    body = f"""<div class="crumbs"><a href="/">Home</a> / Adoption events</div>
<div class="head-art"><div><h1>Pet and dog adoption events near you</h1>
<p class="lede">{len(allev):,} upcoming adoption days, open houses and fee-waived events at shelters nationwide. Dates come from each shelter's own website; confirm with the shelter before you go.</p></div><img src="/assets/art/events.svg" alt="A calendar with a paw print and a party hat" width="420" height="240"></div>
{f'<p><label class="animal" for="evst">Show state: </label><select id="evst"><option value="">All states</option>{opts}</select></p>' if allev else ""}
{groups or '<p>No upcoming events listed right now. Check back soon: we update monthly.</p>'}
{js if allev else ""}"""
    write("/events/", page(f"Pet Adoption Events Near Me: {len(allev):,} Upcoming Dates | {BRAND}",
        f"Dog and pet adoption events near you: adoption days, open houses and fee-waived events at animal shelters nationwide. {len(allev):,} dates, updated monthly.",
        body, "/events/", ld + crumbs_ld([("Home", "/"), ("Adoption events", "/events/")])))
    # fee-waived subset
    fw = [x for x in allev if re.search(r"fee|free|waiv|\$|half|reduced|clear the shelter|empty the shelter|discount", x[2]["title"], re.I)]
    items = "".join(f'<li><b>{ev_when(e)}</b> &middot; <a href="/shelters/{r["slug"]}/">{esc(r["org"])}</a> ({esc(r["city"])}, {r["state"]}): {esc(e["title"])}</li>' for _, r, e in fw)
    body = f"""<div class="crumbs"><a href="/">Home</a> / Fee-waived adoption events</div>
<h1>Free pet adoption: fee-waived and reduced-fee events</h1>
<p class="lede">Shelters often waive or cut adoption fees when they're full, around holidays, and during national events like Clear the Shelters. Here are the upcoming ones we've found on shelters' own websites.</p>
{f'<ul class="evlist">{items}</ul>' if items else '<p>No fee-waived events listed right now. See <a href="/events/">all adoption events</a>.</p>'}
<p>Reduced fees don't mean a shortcut on the process: shelters still ask for an application and a meet-and-greet. See our <a href="/adoption-checklist/">adoption checklist</a>.</p>"""
    write("/fee-waived-adoption-events/", page(f"Free Pet Adoption Near Me: Fee-Waived & Free Dog Adoption Events | {BRAND}",
        "Free dog and cat adoption near you: upcoming fee-waived and reduced-fee adoption events at animal shelters nationwide, from shelters' own announcements.",
        body, "/fee-waived-adoption-events/", crumbs_ld([("Home", "/"), ("Fee-waived adoption events", "/fee-waived-adoption-events/")])))
    return allev


def build_cities(rows):
    by = {}
    for r in rows:
        by.setdefault((r["city"], r["state"]), []).append(r)
    keep = {k: v for k, v in by.items() if len(v) >= 2}
    for (c, st), lst in keep.items():
        path = f"/cities/{slugify(c + ' ' + st)}/"
        body = f"""<div class="crumbs"><a href="/">Home</a> / <a href="/states/{slugify(STATES[st])}/">{STATES[st]}</a> / {esc(c)}</div>
<h1>Animal shelters near {esc(c)}, {st}</h1>
<p class="lede">{len(lst)} shelters and humane societies in {esc(c)}, {STATES[st]} where you can adopt a dog or cat.</p>
<ul class="slist">{"".join(shelter_li(r, False) for r in sorted(lst, key=lambda r: r["org"]))}</ul>
<p class="animal" style="margin-top:14px">More nearby: <a href="/states/{slugify(STATES[st])}/">all shelters in {STATES[st]}</a>.</p>"""
        write(path, page(f"Animal Shelters Near {c}, {st}: Dog, Puppy & Cat Adoption | {BRAND}",
            f"{len(lst)} animal shelters in {c}, {STATES[st]}: adopt a dog or cat, see adoptable pets and upcoming adoption events.",
            body, path, crumbs_ld([("Home", "/"), (STATES[st], f"/states/{slugify(STATES[st])}/"), (c, path)])))
    links = " ".join(f'<a href="/cities/{slugify(c + " " + st)}/">{esc(c)}, {st}</a>' for (c, st) in sorted(keep, key=lambda k: (STATES[k[1]], k[0])))
    write("/cities/", page(f"Animal Shelters by City | {BRAND}", "Browse animal shelters by city and adopt a dog or cat near you.",
        f'<div class="crumbs"><a href="/">Home</a> / Cities</div><h1>Animal shelters by city</h1><p class="lede">Cities with two or more shelters. For everywhere else, <a href="/#find">search</a> or browse by state.</p><p class="citylinks">{links}</p>',
        "/cities/"))


GUIDES = {
    "/how-to-adopt-a-dog/": ("How to Adopt a Dog From a Shelter: Step-by-Step Guide", "How to adopt a dog from an animal shelter: what to bring, what shelters ask, meet-and-greets, fees and the first week home.",
        "How to adopt a dog from a shelter", """
<p class="lede">Adopting from a shelter is usually quicker and simpler than people expect. Here's how it typically works.</p>
<h2>1. Find shelters near you</h2><p><a href="/#find">Search by city or state</a>. Look at more than one: city and county shelters, humane societies and SPCAs all have different dogs.</p>
<h2>2. Browse adoptable dogs online</h2><p>Every shelter page links to the shelter's own adoptable animals. Read the notes: energy level, how the dog does with kids, cats and other dogs.</p>
<h2>3. Visit or apply</h2><p>Some shelters are walk-in; others want an online application first. Bring a photo ID. Renters may be asked for landlord approval.</p>
<h2>4. Meet the dog</h2><p>Staff will set up a meet-and-greet. If you have a dog at home, many shelters ask you to bring them so the two can meet. Ask about history, health and behavior.</p>
<h2>5. Pay the fee and take them home</h2><p>The fee usually includes spay or neuter, vaccines and a microchip. See <a href="/adoption-fees/">adoption fees</a> and watch for <a href="/fee-waived-adoption-events/">fee-waived events</a>.</p>
<h2>The first weeks home</h2><p>Give your dog a quiet space, a steady routine and time. Many trainers talk about the "3-3-3" pattern: about 3 days to decompress, 3 weeks to learn the routine and 3 months to feel at home.</p>
<h2>Not sure yet?</h2><p>Many shelters let you take a dog out for a day or host a sleepover first. <a href="SDO/">Find a dog day out program</a>.</p>"""),
    "/how-to-adopt-a-cat/": ("How to Adopt a Cat From a Shelter: A Simple Guide", "How to adopt a cat or kitten from an animal shelter: choosing a cat, bonded pairs, what to bring, fees and settling in.",
        "How to adopt a cat from a shelter", """
<p class="lede">Shelters and humane societies have cats of every age and personality. Here's how to find the right one.</p>
<h2>Kitten or adult?</h2><p>Kittens are fun and a lot of work. Adult cats' personalities are already known, so it's easier to find a match. Senior cats are often the calmest companions.</p>
<h2>Consider a bonded pair</h2><p>Shelters often have pairs that must be adopted together, and some offer reduced fees for two. Two cats keep each other company while you're out.</p>
<h2>Visit the cat room</h2><p>Spend time with a few cats. Ask staff which ones are shy, playful or good with kids and other pets. Some shelters run cat lounges or cat cafés you can visit.</p>
<h2>Apply and bring them home</h2><p>Bring a photo ID and a carrier. The fee usually includes spay or neuter, vaccines and a microchip.</p>
<h2>Settling in</h2><p>Start your cat in one quiet room with food, water, a litter box and a hiding spot, then open up the house over days or weeks. See the <a href="/adoption-checklist/">adoption checklist</a>.</p>"""),
    "/adoption-checklist/": ("Pet Adoption Checklist: What to Bring and What to Buy", "A shelter pet adoption checklist: what to bring to the shelter, what to have at home, and questions to ask before you adopt.",
        "Pet adoption checklist", """
<p class="lede">Print this or keep it on your phone.</p>
<h2>Bring to the shelter</h2><ul><li>Photo ID</li><li>Landlord's name and number, or proof you can have pets, if you rent</li><li>Your current pets' vet records, if the shelter asks</li><li>A leash and collar (dogs) or a carrier (cats)</li><li>Everyone in your household, if the shelter wants to meet them</li></ul>
<h2>Questions to ask</h2><ul><li>Why was this animal surrendered or found?</li><li>How do they do with kids, dogs and cats?</li><li>Any health issues or medications?</li><li>What vaccines and treatment have they had?</li><li>What does the fee include? Is there a return policy?</li></ul>
<h2>Have ready at home</h2><ul><li>Food (ask what the shelter feeds, and switch slowly)</li><li>Food and water bowls</li><li>Bed or crate (dogs); litter box, litter and scratching post (cats)</li><li>ID tag with your phone number</li><li>A few toys and chews</li><li>A local vet picked out (<a href="SDO/find-a-vet/">find a vet near you</a>)</li></ul>"""),
    "/adoption-fees/": ("How Much Does It Cost to Adopt a Dog or Cat? Shelter Adoption Fees Explained", "What shelter adoption fees usually cover, why they vary, and how to find reduced-fee and fee-waived adoption events near you.",
        "How much does it cost to adopt a pet?", """
<p class="lede">Adoption fees are set by each shelter and vary with the animal's age and type, the shelter, and the time of year. Check the shelter's own website for its current fees.</p>
<h2>What the fee usually covers</h2><ul><li>Spay or neuter surgery</li><li>Age-appropriate vaccines</li><li>A microchip</li><li>Deworming and flea treatment</li><li>Sometimes a free first vet visit, a starter bag of food or a trial of pet insurance</li></ul>
<p>Paying for those services separately would usually cost far more than the adoption fee.</p>
<h2>Why fees differ</h2><p>Puppies and kittens often cost more than adults; seniors often cost less. City and county shelters may charge less than private humane societies. Some shelters add a local license fee.</p>
<h2>How to adopt for less</h2><p>Many shelters run <a href="/fee-waived-adoption-events/">fee-waived or reduced-fee events</a>, especially when they're full or around holidays. Our <a href="/events/">adoption events calendar</a> lists the ones we've found.</p>"""),
}


def build_guides():
    for path, (title, desc, h1, html_) in GUIDES.items():
        ic = {"/how-to-adopt-a-dog/": "puppy", "/how-to-adopt-a-cat/": "kitten", "/adoption-checklist/": "checklist", "/adoption-fees/": "home"}.get(path, "home")
        body = f'<div class="crumbs"><a href="/">Home</a> / {esc(h1)}</div><img class="guide-ic" src="/assets/art/{ic}.svg" alt="" width="72" height="72"><h1>{esc(h1)}</h1><div class="prose">{html_.replace("SDO/", SDO + "/")}</div><p><a class="btn" href="/#find">Find a shelter near you</a></p>'
        write(path, page(f"{title} | {BRAND}", desc, body, path, crumbs_ld([("Home", "/"), (h1, path)])))


KEYWORD_PAGES = {
    "/puppy-adoption/": dict(icon="puppy",
        title="Puppy Adoption Near Me: Shelters With Puppies in Every State",
        desc="Adopt a puppy from a shelter near you. {n:,} animal shelters, humane societies and SPCAs that adopt out puppies, in every state, plus puppy adoption events.",
        h1="Puppy adoption near you", match=lambda r: "Dogs" in (r.get("animals") or "Dogs"),
        intro="Shelters and humane societies take in puppies year-round, with the most in spring and summer. Puppies at shelters are usually vaccinated, microchipped and spayed or neutered before they go home, and the adoption fee covers it. Puppies go fast, so check each shelter's adoptable animals page often.",
        faqs=[("Where can I adopt a puppy near me?", "From city and county animal shelters, humane societies and SPCAs. Pick your state below; every shelter links to its own adoptable dogs page, where puppies are listed."),
              ("Is it cheaper to adopt a puppy from a shelter?", "Usually. Shelter fees for puppies are often higher than for adult dogs, but they include spay or neuter, vaccines and a microchip, which cost far more separately."),
              ("How do I get a puppy before someone else does?", "Check the shelter's site daily, apply early (many shelters let you apply before you visit), and watch for adoption events.")]),
    "/kitten-adoption/": dict(icon="kitten",
        title="Kitten Adoption Near Me: Shelters With Kittens in Every State",
        desc="Adopt a kitten from a shelter near you. {n:,} animal shelters, humane societies and SPCAs that adopt out kittens and cats, in every state.",
        h1="Kitten adoption near you", match=lambda r: "Cats" in (r.get("animals") or "Cats"),
        intro="Kitten season runs from spring through fall, when shelters are full of kittens needing homes. Many shelters offer two-kitten discounts, since kittens adopted in pairs keep each other company and learn good manners from each other.",
        faqs=[("Where can I adopt a kitten near me?", "From animal shelters, humane societies, SPCAs and cat rescues with adoption centers. Choose your state below and open the shelter's adoptable cats page."),
              ("How old does a kitten have to be to be adopted?", "Shelters usually adopt out kittens at about 8 weeks old and 2 pounds, once they're old enough to be spayed or neutered."),
              ("Should I adopt two kittens?", "Many shelters encourage it and some discount the second kitten. Two kittens play with each other and are often easier than one.")]),
    "/humane-society-near-me/": dict(
        title="Humane Society Near Me: Humane Societies & SPCAs in Every State",
        desc="Find a humane society or SPCA near you. {n:,} humane societies and SPCAs listed by state, with links to their adoptable pets and adoption events.",
        h1="Humane societies and SPCAs near you", match=lambda r: bool(re.search(r"humane|spca|s\.p\.c\.a", r["org"], re.I)),
        intro="Humane societies and SPCAs are usually independent local nonprofits, despite the shared names: the Humane Society of the United States and the ASPCA don't run local shelters. Most local humane societies run an adoption center, low-cost vet care and volunteer programs.",
        faqs=[("Is the humane society the same as the SPCA?", "No. Both names are used by many separate local nonprofits. Each one is run on its own, with its own fees and rules."),
              ("Is the humane society the same as animal control?", "Usually not. Animal control is a city or county service that takes in strays; humane societies are nonprofits, though some run the local shelter under contract."),
              ("How do I adopt from the humane society?", "Look at the adoptable animals on its website, then visit or apply. Bring a photo ID; the fee usually covers spay or neuter, vaccines and a microchip.")]),
    "/animal-control-near-me/": dict(
        title="Animal Control & County Animal Shelters Near Me (Adopt a Pet)",
        desc="Find animal control and county or city animal shelters near you. {n:,} government animal services listed by state, most of which adopt out dogs and cats.",
        h1="Animal control and county animal shelters near you", match=lambda r: bool(re.search(r"animal control|animal services|animal care|county|city of|municipal|parish|police", r["org"], re.I)),
        intro="Animal control is run by a city, county or parish. It takes in stray and surrendered animals, and most animal control shelters also adopt pets out, often for lower fees than private shelters. For emergencies involving a dangerous animal, call 911 or your local non-emergency police number.",
        faqs=[("Can you adopt from animal control?", "Yes, most city and county animal services shelters adopt out dogs and cats. Each one below links to its own site."),
              ("What does animal control do?", "Animal control picks up strays, investigates bites and cruelty reports, enforces local pet laws and runs the public shelter in many areas."),
              ("My pet is lost. Where should I look?", "Check your county or city animal shelter first, in person if you can, plus nearby humane societies. Shelters keep strays only a few days before they can be adopted out.")]),
    "/rescue-dogs-near-me/": dict(icon="puppy",
        title="Rescue Dogs Near Me: Adopt a Rescue Dog From a Shelter",
        desc="Adopt a rescue dog near you. {n:,} shelters, humane societies and rescues with adoption centers in every state, plus dog adoption events.",
        h1="Rescue dogs near you", match=lambda r: "Dogs" in (r.get("animals") or "Dogs"),
        intro="Every shelter dog is a rescue dog. City and county shelters, humane societies and rescue groups with adoption centers all have dogs of every age and size, and many know each dog's personality well from staff and volunteer notes.",
        faqs=[("Where can I find rescue dogs near me?", "Choose your state below. Each shelter links to its own adoptable dogs page, updated daily."),
              ("Can I take a rescue dog out before adopting?", "Often, yes. Many shelters let you take a dog out for a day or a sleepover. Our sister site ShelterDayOut lists those programs."),
              ("What should I bring to adopt a rescue dog?", "A photo ID, a leash and collar, and, if you rent, your landlord's approval. See our adoption checklist.")]),
}


def build_keyword_pages(rows):
    for path, k in KEYWORD_PAGES.items():
        lst = [r for r in rows if k["match"](r)]
        by = {}
        for r in lst:
            by.setdefault(r["state"], []).append(r)
        states_html = "".join(
            f'<h2 id="{s}">{STATES[s]} <span class="animal">({len(by[s])})</span></h2><ul class="slist">' + "".join(shelter_li(r, False) for r in sorted(by[s], key=lambda r: (r["city"], r["org"]))) + "</ul>"
            for s in sorted(by, key=lambda k_: STATES[k_]))
        jump = " ".join(f'<a href="#{s}">{STATES[s]}</a>' for s in sorted(by, key=lambda k_: STATES[k_]))
        faq_html, faq_ld = faq_block(k["faqs"])
        body = f"""<div class="crumbs"><a href="/">Home</a> / {esc(k['h1'])}</div>
<img class="guide-ic" src="/assets/art/{k.get('icon', 'home')}.svg" alt="" width="72" height="72"><h1>{esc(k['h1'])}</h1>
<div class="prose"><p class="lede">{esc(k['intro'])}</p></div>
<p class="animal">{len(lst):,} shelters in {len(by)} states and DC. Jump to a state: </p><p class="citylinks">{jump}</p>
<h2>Questions people ask</h2>
{faq_html}
{states_html}"""
        write(path, page(f"{k['title']} | {BRAND}", k["desc"].format(n=len(lst)), body, path, faq_ld + crumbs_ld([("Home", "/"), (k["h1"], path)])))


def build_static(rows):
    write("/about/", page(f"About | {BRAND}", f"{BRAND} is a free nationwide directory of animal shelters, run by the nonprofit Charity Good.",
        f"""<h1>About {BRAND}</h1><div class="prose">
<p class="lede">{BRAND} helps people find animal shelters and adopt. We list {len(rows):,} shelters, humane societies and SPCAs across the country, link to each shelter's own adoptable animals, and gather upcoming adoption events.</p>
<p>We check every state each month: shelters' own websites, government shelter lists and OpenStreetMap. We don't copy pet listings, because shelters update them daily; we send you straight to the source.</p>
<p>{BRAND} is a program of <a href="https://charitygood.org">Charity Good</a>, a nonprofit, and the sister site of <a href="{SDO}/">ShelterDayOut</a>, the directory of shelter day-out and sleepover programs. It's free for adopters and shelters.</p>
<p>Questions or corrections: <a href="mailto:{CONTACT}">{CONTACT}</a>. Run a shelter? <a href="{SDO}/for-shelters/">Update your listing</a>.</p></div>""", "/about/"))
    write("/terms/", page(f"Terms | {BRAND}", "Terms of use.", f"""<h1>Terms of use</h1><div class="prose">
<p>{BRAND} is a free informational directory provided by Charity Good. Listings are gathered from public sources and checked monthly, but may be out of date or incomplete. We don't place animals, process adoptions or speak for any shelter. Each shelter sets its own policies, fees and requirements; confirm details with the shelter. Links to other websites are provided for convenience and we aren't responsible for their content. Use of this site is at your own risk and is provided as is, without warranties.</p>
<p>Some location data &copy; OpenStreetMap contributors, available under the Open Database License.</p></div>""", "/terms/"))
    write("/privacy/", page(f"Privacy | {BRAND}", "Privacy policy.", f"""<h1>Privacy</h1><div class="prose">
<p>{BRAND} doesn't require an account and doesn't sell personal information. Our web host keeps standard server logs (such as IP address and pages requested) for security. Visits are counted with our own cookie-free counter, which records the page, referring site, device type, browser family and a daily anonymous code; it stores no IP address and sets no cookies. Fonts are loaded from Google Fonts. Forms for suggestions and corrections are handled by our sister site ShelterDayOut under its <a href="{SDO}/privacy/">privacy policy</a>. The site isn't directed to children under 13. Contact: <a href="mailto:{CONTACT}">{CONTACT}</a>.</p></div>""", "/privacy/"))
    write("/404.html", page(f"Page not found | {BRAND}", "Page not found.",
        '<h1>Page not found</h1><p class="lede">That page doesn\'t exist or has moved.</p><p><a class="btn" href="/">Find a shelter</a></p>', "/404.html", canonical=False))


def build_assets():
    (DIST / "assets").mkdir(parents=True, exist_ok=True)
    (DIST / "assets" / "site.css").write_text(CSS.strip() + "\n")
    og = ROOT / "src" / "art" / "og_adopt.png"
    if og.exists():
        shutil.copy(og, DIST / "assets" / "og.png")
    shutil.copytree(ROOT / "src" / "api", DIST / "api", dirs_exist_ok=True)
    sdo.write_places(DIST)
    (DIST / "assets" / "art").mkdir(parents=True, exist_ok=True)
    for f in (ROOT / "src" / "art_adopt").glob("*.svg"):
        shutil.copy(f, DIST / "assets" / "art" / f.name)
    (DIST / "favicon.svg").write_text(LOGO.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '))
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: {SITE}/sitemap.xml\n")
    (DIST / ".htaccess").write_text(
        "ErrorDocument 404 /404.html\nOptions -Indexes\n"
        "<IfModule mod_rewrite.c>\nRewriteEngine On\nRewriteCond %{HTTPS} off\nRewriteRule ^ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]\n"
        "RewriteCond %{HTTP_HOST} ^www\\.(.+)$ [NC]\nRewriteRule ^ https://%1%{REQUEST_URI} [L,R=301]\n</IfModule>\n")


def build_sitemap():
    return sdo.split_sitemaps(DIST, SITE, "adopt")


def main(rows=None):
    if rows is None:
        sdo.remember_lastmod(DIST, "adopt")
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    if rows is None:
        rows, _ = sdo.load()
    build_assets()
    evs = build_home(rows)
    build_states(rows)
    build_shelters(rows)
    build_events(rows)
    build_cities(rows)
    build_guides()
    build_keyword_pages(rows)
    build_static(rows)
    build_sitemap()
    n = sum(1 for _ in DIST.rglob("*.html"))
    print(f"ShelterAdoption: {len(rows)} shelters, {len(evs)} events, {n} pages into {DIST}")


if __name__ == "__main__":
    main()
