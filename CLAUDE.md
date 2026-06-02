# CLAUDE.md — Santa Cruz Rental Map

Project context for Claude Code. Read this first, then `TASK.md`.

## What this project is
A self-hosted, auto-updating map of Santa Cruz County rental listings. It scrapes
direct property-management websites once a day, geocodes the addresses, and renders
them as an interactive map the user can browse, filter, and annotate. It is embedded
in the user's GoHighLevel site via an iframe and shared by URL.

## How it's deployed
- **Hosting:** GitHub Pages (static — no build step, no server).
- **Daily updates:** GitHub Actions (`.github/workflows/update.yml`) runs `scrape.py`
  every morning and commits a fresh `data.json`.
- **Embed:** an `<iframe>` in GoHighLevel points at the GitHub Pages URL.
- Keep it a **static site** for the base feature set so deployment stays trivial.
  (A backend is only introduced for the optional shared-sync stretch goal — see TASK.md.)

## File map
- `index.html` — the entire front-end (HTML + CSS + vanilla JS, single file). Loads
  Leaflet from cdnjs, OpenStreetMap tiles, and **fetches `data.json` at runtime** so the
  page is decoupled from the data.
- `scrape.py` — scraper for 9 sources (AppFolio × 5, Buildium, Utopia, a ColdFusion
  site, and Streamline). Classifies type + city, filters to Santa Cruz County 1–3BR,
  dedupes, and geocodes with a cache. Writes `data.json` and `geocache.json`.
- `data.json` — `{ generated, count, listings: [...] }`. Rebuilt daily.
- `geocache.json` — address → `[lat, lon, approx]` cache (avoids re-geocoding).
- `config.js` — the single settings file (your `me` name, Supabase `supabaseUrl` /
  `supabaseAnon`, `defaultBoard`). `index.html` reads `window.SC_CONFIG` from it.
- `requirements.txt`, `README.md`, `.github/workflows/update.yml`.
- **Build docs:** `TASK.md` (feature spec + acceptance), `SUPABASE.md` (sync schema +
  client snippet), `BUILD.md` (the ordered build/deploy runbook — start here).

## The listing data model (each item in `data.json.listings`)
```
{
  "id": "42a0136a17",        // STABLE id = sha1(normalized address)[:10]. NEVER changes.
  "addr", "city", "type",    // type ∈ House|Condo|Townhome|Duplex|Apartment|Studio|Verify type
  "beds", "baths", "sqft",
  "rent", "avail",
  "pm", "phone", "url",
  "lat", "lon", "approx",    // approx=true → geocoded to city center, show dashed pin
  "summary"
}
```

## CRITICAL invariant
The `id` is the join key between scraped data and the user's personal annotations.
**Any user state (favorite, trash, viewed, dogs, notes) must be keyed by `id`** so it
survives the daily `data.json` rebuild. Never key user state by array index or by the
listing object.

## Conventions
- Vanilla JS, no framework, no bundler (keep the base build deployable to Pages as-is).
- Coastal theme already in place: fonts Fraunces (display) + Outfit (body); palette in
  `:root` CSS vars (--ocean, --coral, --sand, --paper). Match it.
- Don't break the daily scrape or the iframe embed.
- Be polite in the scraper: once-daily, rate-limited, identified User-Agent.

## How to run locally
```
pip install -r requirements.txt
python scrape.py            # refresh data.json
python -m http.server 8000  # then open http://localhost:8000
```
