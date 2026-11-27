# Daily copycat watch (ShelterDayOut + ShelterAdoption)

Runs once a day as a cloud scheduled task. Goal: find sites that copied our pages or data.

1. Clone https://github.com/CopernicusHedgeFund/shelterdayout (main).
2. Pick 12 distinctive sentences at random from our own content: 6 from dist/listings/*/index.html
   (program descriptions, "offers" text) and 6 from dist_adopt (guides, shelter pages, event write-ups).
   Prefer long, specific sentences that only we would have written.
3. WebSearch each sentence in quotes (standard mode). Also search 3 of our page titles and
   "ShelterDayOut" / "ShelterAdoption" brand names to spot clones using our names.
4. Ignore: shelterdayout.com, shelteradoption.com, charitygood.org, search engines, the shelter's own
   site quoting its own program, and normal news or blog posts that quote a line and link to us.
5. For a suspected copy, WebFetch the page. Save its text to a temp file and run
   `python3 -I tools/find_tracer.py <file>`. Any mark found names the exact page or record copied.
   Note how much matches (one quoted line vs. many listings).
6. Log every run in data/copycat_log.json (append: date, sentences checked, suspects with URL,
   evidence, tracer ids). Commit with message "Copycat watch YYYY-MM-DD". On a merge conflict in
   dist/ take theirs (`git checkout --theirs dist dist_adopt`), do not rebuild.
7. Email Ward (mckinley@copernicushedgefund.com) ONLY when a site has copied many listings, a guide,
   or our data in bulk (confirmed tracer marks or 5+ matching passages). Subject
   "Copycat found: <domain>"; include URLs, what was copied, tracer ids and the whois/host if public.
   This is an automatic notice: sign it "ShelterDayOut copycat watch". No email when nothing is found.
8. Respect robots.txt and the sites' terms when fetching; no headless browsers, no logins.
   Do not schedule any follow-up tasks.
