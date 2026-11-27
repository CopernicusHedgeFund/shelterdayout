# Checks both built sites: broken internal links, bad structured data, duplicate titles, pages over 900 KB (the host returns 500), missing H1s and JavaScript syntax errors.
import re, os, json, collections, sys
from urllib.parse import urlparse, unquote
sites={'dist':'shelterdayout.com','dist_adopt':'shelteradoption.com'}
roots={v:k for k,v in sites.items()}
def exists(root, path):
    path=unquote(path.split('#')[0].split('?')[0])
    if not path: return True
    f=os.path.join(root, path.lstrip('/'))
    if path.endswith('/'): return os.path.isfile(os.path.join(f,'index.html'))
    return os.path.isfile(f) or os.path.isfile(os.path.join(f,'index.html'))
bad=collections.defaultdict(list); pages=0; ldbad=[]; dupt=collections.defaultdict(list); big=[]; noh1=[]
for root,host in sites.items():
    for dp,dn,fn in os.walk(root):
        for f in fn:
            if not f.endswith('.html'): continue
            fp=os.path.join(dp,f); t=open(fp,encoding='utf-8',errors='replace').read(); pages+=1
            page='/'+os.path.relpath(fp,root).replace('index.html','')
            if os.path.getsize(fp)>900000: big.append(fp)
            for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>',t,re.S):
                try: json.loads(m.group(1))
                except Exception as e: ldbad.append((fp,str(e)[:60]))
            if f=='index.html' and '<h1' not in t and '404' not in fp and 'data/' not in fp: noh1.append(fp)
            tm=re.search(r'<title>(.*?)</title>',t)
            if tm and 'noindex' not in t[:3000]: dupt[(host,tm.group(1))].append(page)
            for m in re.finditer(r'(?:href|src)="([^"]+)"',t):
                u=m.group(1)
                if u.startswith(('mailto:','tel:','#','javascript:','data:')): continue
                if "'+" in u: continue  # built inside a script
                if u.startswith('/') and not u.startswith('//'):
                    if not exists(root,u): bad[(host,u)].append(page)
                else:
                    pu=urlparse(u)
                    if pu.netloc in roots and not exists(roots[pu.netloc],pu.path or '/'): bad[(pu.netloc,pu.path)].append(host+page)
print('pages',pages)
print('broken internal links',len(bad))
for (h,u),ps in sorted(bad.items(),key=lambda x:-len(x[1]))[:40]: print(' ',h,u,len(ps),ps[:2])
print('bad JSON-LD',len(ldbad),ldbad[:5])
d=[(k,v) for k,v in dupt.items() if len(v)>1]
print('duplicate titles',len(d)); [print(' ',k,v[:3]) for k,v in d[:10]]
print('too big',big); print('no h1',len(noh1),noh1[:5])

# inline JavaScript syntax (needs node)
import hashlib, subprocess, shutil as _sh
if _sh.which('node'):
    seen = {}
    for root in sites:
        for dp, dn, fn in os.walk(root):
            for f in fn:
                if f.endswith('.html'):
                    p = os.path.join(dp, f)
                    for m in re.finditer(r'<script>(.*?)</script>', open(p, encoding='utf-8', errors='replace').read(), re.S):
                        seen.setdefault(hashlib.md5(m.group(1).encode()).hexdigest(), (p, m.group(1)))
    jsbad = []
    for p, js in seen.values():
        open('/tmp/_sc.js', 'w').write(js)
        r = subprocess.run(['node', '--check', '/tmp/_sc.js'], capture_output=True, text=True)
        if r.returncode:
            jsbad.append(p)
    print('script errors', len(jsbad), jsbad[:5])
    if jsbad or big or ldbad:
        sys.exit(1)
