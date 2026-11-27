# Round 6: discovery sweep (instructions for one cloud run)

Round 5 already opened every listed shelter's site (each has "checked": "November 2026"). Round 6 hunts for what is
still MISSING: shelters we don't list, day-out programs we marked "No day-out program yet", and upcoming adoption events.
Follow every rule, data permission and save step in tools/sweep_round5.md, with these changes:

- Commit messages say "round 6" instead of "round 5".
- Order of work: Pass B first (new shelters), then Pass C (programs), then Pass D (events). Skip round 5's full Pass A,
  except: for every NEW shelter you add, check it fully as in Pass A.
- Your trigger message names your SCOPE (states, sometimes a city letter range). For a city range, add or edit only
  entries whose "city" starts with a letter in that range.

## IMPORTANT: no helper agents
Do ALL the work yourself in this one session. Do NOT use the Agent/Task tool or start subagents, background agents or
parallel workers: their web fetches ask Ward for approval on his phone, one prompt per website. Use WebFetch and
WebSearch directly from this session only.

## Pass B (deeper than round 5): find shelters still missing
1. Build the list of every county in your scope (use the state's government county list) and every city over 5,000 people.
   Mark which already have an entry (match on city and county seat).
2. For each county or city with no entry, search: "<county> County animal shelter", "<county> County animal control
   adoption", "<county> County humane society", "<city> animal shelter", "<city> SPCA", "<city> animal services".
3. Also search the scope for: "dog warden" (OH, PA, NC, WV, KY), "pound" with the county name, the state agriculture
   department's licensed-shelter or animal-facility list, and "adoption center" + the state name.
4. Add every real shelter with a physical adoption facility for dogs and/or cats (county/city shelters, animal control
   that adopts out, humane societies, SPCAs, nonprofit shelters with an adoption center). Confirm on its own site or a
   government page. No duplicates by name+city (also check spelling variants and "Humane Society of X" vs "X Humane Society").

## Pass C: day-out programs we may have missed
1. Search the scope for program words: "doggy day out", "dog day out", "field trip" dog shelter, "day trip" shelter dog,
   "sleepover" shelter dog, "weekend foster", "foster for a day", "staycation" shelter dog, "hiking buddy" shelter,
   "borrow a dog" shelter, "dog for a day", "cat lounge" shelter, each with the state name.
2. For every hit on a shelter's OWN site: if the shelter is listed, update its program fields (Pass A step 1 in
   round 5); if not listed, add it (Pass B) with the program.
3. For listed shelters still marked "No day-out program yet" that have a website with a volunteer, foster or programs
   page, open that page once more and look for any of the program words above.

## Pass D: adoption events
1. For every listed shelter in scope whose site has an events, calendar or news page, open it and add upcoming events
   through March 31, 2027 (round 5 Pass A step 2 rules): holiday adoption events, Black Friday / Clear the Shelters style
   fee-waived specials, Santa paws photo + adoption days, New Year specials, mobile adoption stops at stores.
2. Search the scope for "adoption event" December 2026 <state>, "fee waived adoption" <state>, "holiday adoption event"
   <state>, and add any event that the shelter itself lists on its own site.

## Saving
Same as round 5 (save about every 25 entries and at the end of each state; pull --rebase before push; on dist/ or
dist_adopt/ conflicts take either side, rebuild, recommit). Count exactly; never round.

End with exact counts per state: counties/cities searched, shelters added and removed, programs added, events added,
and anything left unchecked.
