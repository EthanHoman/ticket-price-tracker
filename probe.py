"""Temporary diagnostic: load blocked seller pages in headless Chromium on a GitHub runner."""
import json, re
from playwright.sync_api import sync_playwright

URLS = {
    "StubHub": "https://www.stubhub.com/austin-city-limits-festival-austin-tickets-10-2-2026/event/160034283/",
    "Vivid": "https://www.vividseats.com/austin-city-limits-festival-tickets-austin-zilker-park-10-2-2026--concerts-music-festivals/production/6173217",
    "Ticketmaster": "https://www.ticketmaster.com/austin-city-limits-music-festival-presented-tickets/artist/2148250",
}
LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S)
KEY = re.compile(r'.{0,50}"(?:lowPrice|minPrice|lowestPrice|minListPrice|price|rawPrice)"\s*:\s*"?\$?\d[\d.,]*.{0,50}')
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, url in URLS.items():
        print(f"\n===== {name}")
        pg = b.new_page()
        try:
            r = pg.goto(url, wait_until="domcontentloaded", timeout=45000)
            pg.wait_for_timeout(8000)
            html = pg.content()
            print("status", r.status if r else None, "title", pg.title()[:120], "len", len(html))
            for blk in LD.findall(html):
                if "offers" in blk:
                    print("  jsonld:", blk.strip()[:500])
            for h in KEY.findall(html)[:10]:
                print("  key:", h)
            print("  text $:", re.findall(r"\$\s?\d[\d,]{2,}", pg.inner_text("body"))[:20])
            for m in sorted(set(re.findall(r'https?://www\.ticketmaster\.com/[^"\s]*/event/[A-Za-z0-9]+', html)))[:15]:
                print("  event link:", m)
        except Exception as e:
            print("ERR", repr(e)[:300])
        pg.close()
    b.close()
