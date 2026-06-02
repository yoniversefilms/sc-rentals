# SUPABASE.md — shared favorites, trash, flags & comments

This makes annotations **shared between two people** (you + your partner) instead of
per-device. It runs straight from the static page — no server, no build step. Supabase
is called directly from the browser.

## How the sharing model works
- A **board** is a shared workspace. It's a long random slug carried in the URL:
  `https://YOU.github.io/sc-rentals/?board=8f3k...`
- Anyone with that board URL sees and edits the same favorites / trash / viewed / dog
  flags / comments. You share that one link with your partner. Treat the board URL like
  a password — that's the access key.
- The Supabase **anon key is public by design** (it ships in the page). Your data is
  protected by Row-Level Security + the secret board key, NOT by hiding the anon key.

## 1. Create the project
1. supabase.com → New project (free tier is plenty).
2. Project Settings → API → copy the **Project URL** and the **anon public key**.

## 2. Run this SQL (SQL Editor → New query → Run)
```sql
-- toggles + shared note, one row per listing per board
create table public.annotations (
  listing_id  text not null,
  board       text not null,
  favorite    boolean default false,
  trashed     boolean default false,
  viewed      boolean default false,
  dogs        text,                       -- 'yes' | 'no' | null
  note        text default '',            -- quick shared note
  updated_at  timestamptz default now(),
  updated_by  text,
  primary key (listing_id, board)
);

-- threaded comments (append-only), so you can leave each other messages
create table public.comments (
  id          uuid primary key default gen_random_uuid(),
  listing_id  text not null,
  board       text not null,
  author      text,
  body        text not null,
  created_at  timestamptz default now()
);

alter table public.annotations enable row level security;
alter table public.comments    enable row level security;

-- Access is scoped to the board key the client presents as a request header.
-- A client can only read/write rows whose board == the key it holds; it cannot
-- enumerate other boards.
create policy "board access annotations" on public.annotations
  for all
  using      ( board = current_setting('request.headers', true)::json ->> 'x-board-key' )
  with check ( board = current_setting('request.headers', true)::json ->> 'x-board-key' );

create policy "board access comments" on public.comments
  for all
  using      ( board = current_setting('request.headers', true)::json ->> 'x-board-key' )
  with check ( board = current_setting('request.headers', true)::json ->> 'x-board-key' );

grant select, insert, update, delete on public.annotations to anon;
grant select, insert, update, delete on public.comments    to anon;
```

## 3. Wire the page (vanilla, via CDN — keeps it a static file)
All settings come from `config.js` (the single config file) — do NOT hardcode keys in
`index.html`. Put your Project URL + anon key into `config.js` (`supabaseUrl`,
`supabaseAnon`, and your `me` name). Then in `index.html`, load these before the app script:
```html
<script src="config.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
```
Init from config (board comes from the URL `?board=`, else `defaultBoard`):
```js
const C = window.SC_CONFIG || {};
const BOARD = new URLSearchParams(location.search).get("board") || C.defaultBoard || "";
const ME = C.me || "Me";
const SYNC = !!(C.supabaseUrl && C.supabaseAnon && BOARD);

let supa = null;
if (SYNC) {
  supa = window.supabase.createClient(C.supabaseUrl, C.supabaseAnon, {
    global: { headers: { "x-board-key": BOARD } }   // <- enforced by RLS above
  });
}
```

## 4. Read / write pattern
- **On load (if SYNC):** `supa.from('annotations').select('*').eq('board', BOARD)` and
  merge into the in-memory annotations map (keyed by `listing_id`). Also pull comments.
  If not SYNC, use localStorage exactly as the base build does.
- **On any change:** upsert the row:
  ```js
  await supa.from('annotations').upsert(
    { listing_id:id, board:BOARD, favorite, trashed, viewed, dogs, note,
      updated_at:new Date().toISOString(), updated_by:ME },
    { onConflict: 'listing_id,board' });
  ```
  Add a comment: `supa.from('comments').insert({listing_id:id, board:BOARD, author:ME, body:text})`.
- **Always** also write localStorage as an offline cache, so the page works if Supabase
  is unreachable; reconcile on next load (last-write-wins on `updated_at`).
- **Live sync (optional, nice):** subscribe to changes so both phones update in real time:
  ```js
  supa.channel('board:'+BOARD)
    .on('postgres_changes',{event:'*',schema:'public',table:'annotations',filter:'board=eq.'+BOARD},
        payload => applyRemote(payload.new))
    .subscribe();
  ```

## 5. Use it
- Pick a random board slug (e.g., generate once: `crypto.randomUUID()`), then open
  `?board=<that>`. Share that exact URL with your partner. Done — shared list.
- The base GitHub Pages URL with no `?board=` stays private/localStorage-only.

## Acceptance (sync)
- [ ] Two browsers on the same `?board=` converge: favorite/trash/viewed/dogs/comments
      made in one appear in the other (on reload, and live if realtime is wired).
- [ ] Different `?board=` values can't see each other's data.
- [ ] With Supabase unreachable, the page still works via localStorage and reconciles later.
- [ ] No `?board=` → behaves exactly like the localStorage-only base build.

## Security notes (honest)
- The anon key being public is expected; RLS + the board key are the protection.
- This is a **capability-URL** model: whoever has the board link can edit. Fine for two
  people and low-sensitivity rental notes. If you later want named logins / per-person
  permissions, upgrade to Supabase Auth (magic link) and switch the RLS to `auth.uid()`
  — that's a clean follow-up, not needed now.
