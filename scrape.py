#!/usr/bin/env python3
"""
Santa Cruz County rental scraper.
Scrapes direct property-management sites, classifies + geocodes (with cache),
and writes data.json consumed by index.html.
Runs daily via GitHub Actions. Be polite: light, rate-limited requests.
"""
import json, re, time, hashlib, urllib.parse, datetime, sys
import requests
from bs4 import BeautifulSoup

UA = {"User-Agent": "sc-rental-map/1.0 (personal house-search project)"}
TIMEOUT = 40

def get(url, tries=2):
    for _ in range(tries):
        try:
            r = requests.get(url, headers=UA, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.text
        except Exception:
            time.sleep(1.5)
    return ""

# ---------- helpers ----------
def beds_of(s):
    m = re.search(r'(\d+)\s*(?:bd|bed)', s or "", re.I)
    if m: return int(m.group(1))
    if re.search(r'\bstudio\b', s or "", re.I): return 0
    return None

def baths_of(s):
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:ba\b|bath)', s or "", re.I)
    if m:
        v = float(m.group(1))
        return v if v <= 12 else None
    return None

def phone_from(t):
    m = re.search(r'\(?\b831\)?[\s.\-]?\d{3}[\s.\-]?\d{4}', t or "")
    return m.group(0) if m else ""

def norm_rent(r):
    if not r: return "Contact for price"
    if re.sub(r'[^\d]', '', r) in ("0", ""): return "Contact for price"
    return r.strip()

def stable_id(addr):
    key = re.sub(r'[^a-z0-9]', '', (addr or "").lower())
    return hashlib.sha1(key.encode()).hexdigest()[:10]

OTHER_COUNTY = ["aptos","capitola","soquel","watsonville","scotts valley","felton","ben lomond",
  "boulder creek","brookdale","la selva","rio del mar","corralitos","freedom","davenport",
  "mount hermon","bonny doon","willowbrook"]
ALL_COUNTY = ["santa cruz","live oak"] + OTHER_COUNTY
ZIP_RE = r'9506[0-9]|9507[0-7]|95010|95003|95005|95006|95007|95017|95018|95019|95041|95001'

def city_of(text):
    t = (text or "").lower()
    if "live oak" in t: return "Live Oak"
    if "watsonsville" in t: return "Watsonville"   # common source typo
    for c in ["santa cruz"] + OTHER_COUNTY:
        if c in t: return c.title()
    if re.search(ZIP_RE, t): return "Santa Cruz County"
    return None

def in_county(text):
    t = (text or "").lower()
    return any(c in t for c in ALL_COUNTY) or bool(re.search(ZIP_RE, t))

APT_SIGNALS = ["apartment","coin-op","coin op","carport","upstairs unit","downstairs unit",
  "well maintained complex","laundry facility","on site laundry","quiet complex","small complex"]
def classify(text, addr):
    t = (text or "").lower()
    if any(w in t for w in ["loft","penthouse"]) or "condo" in t: return "Condo"
    if "townhome" in t or "townhouse" in t: return "Townhome"
    if "duplex" in t: return "Duplex"
    if any(w in t for w in ["adu","back house","front house","cottage","bungalow","single family","single-family","detached","- primary"]): return "House"
    if re.search(r'\bstudio\b', t): return "Studio"
    if any(w in t for w in APT_SIGNALS): return "Apartment"
    if re.search(r'#\s?\d{2,}', addr or "") and "house" not in t and "home" not in t: return "Condo"
    if "house" in t: return "House"
    if "home" in t and "complex" not in t: return "House"
    return "Unknown"

# ---------- scrapers (each isolated; failures don't kill the run) ----------
rows = []
PH = {}

def safe(fn, name):
    try:
        n = fn()
        print(f"  {name}: {n}")
    except Exception as e:
        print(f"  {name}: ERROR {e}", file=sys.stderr)

def add(source, address, beds, baths, rent, sqft, avail, summary, url, cls_text):
    rows.append(dict(source=source, address=address.strip(), beds=beds, baths=baths,
        rent=norm_rent(rent), sqft=sqft or "", available=avail or "",
        summary=(summary or "").strip()[:300], url=url, cls=cls_text or ""))

