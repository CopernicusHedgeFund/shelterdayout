# Vet sweep (instructions for one cloud run)


**Stay in the foreground until the job is finished.** Do every step yourself in this one session. Never start background work: no Agent/Task tool, no subagents, no `run_in_background` commands, no Monitor, no sleeping until later. Do not end your reply (and so the session) until your whole scope is checked, saved and pushed. If you end early, everything still running is killed and nothing is saved. If the scope is too big, save and push every ~25 entries and keep going.

**No helper agents:** do all work in this one session; never use the Agent/Task tool or subagents (their web fetches ask Ward for approval).

ShelterDayOut.com and ShelterAdoption.com (free directories run by Charity Good for Philip "Ward" McKinley III) both have a
"Find a vet" section. It lists 9,587 clinics from OpenStreetMap, but the US has roughly three times that many. Your job: add
every missing veterinary clinic in your SCOPE (named in your trigger message). Work in the cloud without asking questions.

## Rules for this run
- Finish inside this one session. Do NOT schedule any follow-up or continuation tasks (no send_later, no create_trigger).
- Pace web requests (other runs share the limits): on an error or 429, wait 2 minutes and retry; after 5 failures in a row, save what you have and stop.
- Never send email.
- Data permissions: facts may come only from (1) state government sources: veterinary board or licensing agency public lists, public license lookups and official open-data downloads (use bulk downloads only where the state publishes them for public use), and (2) each clinic's own website. Directory sites (Yelp, Google listings, Vetstreet, AAHA locator, BringFido, chain store locators of other companies) may only be used to discover names; never copy from them. Respect robots.txt and site terms; never use a headless browser to get past bot blocks; if a site blocks you, move on.
- List clinic businesses only, never a person's home address or a vet's personal details. Skip mobile-only vets with no public business address, house-call vets who list only a home address, research labs, and clinics that are closed.

## Repo
GitHub CopernicusHedgeFund/shelterdayout, branch main (push access attached; use `gh api` REST, not GraphQL). Pushing to main publishes both sites within the hour.
- Existing clinics: data/osm_vets.json ("places", each with "state", "name", "city", "street", "phone"). Don't edit it.
- Your additions: data/vets_extra/<STATE>.json, one JSON list per state (create it if missing). Format in data/vets_extra/README.md. Edit only your states' files.
- build.py merges these and skips clinics OpenStreetMap already has (same name and city, or same phone), but check yourself too, so you don't waste time.

## Steps for each state
1. Find the state's official source: does its veterinary board license veterinary premises or facilities, or publish a licensee list or open-data download? Use it for names, addresses and cities of clinics (premises/facility records, not individual vets' home addresses).
2. Where there is no usable state list, go city by city (every city over ~10,000 people): search "veterinary clinic <city> <state>" and "animal hospital <city> <state>" to discover names, then confirm each on the clinic's own website.
3. For each missing clinic, add: {"state","name","city","street","zip","phone":"(555) 555-5555","website":"<clinic's own site>","emergency":"yes" only if the clinic's own site says 24/7 or 24-hour emergency care, else "","operator_type":"ngo" only for nonprofit, humane-society or low-cost clinics, else "","lat":null,"lon":null,"src":"<URL you confirmed it on>","checked":"November 2026"}. Phone and website only from the clinic's own site or the state source; leave "" if unsure. Never guess.
4. Prioritize: 24/7 emergency hospitals and low-cost or nonprofit clinics first (people need these most), then all others.

## Saving
Save after about every 50 clinics and at the end of each state: `python3 build.py`, check for warnings, commit "Vets <STATE> (part N): +V clinics (E emergency, L low-cost)" (data file plus dist/ and dist_adopt/), `git pull --rebase origin main` (on dist/ or dist_adopt/ conflicts take either side, rebuild and recommit; on a data file conflict keep both sides' changes), push. Count numbers exactly; never round.

End with exact counts per state: clinics added, emergency, low-cost, the state source used (or "none, city search"), and what's left.

## Quarterly runs (when your trigger message says "quarterly")
Do these before the steps above, for your scope:
1. **Re-check every clinic already in data/vets_extra/<STATE>.json** on its own website or the state source: still open (remove it if the site or state record says it closed for good or the license lapsed), correct name, street, city, phone and website (update moved addresses), and "emergency" / "operator_type" still accurate. Set "checked" to the current month and year.
2. **Spot-check OpenStreetMap clinics** in data/osm_vets.json (don't edit that file): for clinics whose website is in data/dead_links.json or that look closed, add a corrected entry to vets_extra only if you confirm the clinic moved or renamed; note confirmed closures in your end report.
3. Then run the steps above to add clinics that opened or that earlier sweeps missed.
In your commit messages use "Vets <STATE> (quarterly, part N): +A added, U updated, R removed".
