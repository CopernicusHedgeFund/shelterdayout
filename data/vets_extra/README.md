One JSON list per state (XX.json) of veterinary clinics added by the vet sweeps, merged into Find a vet by build.py
(build_vets). Clinics OpenStreetMap already has (same name and city, or same phone) are skipped automatically.
Entry: {"state":"CO","name":"...","city":"...","street":"...","zip":"80202","phone":"(303) 555-0100","website":"https://...",
"emergency":"yes" (24/7 emergency only, else ""),"operator_type":"" ("ngo" for nonprofit/low-cost clinics),
"lat":null,"lon":null,"src":"<state board list or clinic site URL>","checked":"November 2026"}
