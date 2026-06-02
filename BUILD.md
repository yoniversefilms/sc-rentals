# BUILD.md — Build & deploy runbook for Claude Code

Execute this in order. It's the operational plan; the *what* lives in the other docs.

**Read first:** `CLAUDE.md` (context + invariants), `TASK.md` (feature spec + acceptance),
`SUPABASE.md` (sync schema + client), `config.js` (the single settings file).

## Ground rules
- Single static site — **no bundler, no build step, no server.** Vanilla JS only.
- All user state keyed by the **stable listing `id`** (survives the daily data refresh).
- Match the existing coastal theme (`:root` CSS vars; Fraunces + Outfit).
- Don't break the daily scraper (`scrape.py` / `.github/workflows/update.yml`) or the
  iframe embed.
- Commit in small, working increments with clear messages.

## Step 0 — Baseline
```bash
pip install -r requirements.txt
python -m http.server 8000     # open http://localhost:8000
```
Confirm the map loads with pins from `data.json` (currently 59). Optionally run
`python scrape.py` to refresh. Commit the untouched baseline so you can diff against it.

## Step 1 — Phase 1: annotations (localStorage)
Implement per `TASK.md`:
- Unified `annotations` store keyed by `id`; **migrate** existing `sc_rental_favs_v2`
  favorites in (don't lose them).
- Features: 🗑 trash + Trash view + Restore; 💬 comments/notes; ✓ viewed + hide/only
  filters; 🐶 dogs tri-state + filter; keep favorites.
- Author tag from `config.me` on edits/comments.
- Daily-refresh **merge behavior**: annotations reattach by `id`; trashed-but-still-listed
  stays trashed; a delisted-but-annotated listing appears in a read-only "No longer
  listed" section; new listings start clean; never throw on a missing id.
- Wire `config.js` (page reads `window.SC_CONFIG`; nothing hardcoded in `index.html`).

**Gate:** run the entire Phase-1 acceptance checklist in `TASK.md`, including the
**simulated-refresh test** (swap `data.json` for one with a listing removed and one added;
confirm annotations reattach and the removed-but-noted one shows in "No longer listed").
Commit.

## Step 2 — Phase 2: Supabase shared sync
Follow `SUPABASE.md` exactly:
1. Create the Supabase project; run the SQL (tables + RLS + grants).
2. Put the URL + anon key + your name into `config.js`.
3. Implement: load board annotations + comments on start; upsert on change; insert
   comments; keep localStorage as offline cache; reconcile last-write-wins on `updated_at`.
4. Wire the optional Realtime subscription so both phones update live.
5. **Config-gated:** with Supabase fields blank or no `?board=`, behave EXACTLY like the
   Phase-1 localStorage build.

**Gate:** run the sync acceptance checklist in `SUPABASE.md` (two browsers on the same
`?board=` converge; different boards are isolated; offline still works; no-board = local).
Commit.

## Step 3 — Deploy
- Push to the GitHub repo (create one if needed). **Don't commit a service_role key** —
  only the anon key belongs in `config.js`.
- Settings → Pages → Deploy from branch `main` / root. Confirm the live URL renders
  **streets + all features** (real web = no sandbox limits).
- Actions tab → enable workflows → run **Daily rental update** once manually; confirm it
  commits a fresh `data.json`.
- Test `?board=...` sync across two devices.

## Step 4 — Embed in GoHighLevel
Add a Custom HTML element:
```html
<iframe src="https://YOUR-USERNAME.github.io/sc-rentals/?board=YOUR-BOARD"
        style="width:100%;height:85vh;border:0;border-radius:14px"
        loading="lazy" title="Santa Cruz Rental Map"></iframe>
```
Verify it works at phone width (it's used on mobile).

## Step 5 — Hand back
Print: the live Pages URL, the shareable `?board=` URL, and a one-line note that all
settings live in `config.js`. List anything deferred.

## Gotchas
- Page is embedded in an iframe on phones → test narrow viewports; storage may be blocked
  in some embeds, so keep the in-memory fallback.
- `approx:true` pins render dashed; keep the legend.
- Keep the scrape once-daily and rate-limited — these are small local businesses' sites.

## Definition of done
Both acceptance checklists pass · deployed to Pages with streets visible · embedded in
GHL · `?board=` sync works across two devices · daily Action runs green · all settings in
`config.js`.
