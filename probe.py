"""Temporary diagnostic: show what each seller page returns to a GitHub runner."""
import json, re, urllib.error
from check import fetch, JSONLD_RE, walk

URLS = {
    "StubHub": "https://www.stubhub.com/austin-city-limits-festival-austin-tickets-10-2-2026/event/160034283/",
    "Vivid page": "https://www.vividseats.com/austin-city-limits-festival-tickets-austin-zilker-park-10-2-2026--concerts-music-festivals/production/6173217",
    "Vivid hermes listings": "https://www.vividseats.com/hermes/api/v1/listings?productionId=6173217&includeIpAddress=true&currency=USD",
    "Vivid hermes production": "https://www.vividseats.com/hermes/api/v1/productions/6173217",
    "Ticketmaster artist": "https://www.ticketmaster.com/austin-city-limits-music-festival-presented-tickets/artist/2148250",
    "TickPick": "https://www.tickpick.com/buy-austin-city-limits-music-festival-weekend-one-twenty-one-pilots-rufus-du-sol-charli-xcx-lorde-3-day-pass-tickets-zilker-park-10-2-26-3am/7617998/",
    "Gametime": "https://gametime.co/concert/2026-austin-city-limits-festival-weekend-one-3-day-pass-10-2-10-4-tickets/10-2-2026-austin-tx-zilker-park/events/68f95e10003985ae44495e38",
}
KEY_RE = re.compile(r'.{0,60}"(?:lowPrice|minPrice|lowestPrice|min_price|lowest_price|minListPrice|lowestPriceWithFees|price|p|allInPrice|rawPrice|priceWithFees|minTicketPrice)"\s*:\s*"?\$?\d[\d.,]*.{0,60}', re.I)

for name, url in URLS.items():
    print(f"\n===== {name}")
    try:
        html = fetch(url)
    except urllib.error.HTTPError as e:
        print("HTTP", e.code, e.read()[:200]); continue
    except Exception as e:
        print("ERR", repr(e)); continue
    t = re.search(r"<title>(.*?)</title>", html, re.S)
    print("len", len(html), "title:", t.group(1).strip()[:150] if t else None)
    for i, block in enumerate(JSONLD_RE.findall(html)):
        try:
            data = json.loads(block.strip())
        except ValueError:
            print(f"jsonld[{i}] unparseable"); continue
        for n in walk(data):
            if "offers" in n:
                print(f"jsonld[{i}] {n.get('@type')} {str(n.get('name',''))[:80]!r} start={n.get('startDate')} offers={json.dumps(n['offers'])[:400]}")
    hits = KEY_RE.findall(html)
    print("price-key hits:", len(hits))
    for h in hits[:15]:
        print("  ", h.replace("\n", " "))
    for m in sorted(set(re.findall(r'https?://www\.ticketmaster\.com/[^"\s]*/event/[A-Za-z0-9]+|/[a-z0-9-]*weekend[a-z0-9-]*/event/[A-Za-z0-9]+', html)))[:20]:
        print("  event link:", m)
    for k in ("__NEXT_DATA__", "__INITIAL_STATE__", "__APOLLO_STATE__", "captcha", "Pardon the Interruption", "px-captcha", "cf-chl"):
        if k in html:
            print("  contains", k)
