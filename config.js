// config.js — the ONLY file you edit to set things up.
// Safe to commit: the Supabase anon key is public by design (protected by RLS +
// the board key). NEVER put a service_role key here.

window.SC_CONFIG = {
  // Your name — shown on edits and comments so you and your partner can tell
  // who favorited / trashed / commented on a listing ("who changed what").
  me: "Me",

  // ---- Sharing via Supabase (optional) ----
  // Leave supabaseUrl + supabaseAnon BLANK to run localStorage-only (no sharing).
  // Fill them in (see SUPABASE.md) to sync favorites/trash/flags/comments between
  // you and your partner.
  supabaseUrl:  "",          // e.g. "https://abcd1234.supabase.co"
  supabaseAnon: "",          // anon public key (eyJ...)

  // Which shared board to use. The URL "?board=XXXX" always wins if present.
  // Set a defaultBoard only if you want the base URL to be shared too;
  // leave blank to keep the bare URL private/localStorage-only.
  defaultBoard: "",
};

// Resolution order used by the app:
//   board = (?board= in URL)  ||  defaultBoard  ||  ""(none → localStorage only)
//   sync is ON only when supabaseUrl, supabaseAnon, and a board are all present.
