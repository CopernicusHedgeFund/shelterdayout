# Round 7: overnight events + programs sweep (instructions for one cloud run)

**Tools:** WebSearch and WebFetch are approved for this run: use them freely, directly, as often as the job needs. Nobody needs to approve anything.

**Stay in the foreground until the job is finished.** Do every step yourself in this one session. No Agent/Task tool, no subagents, no background commands. Do not end your reply until your scope is saved and pushed. Commit and push after every 10 shelters changed or added, so progress is never lost.

Follow every rule, data permission and save step in tools/sweep_round5.md (facts only from shelters' own sites and government pages, robots.txt, no headless browsers, no directories as sources), with these changes. Commit messages say "round 7".

Round 6 already searched counties for missing shelters. Round 7 goes shelter by shelter for what changes most: events and programs.

## Pass E: every listed shelter's own site (main work)
For each entry in data/sweep/<STATE>.json in your scope that has a website ("url"), in order:
1. Open its events / calendar / news / "adopt" specials page (find it from the home page menu). Add every upcoming adoption event or fee special dated Nov 28, 2026 to Mar 31, 2027 that is not already in its "events" list (holiday adoption events, Black Friday / Giving Tuesday specials, Empty the Shelters / Holiday Hope, Santa paws days, mobile adoptions at stores, New Year specials, winter fee waivers). Same event format as round 5.
2. On the same visit, if the entry says "No day-out program yet", glance at the volunteer / foster / programs page for day trips, field trips, doggy day out, sleepovers, weekend foster, foster-for-a-day, hiking buddy, cat lounge. If found, update the program fields.
3. Remove events that are already past.
Skip entries with no website. Don't re-check things unrelated to events and programs.

## Pass F: rescues with adoption centers (only after Pass E)
Search the scope for "rescue adoption center" <state>, "cat adoption center" <state>, "pet adoption center" <state>. Add real nonprofit rescues that have a public, physical adoption center with regular hours (confirmed on their own site). No foster-only rescues, no breeders, no pet stores.

End with exact counts per state: shelters visited, events added, events removed (past), programs added, rescues added, anything left unchecked.
