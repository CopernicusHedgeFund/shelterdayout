# Monthly listing check (instructions for one cloud run)

**Tools:** WebSearch and WebFetch are approved for this run: use them freely, directly, as often as the job needs. Nobody needs to approve anything.

**Stay in the foreground until the job is finished.** Do every step yourself in this one session. No Agent/Task tool, no subagents, no background commands. Do not end your reply until your scope is saved and pushed. Commit and push after every 20 listings checked.

Follow the data rules in tools/sweep_round5.md (facts only from shelters' own sites and government pages, respect robots.txt, no headless browsers, never use directories as sources). Commit messages: "Monthly check <STATE>: N checked, +E events, -P past events, +G programs, F fixes".

## The fast path
1. `python3 tools/worklist.py <STATES>` lists every listing in your scope, oldest-checked first, with its saved direct pages
   (events_url, programs_url, contact_url) plus phone and email.
2. For each listing, open the saved pages directly (no hunting):
   - events_url: add upcoming adoption events / fee specials for the next 4 months; remove past events.
   - programs_url: confirm the day-out / sleepover / cat program still runs (name, status, offers); if the entry has no
     program, check for one under any name (see the word list in tools/sweep_round7.md, Pass E step 2).
   - contact_url (or home page): confirm phone and email_main; fix if changed.
   - If a saved page is gone (404) or moved, find the new page on the shelter's site and save the new address.
   - If the shelter has closed for good (its own site or the government says so), remove the entry.
3. Set "checked_on" to today (YYYY-MM-DD) for every listing you checked, and save any missing events_url / programs_url /
   contact_url you found along the way, so next month is even faster.
4. Rebuild (`python3 build.py`), `python3 tools/site_check.py`, commit, `git pull --rebase` (on dist/ or dist_adopt/ conflicts
   take either side, rebuild, recommit), push.

End with exact counts: listings checked, events added, past events removed, programs added or changed, phones/emails fixed,
pages re-found, entries removed, and any listings left unchecked (they will be first in line next month).
