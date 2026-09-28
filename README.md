# Ticket Price Tracker

A watchlist for flight and event ticket prices. Add a flight or an event with a target price per ticket, and a scheduled check looks up current prices and alerts you when one drops to your target.

## What's here

`index.html` is the app itself: a Claude artifact page. It stores its watchlist in the artifact's own database (no separate backend), and reads/writes it live so the page always reflects the latest checked prices.

The recurring price check runs as a Claude scheduled task, not as code in this repo: it reads the watchlist, searches flight and ticket sites for the current lowest price per watch, writes results back, and sends a push notification when a target is hit.

## Using it

Publish `index.html` as a Claude artifact with the `db` capability enabled. From there:

- Add a flight (origin, destination, dates, cabin, travelers) or an event (name, city, date, quantity, section) with a target price.
- The page shows the latest checked price, how it compares to your target, and a trend line across checks.
- Pause, resume, change the target, or delete a watch at any time.

Prices come from public listings at check time and can shift within minutes; confirm on the seller's site before buying.
