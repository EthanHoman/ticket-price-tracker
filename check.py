#!/usr/bin/env python3
"""Check ticket prices for each watch in watches.json and send an ntfy alert
when the lowest price drops under the target.

Runs on GitHub Actions (see .github/workflows/check-prices.yml). Standard
library only. Alert state lives in state.json so a watch alerts once per new
low instead of on every run.
"""
import datetime
import gzip
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
WATCHES = os.path.join(ROOT, "watches.json")
STATE = os.path.join(ROOT, "state.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}
MIN_PLAUSIBLE = 5  # ignore prices below this; they are fees or placeholders, not tickets

JSONLD_RE = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.S | re.I)
# Fallback for pages that embed prices in app state instead of JSON-LD.
FALLBACK_RE = re.compile(
    r'"(?:lowPrice|minPrice|lowestPrice|min_price|lowest_price|minListPrice|lowestPriceWithFees)"'
    r'\s*:\s*"?\$?(\d+(?:\.\d+)?)')


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read()
        enc = r.headers.get("Content-Encoding", "")
    if enc == "gzip":
        body = gzip.decompress(body)
    elif enc == "deflate":
        body = zlib.decompress(body)
    return body.decode("utf-8", "replace")


_browser = None


def fetch_browser(url):
    """Load a page in headless Chromium, for sellers that only serve prices to
    real browsers. Returns None if Playwright isn't installed."""
    global _browser
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    if _browser is None:
        _browser = sync_playwright().start().chromium.launch()
    page = _browser.new_page()
    try:
        resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
        page.wait_for_timeout(5000)
        if resp and resp.status >= 400:
            raise urllib.error.HTTPError(url, resp.status, "blocked", None, None)
        return page.content()
    finally:
        page.close()


def walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def to_price(v):
    try:
        p = float(str(v).replace(",", "").lstrip("$"))
    except (TypeError, ValueError):
        return None
    return p if p >= MIN_PLAUSIBLE else None


def offer_prices(offers):
    out = []
    for o in walk(offers):
        for key in ("lowPrice", "price"):
            p = to_price(o.get(key))
            if p is not None:
                out.append(p)
                break
    return out


def price_from_html(html, date):
    """Return (price, method) or (None, reason)."""
    events = []
    for block in JSONLD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for node in walk(data):
            if "offers" in node and ("startDate" in node or "Event" in str(node.get("@type", ""))):
                events.append(node)
    if date:
        dated = [e for e in events if str(e.get("startDate", "")).startswith(date)]
        events = dated or events
    if len(events) == 1:
        prices = offer_prices(events[0]["offers"])
        if prices:
            return min(prices), "json-ld"
    elif len(events) > 1:
        return None, f"page lists {len(events)} events; use the single event page URL"

    found = [p for p in (to_price(m) for m in FALLBACK_RE.findall(html)) if p is not None]
    if found:
        return min(found), "embedded data"
    return None, "no price found on page"


def seatgeek_price(event_id):
    cid = os.environ.get("SEATGEEK_CLIENT_ID")
    if not cid:
        return None, "set SEATGEEK_CLIENT_ID secret to use the SeatGeek API"
    q = urllib.parse.urlencode({"client_id": cid})
    data = json.loads(fetch(f"https://api.seatgeek.com/2/events/{event_id}?{q}"))
    p = to_price((data.get("stats") or {}).get("lowest_price"))
    return (p, "seatgeek api") if p else (None, "no listings in SeatGeek API")


def check_watch(w):
    results = []  # (site, price, detail, url)
    for site, url in (w.get("urls") or {}).items():
        if not url:
            continue
        price, detail = None, "not checked"
        # Plain request first; sites that block it or hide prices get a real browser.
        for how, get in (("", fetch), ("browser, ", fetch_browser)):
            try:
                html = get(url)
                if html is None:
                    break
                price, detail = price_from_html(html, w.get("date"))
            except urllib.error.HTTPError as e:
                price, detail = None, f"blocked (HTTP {e.code})"
            except Exception as e:  # network errors, timeouts, bad encodings
                price, detail = None, f"error: {type(e).__name__}"
            detail = how + detail
            if price is not None:
                break
        results.append((site, price, detail, url))
    if w.get("seatgeek_event_id"):
        try:
            price, detail = seatgeek_price(w["seatgeek_event_id"])
        except Exception as e:
            price, detail = None, f"error: {type(e).__name__}"
        results.append(("SeatGeek API", price, detail, f"https://seatgeek.com/e/{w['seatgeek_event_id']}"))
    return results


def notify(title, message, click=None, priority="high"):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set; skipping notification:", message)
        return False
    headers = {"Title": title, "Priority": priority, "Tags": "ticket"}
    if click:
        headers["Click"] = click
    req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=message.encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=20) as r:
        return 200 <= r.status < 300


def money(p):
    return f"${p:,.0f}" if p is not None else "n/a"


def main():
    if os.environ.get("TEST_NOTIFICATION") == "true":
        ok = notify("Ticket Watch test", "GitHub Actions can reach your phone. Alerts will look like this.", priority="default")
        print("Test notification sent" if ok else "Test notification failed")

    watches = json.load(open(WATCHES))
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    today = datetime.date.today().isoformat()
    summary = [f"## Ticket Watch check {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC\n"]
    alerts = []

    for w in watches:
        wid, target = w["id"], float(w["target"])
        if not w.get("active", True):
            summary.append(f"**{w['name']}**: paused\n")
            continue
        if w.get("date") and w["date"] < today:
            summary.append(f"**{w['name']}**: date has passed, skipped\n")
            continue

        results = check_watch(w)
        priced = [r for r in results if r[1] is not None]
        summary.append(f"### {w['name']} (target {money(target)})\n\n| Site | Price | Detail |\n|---|---|---|")
        for site, price, detail, url in results:
            summary.append(f"| [{site}]({url}) | {money(price)} | {detail} |")
        summary.append("")

        st = state.setdefault(wid, {"alerted_price": None})
        if not priced:
            summary.append("No site returned a price this run.\n")
            continue
        site, price, _, url = min(priced, key=lambda r: r[1])
        summary.append(f"Lowest: **{money(price)}** on {site}\n")

        if price < target:
            if st["alerted_price"] is None or price < st["alerted_price"]:
                alerts.append((w, site, price, url))
                st["alerted_price"] = price
        elif st["alerted_price"] is not None:
            # Back at or above target: re-arm so the next drop alerts again.
            st["alerted_price"] = None

    for w, site, price, url in alerts:
        msg = f"{w['name']}: {money(price)}/ticket on {site}, under your {money(float(w['target']))} target"
        try:
            ok = notify("Ticket Watch: price under target", msg, click=url)
        except Exception as e:
            ok = False
            print("ntfy error:", e)
        print(("Alert sent: " if ok else "Alert FAILED: ") + msg)
        summary.append(("Alert sent: " if ok else "Alert failed: ") + msg + "\n")

    with open(STATE, "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")

    text = "\n".join(summary)
    print(text)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(text + "\n")


if __name__ == "__main__":
    # `python3 check.py --every 5` keeps checking every 5 minutes until stopped.
    if len(sys.argv) == 3 and sys.argv[1] == "--every":
        import time
        while True:
            try:
                main()
            except Exception as e:  # keep looping through network hiccups
                print("Check failed:", repr(e))
            time.sleep(float(sys.argv[2]) * 60)
    sys.exit(main())
