# Round 7: overnight events + programs sweep (instructions for one cloud run)

**Tools:** WebSearch and WebFetch are approved for this run: use them freely, directly, as often as the job needs. Nobody needs to approve anything.

**Stay in the foreground until the job is finished.** Do every step yourself in this one session. No Agent/Task tool, no subagents, no background commands. Do not end your reply until your scope is saved and pushed. Commit and push after every 10 shelters changed or added, so progress is never lost.

Follow every rule, data permission and save step in tools/sweep_round5.md (facts only from shelters' own sites and government pages, robots.txt, no headless browsers, no directories as sources), with these changes. Commit messages say "round 7".

Round 6 already searched counties for missing shelters. Round 7 goes shelter by shelter for what changes most: events and programs.

## Pass E: every listed shelter's own site (main work)
For each entry in data/sweep/<STATE>.json in your scope that has a website ("url"), in order:
1. Open its events / calendar / news / "adopt" specials page (find it from the home page menu). Add every upcoming adoption event or fee special dated Nov 28, 2026 to Mar 31, 2027 that is not already in its "events" list (holiday adoption events, Black Friday / Giving Tuesday specials, Empty the Shelters / Holiday Hope, Santa paws days, mobile adoptions at stores, New Year specials, winter fee waivers). Same event format as round 5.
2. **Hunt hard for day-out and cat programs on every visit** (Ward's top priority). Shelters name them many different ways, often buried in volunteer, foster, "get involved", "ways to help", FAQ or news pages, PDFs and sign-up forms. Open the volunteer, foster, programs and "get involved" pages (and their sub-pages) and search the text for ANY of these:
   - Dogs: day out, dog day out, doggy day out, dog's day out, day trip, field trip, foster field trip, adventure, dogventure, pupventure, outing, excursion, day pass, dog date, doggie date, "borrow a", "rent a", "take a dog", "check out a dog", walk-and-go, hike, hiking buddy, trail buddy, running buddy, jogging, "shelter skip day", "break from the shelter", "kennel break", staycation, daycation, sleepover, slumber party, overnight, weekend foster, weekend getaway, holiday foster, foster for a day, short-term foster, fospice is NOT one, "pup cup", "Pup Crawl", "pawty", "Tails around town", "out and about", "snout and about", "barks and rec", "furlough", "respite foster".
   - Cats: cat lounge, cat café / cafe, cat room, catio, kitty lounge, cat visiting hours, "cuddle", "lap cat", "reading to cats", "book buddies", "cat socializer" open to the public, kitten cuddling, kitten shower, "Purr", cat sleepover, cat foster for a weekend, "Kitty Day Out", "cat hangout", yoga with cats.
   - Also: dog yoga with shelter dogs, "puppy yoga", walk-in dog walking open to the public (not only trained volunteers), community dog walking days, "Dogs Day Out" events.
   If the program is open to the public (anyone can sign up, maybe after a short orientation), set status "Open to public"; if only for trained volunteers, "Volunteers only". Fill program (its own name), offers (Day trip / Sleepover / Cat lounge etc.), and url (the program's own page). If the entry says "No day-out program yet" but you find one, this is the most valuable change you can make.
3. Remove events that are already past.
Skip entries with no website. Don't re-check things unrelated to events and programs.

## Pass F2: program search by name (after Pass E)
WebSearch the scope with several of the words above plus the state name (e.g. "field trip" shelter dog <state>, "cat lounge" humane society <state>, "sleepover" shelter dog <state>, "dog date" shelter <state>, "kennel break" <state>, "cat cafe" adoptable cats <state>). Confirm each hit on the shelter's own site and update or add it.

## Pass F: rescues with adoption centers (only after Pass E)
Search the scope for "rescue adoption center" <state>, "cat adoption center" <state>, "pet adoption center" <state>. Add real nonprofit rescues that have a public, physical adoption center with regular hours (confirmed on their own site). No foster-only rescues, no breeders, no pet stores.

End with exact counts per state: shelters visited, events added, events removed (past), programs added, rescues added, anything left unchecked.