def scrape_appfolio(co, sub):
    base = f"https://{sub}.appfolio.com"
    html = get(base + "/listings/listings")
    if not html: return 0
    PH[co] = phone_from(html)
    s = BeautifulSoup(html, "lxml"); n = 0
    for it in s.select(".listing-item"):
        labs = [x.get_text(' ', strip=True).lower() for x in it.select(".detail-box__label")]
        vals = [x.get_text(' ', strip=True) for x in it.select(".detail-box__value")]
        D = dict(zip(labs, vals))
        addr = (it.select_one(".js-listing-address") or it).get_text(' ', strip=True)
        if "application" in addr.lower(): continue
        title = (it.select_one(".listing-item__title") or it).get_text(' ', strip=True)
        d = it.select_one(".listing-item__description") or it.select_one("p")
        desc = d.get_text(' ', strip=True) if d else ""
        link = it.select_one("a[href*='/listings/detail/']")
        bb = D.get("bed / bath", "")
        add(co, addr, beds_of(bb), baths_of(bb), D.get("rent", ""), D.get("square feet", ""),
            D.get("available", ""), title + ". " + desc,
            base + link['href'] if link else base + "/listings/listings",
            title + " " + desc + " " + addr); n += 1
    return n

APPFOLIO = [("Bailey PM","baileypm"),("Blue Sky PM","blueskysantacruz"),
            ("Kendall & Potter","kendallpotter"),("Anderson Christie","andersonchristierealestate"),
            ("C&C PM","ccpmgmt")]

def scrape_buildium():
    html = get("https://pacificsun.managebuilding.com/Resident/public/rentals")
    if not html: return 0
    PH["Santa Cruz Rentals (Pacific Sun)"] = phone_from(html)
    s = BeautifulSoup(html, "lxml"); n = 0
    for a in s.select("a[href*='/Resident/public/rentals/']"):
        card = a
        for _ in range(3):
            if card.parent: card = card.parent
        blob = card.get_text(' ', strip=True); atext = a.get_text(' ', strip=True)
        m = re.search(r'(.+?\d{5})', atext); addr = (m.group(1) if m else atext)[:90]
        href = a['href']; url = "https://pacificsun.managebuilding.com" + href if href.startswith("/") else href
        rent = re.search(r'\$[\d,]+', blob); rent = rent.group(0) if rent else ""
        add("Santa Cruz Rentals (Pacific Sun)", addr,
            beds_of(atext) if beds_of(atext) is not None else beds_of(blob),
            baths_of(atext) if baths_of(atext) is not None else baths_of(blob),
            rent, (re.search(r'([\d,]+)\s*sqft', atext) or [None, ""])[1] if 'sqft' in atext else "",
            "", atext, url, blob); n += 1
    return n

def scrape_utopia():
    n = 0
    for slug in ["santa-cruz-ca","capitola-ca","soquel-ca","aptos-ca","scotts-valley-ca","live-oak-ca"]:
        html = get(f"https://utopiamanagement.com/rental-list/{slug}")
        if not html: continue
        PH["Utopia Management"] = PH.get("Utopia Management") or phone_from(html) or "(831) 580-1111"
        for u in sorted(set(re.findall(r'https://utopiamanagement\.com/rental-list/property-at-[a-z0-9\-]+', html))):
            dh = get(u)
            if not dh: continue
            s = BeautifulSoup(dh, "lxml")
            h1 = s.select_one("h1").get_text(' ', strip=True) if s.select_one("h1") else ""
            addr = re.sub(r'^Available Rental Property at\s*', '', h1)
            F = {}
            for st in s.select("strong"):
                lab = st.get_text(strip=True).rstrip(':').lower(); nx = st.next_sibling
                if lab in ("bedrooms","bathrooms"): F[lab] = str(nx).strip() if nx else ""
            rent_m = re.search(r'\$[\d,]+\.00', dh)
            rent = rent_m.group(0).replace(".00", "") if rent_m else ""
            add("Utopia Management", addr,
                int(re.search(r'\d+', F.get("bedrooms","")).group()) if re.search(r'\d', F.get("bedrooms","")) else None,
                float(re.search(r'[\d.]+', F.get("bathrooms","")).group()) if re.search(r'\d', F.get("bathrooms","")) else None,
                rent, "", "", addr, u, h1); n += 1
            time.sleep(0.25)
    return n

