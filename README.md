# Santa Cruz Rental Map — self-hosted & auto-updating

A live map of Santa Cruz County rentals scraped daily from direct property-management
sites. Hosted free on GitHub Pages, refreshed every morning by GitHub Actions, and
embeddable in your GoHighLevel site (or anywhere) with one iframe.

## What's in here
- `index.html` — the map (fetches `data.json`, so it always shows the latest)
- `data.json` — current listings (rebuilt daily)
- `scrape.py` — the scraper
- `geocache.json` — cached address → coordinates (so we don't re-geocode daily)
- `.github/workflows/update.yml` — the daily job
- `requirements.txt` — Python deps

## One-time setup (~10 minutes, on a computer)

1. **Create a free GitHub account** at github.com if you don't have one.
2. **New repository** → name it e.g. `sc-rentals` → set **Public** → Create.
3. **Upload these files**: on the repo page click **Add file → Upload files**, drag in
   everything from this folder (keep the `.github/workflows/` folder structure), then
   **Commit**. (If the `.github` folder is hard to drag on some browsers, create the file
   manually: **Add file → Create new file**, name it
   `.github/workflows/update.yml`, paste the contents, commit.)
4. **Turn on Pages**: repo **Settings → Pages →** Source: **Deploy from a branch**,
   Branch: **main** / **/(root)** → Save. After a minute your map is live at:
   `https://YOUR-USERNAME.github.io/sc-rentals/`
5. **Turn on the daily job**: go to the **Actions** tab → enable workflows if prompted.
   It runs automatically every morning. To run it on demand, open **Actions → Daily
   rental update → Run workflow**.

That's it — it now refreshes itself daily with no further action.

## Embed in GoHighLevel
Add a **Custom HTML / Code** element to your page and paste:

```html
<iframe src="https://YOUR-USERNAME.github.io/sc-rentals/"
        style="width:100%;height:85vh;border:0;border-radius:14px"
        loading="lazy" title="Santa Cruz Rental Map"></iframe>
```

Replace `YOUR-USERNAME`. You never touch this again — the data updates behind it.

## Share it
Just send the Pages URL: `https://YOUR-USERNAME.github.io/sc-rentals/`

## Notes
- **Favorites** save in each person's browser (keyed to a stable per-address ID, so they
  survive the daily refresh). They don't sync between two devices — that would need a
  small database; ask if you want that.
- **Scraping etiquette**: the job runs once a day with rate-limited, identified requests.
  Don't crank the frequency up — these are small local businesses' sites, and aggressive
  scraping can get blocked.
- **Geocoding** uses the free OpenStreetMap Nominatim service with a local cache, so only
  brand-new addresses are looked up. If it ever stops returning coordinates, swap in a
  free geocoder API key (LocationIQ / Geoapify) in `scrape.py`.
- **Adjust the run time**: edit the `cron` line in `.github/workflows/update.yml`
  (it's in UTC).
- **Add/remove sites**: edit the scraper functions in `scrape.py`.
