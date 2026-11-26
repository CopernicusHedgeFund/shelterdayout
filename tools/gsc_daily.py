#!/usr/bin/env python3
"""Google Search numbers for both sites, read from Search Console (read-only).

Run by .github/workflows/gsc_daily.yml with keyless Google sign-in as the read-only
gsc-reader account (the same one AltMountain uses). That account must be a "Restricted"
user on both Search Console properties. Writes out/data/gsc_daily.json, which the
workflow saves to the "gsc-data" branch.

Contents: clicks and impressions per day per site (last 90 days), plus the top searches
and top pages for the last 28 days. Google's last 2-3 days are preliminary and usually
rise. Dates are Pacific time (Google's).
"""
import datetime as dt, json, os, urllib.parse
import google.auth
from google.auth.transport.requests import AuthorizedSession

PROPS = {"shelterdayout.com": "sc-domain:shelterdayout.com",
         "shelteradoption.com": "sc-domain:shelteradoption.com"}
DAYS = 90
TOP_DAYS = 28


def query(s, prop, body):
    url = f"https://www.googleapis.com/webmasters/v3/sites/{urllib.parse.quote(prop, safe='')}/searchAnalytics/query"
    r = s.post(url, json=body)
    if not r.ok:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.json().get("rows", [])


def main():
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    s = AuthorizedSession(creds)
    end = dt.date.today()
    out = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "note": "Google's last 2-3 days are preliminary and usually rise. Dates are Pacific time (Google's).",
           "properties": PROPS, "errors": {}, "sites": {}}
    for site, prop in PROPS.items():
        try:
            daily = query(s, prop, {"startDate": str(end - dt.timedelta(days=DAYS)), "endDate": str(end),
                                    "dimensions": ["date"], "rowLimit": 1000, "dataState": "all"})
            top_start = str(end - dt.timedelta(days=TOP_DAYS))
            queries = query(s, prop, {"startDate": top_start, "endDate": str(end), "dimensions": ["query"],
                                      "rowLimit": 50, "dataState": "all"})
            pages = query(s, prop, {"startDate": top_start, "endDate": str(end), "dimensions": ["page"],
                                    "rowLimit": 50, "dataState": "all"})
        except Exception as e:  # keep the other site's numbers if one fails
            out["errors"][site] = str(e)
            continue
        out["sites"][site] = {
            "daily": [{"date": r["keys"][0], "clicks": int(r["clicks"]), "impressions": int(r["impressions"]),
                       "position": round(r["position"], 2)} for r in daily],
            "top_queries_28d": [{"query": r["keys"][0], "clicks": int(r["clicks"]),
                                 "impressions": int(r["impressions"]), "position": round(r["position"], 2)}
                                for r in queries],
            "top_pages_28d": [{"page": r["keys"][0], "clicks": int(r["clicks"]),
                               "impressions": int(r["impressions"])} for r in pages],
        }
    os.makedirs("out/data", exist_ok=True)
    json.dump(out, open("out/data/gsc_daily.json", "w"), indent=1)
    print("errors:", out["errors"])
    for site, d in out["sites"].items():
        print(site, "days:", len(d["daily"]), "clicks:", sum(x["clicks"] for x in d["daily"]),
              "impressions:", sum(x["impressions"] for x in d["daily"]))
    if len(out["errors"]) == len(PROPS):
        raise SystemExit("both properties failed")


if __name__ == "__main__":
    main()