def scrape_scprop():
    html = get("https://santacruzproperty.com/rental_listings.cfm")
    if not html: return 0
    PH["Santa Cruz Property Mgmt Co"] = phone_from(html)
    n = 0
    for i in sorted(set(re.findall(r'rental\.cfm\?id=(\d+)', html))):
        dh = get(f"https://santacruzproperty.com/rental.cfm?id={i}")
        if not dh: continue
        txt = BeautifulSoup(dh, "lxml").get_text(' ', strip=True)
        addr = (re.search(r'Address:\s*(.+?)(?:Pets:|First:|Deposit:)', txt) or [None, ""])[1].strip()
        beds = (re.search(r'Bedrooms?:\s*(\d+)', txt) or [None, None])[1]
        baths = (re.search(r'Bathrooms?:\s*(\d+(?:\.\d+)?)', txt) or [None, None])[1]
        rent = (re.search(r'First:\s*(\$[\d,]+)', txt) or [None, ""])[1]
        avail = (re.search(r'Available:\s*([\d/]+|NOW|Now)', txt) or [None, ""])[1]
        desc = (re.search(r'Deposit:\s*\$[\d,]+\s*(.+)', txt) or [None, ""])[1][:300]
        if not addr: continue
        add("Santa Cruz Property Mgmt Co", addr, int(beds) if beds else None,
            float(baths) if baths else None, rent, "", avail, desc,
            f"https://santacruzproperty.com/rental.cfm?id={i}", desc + " " + addr); n += 1
        time.sleep(0.2)
    return n

def scrape_streamline():
    html = get("https://streamline831.com/rental-listings/")
    if not html: return 0
    PH["Streamline PM"] = phone_from(html)
    s = BeautifulSoup(html, "lxml"); n = 0
    for h in s.select("h2"):
        addr = h.get_text(' ', strip=True)
        if not re.search(r'\d', addr) or "branch" in addr.lower(): continue
        blob = h.parent.get_text(' ', strip=True) if h.parent else addr
        rent = re.search(r'\$[\d,]+', blob)
        add("Streamline PM", addr, beds_of(blob), baths_of(blob),
            rent.group(0) if rent else "", "", "", blob,
            "https://streamline831.com/rental-listings/", blob); n += 1
    return n

# ---------- geocoding with cache ----------
def load_json(path, default):
    try:
        return json.load(open(path))
    except Exception:
        return default

GEOCACHE = load_json("geocache.json", {})
CITY_CENTER = {'Santa Cruz':(36.9741,-122.0308),'Live Oak':(36.9777,-121.9905),
  'Capitola':(36.9752,-121.9533),'Soquel':(36.9880,-121.9558),'Aptos':(36.9772,-121.8994),
  'Scotts Valley':(37.0510,-122.0147),'Watsonville':(36.9102,-121.7569),'Felton':(37.0513,-122.0736),
  'Boulder Creek':(37.1260,-122.1222),'Santa Cruz County':(36.9741,-122.0308)}

def clean_addr(a):
    a = a.replace('Watsonsville', 'Watsonville')                 # source typo
    a = re.sub(r'\s+-\s+[^,]*', '', a)                           # drop ' - Villa of...', ' - Unit A' (keeps 114-116)
    a = re.sub(r'#\s?\w+', '', a)
    a = re.sub(r'\(.*?\)', '', a)
    a = re.sub(r'\bApartment\b|\bApt\.?\s*#?\s*\d+', '', a, flags=re.I)
    a = re.sub(r'\s{2,}', ' ', a).replace(' ,', ',').strip().strip(',')
    return a.replace('California', 'CA')

def geocode(addr, city):
    key = re.sub(r'\s+', ' ', (addr or "").lower()).strip()
    if key in GEOCACHE:
        c = GEOCACHE[key]; return c[0], c[1], c[2]
    q = clean_addr(addr)
    try:
        u = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
            {"q": q, "format": "json", "limit": 1, "countrycodes": "us"})
        j = requests.get(u, headers=UA, timeout=25).json()
        time.sleep(1.1)  # Nominatim politeness
        if j:
            lat, lon = round(float(j[0]["lat"]), 6), round(float(j[0]["lon"]), 6)
            GEOCACHE[key] = [lat, lon, False]
            return lat, lon, False
    except Exception:
        pass
    import random
    c = CITY_CENTER.get(city, (36.9741, -122.0308))
    lat, lon = round(c[0] + random.uniform(-.004, .004), 6), round(c[1] + random.uniform(-.004, .004), 6)
    return lat, lon, True  # NOT cached -> retried next run (e.g. if geocoder was blocked)

