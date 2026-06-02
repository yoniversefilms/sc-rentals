# TASK.md — Add listing annotations (trash, comments, viewed, dogs)

Implement the features below in `index.html`. Read `CLAUDE.md` first. Keep the base
implementation a single static file (no build step) so it still deploys to GitHub Pages.

## Goal
Let the user personally annotate listings — trash them, comment on them, mark them
viewed, and flag whether dogs are allowed — with all annotations persisting and
surviving the daily `data.json` refresh.

## Data model — per-listing annotations
Store one record per listing, keyed by the stable `id`:
```js
annotations[id] = {
  favorite: false,     // already exists today; fold into this unified store
  trashed:  false,
  viewed:   false,
  dogs:     null,      // "yes" | "no" | null  (tri-state; null = unknown)
  notes:    "",        // free-text comment
  updated:  "<ISO>",
  updated_by: ""       // who last changed it (from config.me) — show as a small tag
}
```
Show an author tag ("who changed what"): display `updated_by` subtly on annotated cards
(e.g., "★ saved by Yonatan"), and label each threaded comment with its author. The
current user's name comes from `config.me`.

**Config:** all settings live in `config.js` (loaded before the app script). The page
reads `window.SC_CONFIG` for `me`, `supabaseUrl`, `supabaseAnon`, `defaultBoard`. No
settings hardcoded in `index.html`.
- **Persistence (base):** `localStorage` under key `sc_rental_annotations_v1` as a JSON
  map `{ id: {...} }`. Migrate the existing `sc_rental_favs_v2` favorites into it on
  first load (don't lose current favorites).
- Wrap all storage in try/catch with an in-memory fallback (some embeds block storage).

## Features

### 1. Trash / hide
- Trash button on each card and in the map popup (icon 🗑).
- Trashed listings are **removed from the map and the main list**.
- A view toggle "🗑 Trash (n)" shows only trashed listings, each with a **Restore** button.
- Trashed state persists and survives daily refresh (keyed by id).
- Trashed listings are excluded from all other filters/counts (except the Trash view).

### 2. Comments / notes
- A text area per listing for free-text notes (in the popup, and/or an expandable
  section on the card). Save on blur/change; debounce is fine.
- Cards with a note show a 💬 indicator.
- Notes persist and survive refresh.

### 3. Viewed checkmark
- Toggle "✓ Viewed" per listing (card + popup).
- Viewed cards get a subtle treatment (e.g., reduced opacity + a check badge).
- Filter options: "Hide viewed" and "Viewed only."

### 4. Dogs-allowed flag (manual, tri-state)
- Control per listing cycling Unknown → 🐶 Allowed → 🚫 Not allowed → Unknown.
- This is a **manual override** the user sets (listings often don't state pet policy).
- Show a 🐶 badge on cards flagged Allowed.
- Filter: "Dogs allowed only."

### 5. Keep existing: favorites, city filter, type filter, the map, the legend.

## Filters bar (final set)
City · Type · Favorites only · Dogs allowed only · Hide viewed · Trash view.
Keep it compact and mobile-friendly (the page is embedded in an iframe and viewed on
phones). Show live counts: total visible, favorites, trashed.

## CRITICAL: daily-refresh merge behavior
When `data.json` is rebuilt by the daily job:
- Annotations reattach by `id` automatically — verify saved homes, notes, trash, viewed,
  and dog flags all reappear on the correct listings.
- A previously **trashed** listing that is still in the new data stays trashed.
- If a listing **disappears** from `data.json` (delisted) but has annotations
  (especially notes or favorite), do not lose the annotation: surface these in a small
  "No longer listed" section (read-only, with their saved notes) so the user's research
  isn't lost. Never throw if an annotated id is missing from the data.
- New listings appear normally with empty annotations.

## Acceptance checklist
- [ ] Trash hides from map + list; Trash view lists them; Restore works; persists on reload.
- [ ] Notes save, show 💬 indicator, persist on reload.
- [ ] Viewed toggles, dims the card, and the Hide/Only filters work; persists.
- [ ] Dogs tri-state cycles, badge shows, "Dogs allowed only" filter works; persists.
- [ ] Existing favorites migrated (not lost) and still work.
- [ ] Simulate a refresh: replace `data.json` with a version where one listing is removed
      and one is added — confirm annotations reattach correctly and the removed-but-noted
      listing shows in "No longer listed."
- [ ] Still a single static file; `python -m http.server` serves it; deploys to Pages.
- [ ] Works inside an iframe and on a phone-width viewport.

## Then: deploy
After local verification, help the user push to their GitHub repo and confirm the
GitHub Pages URL renders with streets + all annotations. Don't break the daily workflow.

## Phase 2 — Shared sync via Supabase (REQUESTED — build this)
The user wants shared favorites, trash, flags, and comments across both partners.
**Full schema, RLS policies, client snippet, and setup steps are in `SUPABASE.md` —
follow it.** Summary of requirements:
- Build Phase 1 (localStorage) first and verify it deploys.
- Then add the Supabase sync layer per `SUPABASE.md`: a shared `board` (URL `?board=...`)
  scopes the couple's shared data; `annotations` table for toggles + shared note,
  `comments` table for threaded comments; RLS scopes access by a board-key request header.
- The sync layer is **additive and config-gated**: with no Supabase config or no
  `?board=`, the page must behave EXACTLY like the Phase-1 localStorage build.
- Keep localStorage as an offline cache; reconcile last-write-wins on `updated_at`.
- Wire optional Supabase Realtime so both phones update live (see SUPABASE.md §4).
- NO build step or server — Supabase is called directly from the static page via CDN.

## Nice-to-haves (optional, ask before doing)
- "New since yesterday" badge (diff against previous data.json snapshot).
- Export/import all annotations as a JSON file (manual backup / move between devices).
- Rent range slider and an "available before [date]" filter.
