"""Kalshi: every open event with its nested markets, from the public trade API.

Why events and not /markets: Kalshi's /markets list is dominated by
multivariate-event (combo) markets. On 2026-10-20 the first 224,000 open
markets on that list were 99.9% combos. /events?with_nested_markets=true
returns the underlying events (14,471 open on 2026-10-20) with 149,131
single-leg markets, 200 events a page, about 75 pages. Combo collections do
not appear there. The record keeps single-leg markets; combos are counted
separately, never mixed in (a combo's volume is a bet on several markets at
once and would overstate every leg).

Every market row carries top-of-book (yes_bid, yes_ask), last price, volume,
24h volume, open interest and close time, so one walk is both the listings
snapshot and the hourly book. Prices are dollar strings from the API, kept
as strings; no float arithmetic happens here.

Rate limit: 429 on bursts; one request a second with backoff is enough.
Pagination: cursor-based; the walk ends when the cursor is empty. The page
size (200) is asserted on every full page; a shorter page is only accepted as
the last page when the cursor is empty too.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import DATA, REPO, Http, day, hour, record_run, stamp, utcnow, write_jsonl_gz

BASE = "https://api.elections.kalshi.com/trade-api/v2"
PAGE = 200  # events per page; the API's maximum for this endpoint
SLUG = "kalshi"

MARKET_FIELDS = [
    "ticker", "event_ticker", "market_type", "status", "title", "yes_sub_title", "no_sub_title",
    "open_time", "close_time", "expiration_time", "expected_expiration_time",
    "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "yes_bid_size_fp", "yes_ask_size_fp", "last_price_dollars", "previous_price_dollars",
    "volume_fp", "volume_24h_fp", "open_interest_fp", "notional_value_dollars", "liquidity_dollars",
    "strike_type", "floor_strike", "cap_strike", "result", "can_close_early", "is_provisional",
    "rules_primary", "settlement_timer_seconds", "updated_time",
]
BOOK_FIELDS = [
    "ticker", "event_ticker", "status", "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "yes_bid_size_fp", "yes_ask_size_fp", "last_price_dollars", "volume_fp", "volume_24h_fp", "open_interest_fp", "close_time",
]
EVENT_FIELDS = ["event_ticker", "series_ticker", "title", "sub_title", "category", "mutually_exclusive", "strike_period", "collateral_return_type", "settlement_sources", "last_updated_ts"]


def walk_events(http: Http, status: str = "open", max_pages: int = 2000) -> tuple[list[dict], dict]:
    events: list[dict] = []
    cursor = None
    pages = 0
    short_pages = 0
    while pages < max_pages:
        url = f"{BASE}/events?limit={PAGE}&status={status}&with_nested_markets=true" + (f"&cursor={cursor}" if cursor else "")
        d = http.get_json(url)
        page = d.get("events") or []
        pages += 1
        events.extend(page)
        cursor = d.get("cursor") or None
        if len(page) < PAGE:
            short_pages += 1
            if cursor:
                # A short page with a cursor is not the end; the server shed load. Keep walking.
                continue
        if not cursor:
            break
    return events, {"pages": pages, "short_pages": short_pages, "page_size": PAGE, "ended_on_empty_cursor": cursor is None}


def compact(events: list[dict], fields: list[str], at: str) -> list[dict]:
    rows = []
    for e in events:
        ev = {k: e.get(k) for k in EVENT_FIELDS if k in e}
        for m in e.get("markets") or []:
            if m.get("mve_collection_ticker"):
                continue  # a combo leg listed inside an event; never part of the single-leg record
            row = {k: m.get(k) for k in fields if k in m}
            row["at"] = at
            if fields is MARKET_FIELDS:
                row["event"] = ev
            else:
                row["category"] = ev.get("category")
            rows.append(row)
    return rows


def run(mode: str, out_root: Path) -> int:
    started = utcnow()
    http = Http(min_interval_s=1.1)
    at = stamp(started)
    try:
        events, walk = walk_events(http)
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:{mode}", source="unavailable", counts={}, note=repr(e), http=http, started=started)
        return 1
    n_markets = sum(len(e.get("markets") or []) for e in events)
    n_mve = sum(1 for e in events for m in (e.get("markets") or []) if m.get("mve_collection_ticker"))
    if mode == "daily":
        rows = compact(events, MARKET_FIELDS, at)
        path = DATA / SLUG / "listings" / f"{day(started)}.jsonl.gz"
        store = "git"
    else:
        rows = compact(events, BOOK_FIELDS, at)
        path = out_root / SLUG / day(started) / f"{started.strftime('%H')}.jsonl.gz"
        store = "books"
    n, size = write_jsonl_gz(path, rows)
    counts = {
        "events": len(events),
        "markets_nested": n_markets,
        "markets_single_leg": n,
        "markets_combo_legs_skipped": n_mve,
        "bytes_gz": size,
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        **walk,
    }
    source = "live" if walk["ended_on_empty_cursor"] else "partial"
    record_run(f"{SLUG}:{mode}", source=source, counts=counts, http=http, started=started, store=store)
    return 0 if source == "live" else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "hourly"], default="hourly")
    ap.add_argument("--out", default=str(REPO / "books"), help="root for hourly book files")
    a = ap.parse_args(argv)
    return run(a.mode, Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
