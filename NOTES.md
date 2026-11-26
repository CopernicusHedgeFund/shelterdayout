# ShelterDayOut + ShelterAdoption notes

## Traffic (since Nov 25, 2026)
- Cookie-free counter on both sites: pages send a beacon to /api/hit.php (src/api/). Logs live outside the web root in
  /home/pwycuxm0hcts/sdo_private/hits/{dayout|adopt}/YYYY-MM-DD.log (Denver days). A second beacon on the first scroll/click/
  touch/keypress goes to hits_people/ = real people (programs that only load pages are not counted there).
- Cloud check (works with Ward's laptop off):
  gh api -X POST repos/CopernicusHedgeFund/shelterdayout/actions/workflows/traffic.yml/dispatches -f ref=main
  then ~1 min later: gh api "repos/CopernicusHedgeFund/shelterdayout/contents/data/traffic_live.json?ref=traffic-data" -H "Accept: application/vnd.github.raw"
  (auth = GitHub identity token, audience shelterdayout-traffic; no stored secret).
- Report format Ward wants (same as AltMountain): running-total line chart (views + visitors), daily volume bars underneath,
  plus a real-people chart; always give both people counts and totals including bots; exact numbers, never rounded.
- Google Search Console: domain properties sc-domain:shelterdayout.com and sc-domain:shelteradoption.com (Ward's Google account),
  verified by GoDaddy TXT records (keep them). Sitemaps submitted Nov 25, 2026.
