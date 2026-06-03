// config.js — the ONLY file you edit to set things up.
// Safe to commit: the Supabase anon key is public by design (protected by RLS +
// the board key). NEVER put a service_role key here.

window.SC_CONFIG = {
  // Your name — shown on edits and comments so you and your partner can tell
  // who favorited / trashed / commented on a listing ("who changed what").
  // Each device also has an in-page "your name" input that overrides this in
  // localStorage — so this is just the default for first-time visitors.
  me: "Yonatan",

  // ---- Sharing via Supabase ----
  // The anon key is public by design (protected by RLS + the board key in
  // the URL). NEVER put a service_role key here.
  supabaseUrl:  "https://stoyyffvqpjebbmbwmug.supabase.co",
  supabaseAnon: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InN0b3l5ZmZ2cXBqZWJibWJ3bXVnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODA0NDk1NDEsImV4cCI6MjA5NjAyNTU0MX0.pT6Y5vpQa9v9irIaOM2MotwVJEMFO2ceZ72JbOuotu4",

  // The shared board slug — anyone with this URL can read/edit your shared list.
  // Treat it like a password. Share the full ?board=... URL with your partner.
  // The URL "?board=XXXX" param always overrides this default if present.
  defaultBoard: "3296e600-ae5e-46d7-9d95-925329058d4f",
};

// Resolution order used by the app:
//   board = (?board= in URL)  ||  defaultBoard  ||  ""(none → localStorage only)
//   sync is ON only when supabaseUrl, supabaseAnon, and a board are all present.
