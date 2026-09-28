# Ticket Price Tracker

A watchlist for flight and event ticket prices. Add a flight or an event with a target price per ticket, and a scheduled check looks up current prices and alerts you when one drops to your target.

## What's here

`index.html` is the app itself: a Claude artifact page. It stores its watchlist in the artifact's own database (no separate backend), and reads/writes it live so the page always reflects the latest checked prices.

The recurring price check runs as a Claude scheduled task (routine), not as code in this repo. Every hour it reads the watchlist, checks StubHub, Ticketmaster, SeatGeek, Vivid Seats, TickPick, Gametime and AXS (and flight sites for flights) for the current lowest price per watch, and writes the results back.

## Phone alerts

When a price drops strictly under a watch's target, the check posts an alert to an [ntfy](https://ntfy.sh) topic; subscribe to that topic in the ntfy app to get it as a phone notification. A watch alerts once per new low, not every hour. If ntfy can't be reached, the check falls back to a Claude app push notification. The cloud environment running the check must allow `ntfy.sh` in its network settings.

## Using it

Publish `index.html` as a Claude artifact with the `db` capability enabled. From there:

- Add a flight (origin, destination, dates, cabin, travelers) or an event (name, city, date, quantity, section) with a target price.
- The page shows the latest checked price, how it compares to your target, and a trend line across checks.
- Pause, resume, change the target, or delete a watch at any time.

Prices come from public listings at check time and can shift within minutes; confirm on the seller's site before buying.