# ---------- run ----------
def main():
    print("Scraping sources...")
    for co, sub in APPFOLIO:
        safe(lambda co=co, sub=sub: scrape_appfolio(co, sub), co)
        time.sleep(0.4)
    safe(scrape_buildium, "Pacific Sun (Buildium)")
    safe(scrape_utopia, "Utopia")
    safe(scrape_scprop, "Santa Cruz Property Co")
    safe(scrape_streamline, "Streamline")
    print(f"Raw rows: {len(rows)}")

    # filter + classify + enrich
    out = []
    for r in rows:
        full = r["address"] + " " + r["cls"] + " " + r["summary"]
        if not in_county(r["address"]) and not in_county(full): continue
        if r["beds"] is not None and not (1 <= r["beds"] <= 3): continue
        if "commercial" in full.lower(): continue
        city = city_of(r["address"]) or city_of(full) or "Santa Cruz County"
        typ = classify(full, r["address"])
        r["city"] = city; r["type"] = typ
        r["phone"] = PH.get(r["source"], "") or ""
        out.append(r)

    # dedupe by normalized address (merge sources)
    seen = {}; ded = []
    for r in out:
        k = re.sub(r'[^a-z0-9]', '', r["address"].lower())[:24]
        if k and k in seen:
            if r["source"] not in seen[k]["source"]:
                seen[k]["source"] += " / " + r["source"]
            continue
        seen[k] = r; ded.append(r)

    # geocode (cached)
    listings = []
    CITY_ORDER = {'Santa Cruz':0,'Live Oak':1,'Capitola':2,'Soquel':3,'Aptos':4,'Scotts Valley':5,
                  'Watsonville':6,'Felton':7,'Boulder Creek':8,'Santa Cruz County':9}
    TYPE_ORDER = {'House':0,'Duplex':1,'Townhome':2,'Condo':3,'Apartment':4,'Studio':5,'Unknown':6}
    for r in ded:
        lat, lon, approx = geocode(r["address"], r["city"])
        listings.append({
            "id": stable_id(r["address"]), "addr": r["address"], "city": r["city"],
            "type": r["type"] if r["type"] != "Unknown" else "Verify type",
            "beds": r["beds"], "baths": r["baths"], "sqft": r.get("sqft", "") or "",
            "rent": r["rent"], "avail": r.get("available", "") or "",
            "pm": r["source"], "phone": r.get("phone", "") or "",
            "url": r["url"], "lat": lat, "lon": lon, "approx": approx,
            "summary": (r.get("summary", "") or "")[:200],
        })
    listings.sort(key=lambda x: (CITY_ORDER.get(x["city"], 9),
                                 TYPE_ORDER.get(x["type"] if x["type"] != "Verify type" else "Unknown", 9),
                                 -(x["beds"] or 0)))

    # Stamp first_seen so the front-end can flag "new today" listings.
    # - Preserve existing first_seen.
    # - Pre-feature listings (in prev but unstamped) get "" so they're treated as old.
    # - Listings not in prev get today's UTC date — only when we actually have a prev to compare against.
    prev = load_json("data.json", {})
    today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    prev_by_id = {l.get("id"): l for l in prev.get("listings", []) if l.get("id")}
    for l in listings:
        pl = prev_by_id.get(l["id"])
        if pl and pl.get("first_seen"):
            l["first_seen"] = pl["first_seen"]
        elif pl:
            l["first_seen"] = ""
        elif prev_by_id:
            l["first_seen"] = today

    data = {
        "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "count": len(listings),
        "listings": listings,
    }
    # Safety net: if this run returned far fewer listings than last time (e.g. a source
    # blocked the CI IP), DON'T overwrite good data.json — keep yesterday's and warn.
    prev_n = prev.get("count", 0)
    json.dump(GEOCACHE, open("geocache.json", "w"), ensure_ascii=False, indent=1)  # cache always saved
    if prev_n and len(listings) < max(8, int(prev_n * 0.5)):
        print(f"WARNING: only {len(listings)} listings vs previous {prev_n}. "
              f"Keeping previous data.json (likely a blocked/failed source).", file=sys.stderr)
        return
    json.dump(data, open("data.json", "w"), ensure_ascii=False, indent=1)
    truly_new = sum(1 for l in listings if prev_by_id and l["id"] not in prev_by_id)
    print(f"Wrote data.json with {len(listings)} listings ({truly_new} new since last run, generated {data['generated']})")

if __name__ == "__main__":
    main()
