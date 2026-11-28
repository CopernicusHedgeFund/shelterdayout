# Sweep watchdog (instructions for one cloud run)

Your job: find problems with the ShelterDayOut sweeps and the sites, and **fix them yourself in this run**. Ward doesn't want to approve anything or be emailed unless he truly has to act.

**First:** call ToolSearch with query "select:WebFetch,WebSearch" to load the web tools. Then call ToolSearch with query "list_triggers" to load the tool that lists scheduled tasks (read-only use).

**Rules:**
- Stay in the foreground and do every step yourself: no subagents and no background commands.
- Never create, change, pause, fire or delete scheduled tasks.
- Don't email Ward unless he must act on something only he can do (for example, a password or a host setting). Write to mckinley@copernicushedgefund.com and sign it "ShelterDayOut watchdog", since this is an automatic notice.
- Data rules are in tools/sweep_round5.md. They apply to anything you add.
- Never round numbers.

## 1. Check the sweep runs
1. `git log --since="3 hours ago" --pretty='%ad %s' --date=iso`. That shows what each run saved.
2. List the scheduled tasks whose names start with "ShelterDayOut". Take every one that last ran between 25 minutes and 3 hours ago (sweeps, monthly checks M01–M25, quarterly sweeps, vet sweeps).
3. A run **failed** if any of these is true:
   - it has no commits that mention its scope (its state codes and round)
   - it lasted under 5 minutes
   - its commits say it couldn't read sites
4. For each failed run:
   - **Find the cause.** Known causes so far:
     - WebFetch was deferred and wasn't loaded. Fix: the "load the web tools" step at the top of the instructions.
     - The wording made the run think tools needed approval.
     - Push conflicts in dist/.
     - The run thought it needed subagents.
   - **If you can see the cause, fix it** in the instruction files under tools/ (or in build code) and push. Future runs read those files when they start, so the fix spreads on its own.
   - **Do the failed scope yourself.** Use `python3 tools/worklist.py <STATES>` and follow tools/sweep_round7.md with "round 8" commits. Work oldest-checked first. Commit and push every 10 entries. Keep going until your time is close to running out.
   - If several runs failed, take them in order, starting with the largest number of entries that have no checked_on yet.

## 2. Check that the data and build are healthy
1. `git pull`. Look for leftover merge-conflict markers (`<<<<<<<`) and for JSON in data/ that won't load. Fix any you find.
2. Run `python3 build.py && python3 build_adopt.py && python3 tools/site_check.py`. Fix every broken link, duplicate title and script error. Commit and push.
3. Check for duplicate entries: the same name and city twice in one state. Merge them, keeping the most complete one.
4. Check for past events still listed (dated before today) and remove them.

## 3. Check the live sites
1. WebFetch these three pages:
   - https://shelterdayout.com/
   - https://shelteradoption.com/
   - https://shelteradoption.com/events/
2. Confirm each one loads, the counts match the latest build, and /events/ lists upcoming events (not one month only).
3. The host pulls from GitHub every hour at :37. If the live site is more than 2 hours behind the latest commit, push a fresh rebuild commit. If it's still behind on the next watchdog run, that's something Ward must act on: email him once with what is wrong.

## 4. Log
Append one line to data/watchdog_log.json:
`{"at": "<UTC time>", "runs_checked": n, "failed": [...], "causes_fixed": [...], "entries_done_by_watchdog": n, "site_ok": true/false}`

Commit and push. End with exact counts.
