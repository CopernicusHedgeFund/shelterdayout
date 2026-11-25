Each XX.json here is the complete list of listings for state XX. build.py uses it in place of that
state's rows in data/listings.json. Sweep runs edit only their own states' files, so parallel runs never conflict.
Row format: see data/listings.json (fields: state, city, org, program, status, animals, offers, url, notes,
checked, email_main, email_program, source, source_list, events[{date,end,title,url,place}]).
Status values: "Open to public", "Needs check", "Volunteers only", "Paused", "No program yet".
