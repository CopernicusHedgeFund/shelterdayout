Each XX.json here is the complete list of listings for state XX. build.py uses it in place of that
state's rows in data/listings.json. Sweep runs edit only their own states' files, so parallel runs never conflict.
Row format: see data/listings.json (fields: state, city, org, program, status, animals, offers, url, notes,
checked, phone, email_main, email_program, source, source_list, events[{date,end,title,url,place}]).
Status values: "Open to public", "Needs check", "Volunteers only", "Paused", "No program yet".

"phone": the shelter's main public phone exactly as shown on its own website or a government page, written "(555) 555-5555" (optional " ext. 12"). Never from a directory, Facebook or a search snippet; leave "" if unsure. The sites show it as a tap-to-call link and in the page's structured data.
