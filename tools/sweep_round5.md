# Round 5: final national deep sweep (instructions for one cloud run)


**Stay in the foreground until the job is finished.** Do every step yourself in this one session. Never start background work: no Agent/Task tool, no subagents, no `run_in_background` commands, no Monitor, no sleeping until later. Do not end your reply (and so the session) until your whole scope is checked, saved and pushed. If you end early, everything still running is killed and nothing is saved. If the scope is too big, save and push every ~25 entries and keep going.

Also used by the QUARTERLY full sweeps (March, June, September, December). If your trigger message says "quarterly", follow
everything below the same way, but write "quarterly" instead of "round 5" in commit messages, set "checked" to the current
month and year, and add events through the end of the second month after the current one.

ShelterDayOut.com and ShelterAdoption.com are free shelter directories run by Charity Good for Philip "Ward" McKinley III.
This is the last big national pass and the foundation for both sites, so be thorough. Your trigger message names your
SCOPE (states, sometimes a city range). Work in the cloud without asking questions.

## Rules for this run
- No helper agents: do all work in this one session; never use the Agent/Task tool or subagents (their web fetches ask Ward for approval on his phone).
- Finish inside this one session. Do NOT schedule any follow-up or continuation tasks (no send_later, no create_trigger).
- Pace web requests (other runs share the limits): on an error or 429, wait 2 minutes and retry; after 5 failures in a row, save what you have and stop.
- Never send email.
- Data permissions: use only shelters' own websites and government pages for facts. Directory sites (Petfinder, Adopt-a-Pet, shelterlist, causeiq) only to discover names; never copy from them. Never scrape bestfriends.org's dashboard; skip Shelter Animals Count data. Respect robots.txt. Never use Facebook, Yelp, Google listings or search snippets as the source of a fact. Don't use a headless browser to get past bot blocks; if a site blocks you, move on.

## Repo
GitHub CopernicusHedgeFund/shelterdayout, branch main (push access is attached; use `gh api` REST, not GraphQL). Pushing to main publishes both sites within the hour.
Each state's list is data/sweep/<STATE>.json (format in data/sweep/README.md). Edit ONLY the files for your scope, and for a city range only entries whose "city" starts with a letter in that range.

## Pass A (most important): check every existing entry in your scope
For each entry, open its own site with WebFetch: the listed page, then up to 4 more same-site pages that matter (home, events or calendar, programs, volunteer, foster, "get involved"). Then:
1. **Day-out programs.** If the shelter's own site describes a program where the public or volunteers take an animal out or home for a short time (doggy day out, dog for a day, field trip, day trip, daycation, staycation, sleepover, weekend foster, hiking or trail buddy, running buddy, beach day, rent-a-dog, borrow a buddy, foster for a day, cat lounge or cat visits), set "program" (its name), "status" (Open to public / Volunteers only / Needs check / Paused), "offers" (short, e.g. "Day trips, sleepovers"), "animals", "notes" (one plain sentence of how it works), "url" (the program page) and "email_program" if listed. If an existing program is clearly gone from the site, set status "Needs check" and say so in "notes".
2. **Adoption events.** Add every upcoming event from the shelter's own site through March 31, 2027 to "events": [{"date":"YYYY-MM-DD","end":"YYYY-MM-DD" (optional),"title":"...","url":"...","place":"..."}]: adoption days, open houses, fee-waived or reduced-fee specials, holiday adoption events, mobile adoption stops. Future dates only; drop past ones; no duplicates.
3. **Fill gaps from the same pages:** missing "phone" (main public line, written "(555) 555-5555", never fax, clinic or a staff direct line), missing "email_main" (public email on their own site), a wrong name or city, or a "url" that has clearly moved to a new official address.
4. If the official site says the shelter has closed for good, remove the entry. Remove entries that turn out not to be shelters (vets, boarding, foster-only rescues with no facility, wildlife or farm sanctuaries).
5. Set "checked" to the current month and year (e.g. "November 2026") on every entry you open.

## Pass B: find shelters still missing
Then list which counties and cities in your scope already have entries and search the rest: "<county> County animal shelter <state>", "<county> County humane society", "animal shelter <city>" for every city over ~10,000 people, and the state's licensed-shelter list if one exists. Add every shelter that houses adoptable dogs and/or cats (county/city shelters, animal services and animal control, dog wardens, humane societies, SPCAs, nonprofit shelters with a physical adoption facility), no duplicates by name+city, confirmed on its own website or a government page. New entry:
{"state","city","org","program":"No day-out program yet","status":"No program yet","animals":"Dogs and cats","offers":"","url":"<official site>","notes":"","checked":"November 2026","phone":"","email_program":"","email_main":"","source_list":"shelter website","events":[]}
then check it as in Pass A.

## Saving
Save after about every 25 entries checked and at the end of each state: `python3 build.py`, check for warnings, commit "Sweep <STATE> (round 5, part N): +S shelters, +P programs, +E events" (data file plus dist/ and dist_adopt/), `git pull --rebase origin main` (on dist/ or dist_adopt/ conflicts take either side, rebuild and recommit; on a data file conflict keep both sides' changes), push. Count numbers exactly; never round.

End with exact counts per state: entries checked, shelters added and removed, programs added, events added, phones filled, and anything left unchecked.
