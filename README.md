# Ticket Price Tracker

A watchlist for flight and event ticket prices. Add a flight or an event with a target price per ticket, and a scheduled check looks up current prices and alerts you when one drops to your target.

## How it runs

The price check runs on **GitHub Actions**, free for this public repo, and uses no Claude usage.

- `watches.json` is the watchlist. Each watch has a name, event date, `target` price per ticket, `active` flag, and one event page URL per seller. Edit it on GitHub to add, pause or change watches.
- `check.py` fetches each seller page and reads the lowest listed price. It checks the page's structured data first, then prices embedded in the page's app data. With a `SEATGEEK_CLIENT_ID` secret and a watch's `seatgeek_event_id`, it also asks the SeatGeek API.
- `.github/workflows/check-prices.yml` runs the check every 5 minutes. GitHub often starts scheduled runs late, so expect roughly every 5 to 15 minutes. Each run's summary page shows the price from every site, or why a site gave none.
- `state.json` remembers the last price that triggered an alert, so a watch alerts once per new low. When the price goes back up to the target or higher, the watch resets and alerts again on the next drop.

## Phone alerts

When the lowest price is strictly under a watch's target, the check posts to an [ntfy](https://ntfy.sh) topic. Subscribe to the topic in the ntfy app to get it as a phone notification.

Setup:
1. In the repo, go to Settings > Secrets and variables > Actions and add a secret named `NTFY_TOPIC` with your topic name.
2. Go to Actions > Check ticket prices > Run workflow, tick "Also send a test notification", and run it.

## Limits

- Many ticket sites block automated requests, especially StubHub and Ticketmaster. A blocked site shows as `blocked (HTTP 403)` in the run summary, and the check uses whichever sites answered.
- Use the single event page URL for each seller. A page that lists several events is skipped, so a different date's price can't cause a false alert.
- GitHub turns off scheduled workflows in a public repo after 60 days without commits. Re-enable it from the Actions tab.
- Prices can change within minutes. Confirm on the seller's site before you buy.

## The Claude artifact version

`index.html` is the earlier version of this tracker, built as a Claude artifact whose price checks ran as a Claude scheduled task. That scheduled task is now turned off, and the artifact's watchlist is separate from `watches.json`.
