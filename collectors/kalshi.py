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

Settlements (--mode settled), verified 2026-10-21:
  GET /markets?limit=1000&status=settled&min_close_ts=<unix seconds>
  /markets honours min_close_ts with status=settled (every row's close_time
  was inside the window; settled rows carry status "finalized").
  limit: the maximum is 1000; limit=1001 returns 400. limit=200 and 500 are
  accepted.
  /events?status=settled&with_nested_markets=true does NOT honour
  min_close_ts: the same query returned markets closed from 2026-08-01 to
  2031-01-01. So the settled walk goes by /markets.
  Almost every settled market in a 36 hour window is a combo leg: a full
  unfiltered walk of the window ran for over 30 minutes without finishing,
  and the first 1,000-row page was 1,000 of 1,000 combos. /markets honours
  mve_filter: "exclude" returned 1,000 rows with no mve_collection_ticker,
  "only" returned 1,000 combo rows, an unknown value was ignored (combos
  returned). The walk sends mve_filter=exclude, so the combo legs are not
  paged through and the run record carries mve_filter: "exclude". Rows that
  carry mve_collection_ticker anyway are skipped and counted as
  markets_combo_legs_skipped (expected 0). The number of combo legs the
  server held back is not counted.
  The window is 36 hours, not 24, so one missed daily run leaves no hole. A
  market seen in two runs is a reader's dedupe problem, never a writer's.
  A settled market has no settled_time; the settlement stamp is
  settlement_ts. The outcome is result plus settlement_value_dollars.
  rules_sha256 is sha256 of rules_primary, one newline, rules_secondary
  (empty string when null), UTF-8. It is on listings, book and settlement
  rows so a rule edit shows as a changed hash and a book row ties to the
  rules it traded under.
  occurrence_datetime (read 2026-10-21 on the 135,585 settled single-leg rows
  of the 36 hour window): non-null on every row, sports and non-sports alike
  (it was null on the non-sports markets sampled earlier that day, so do not
  rely on null meaning "no game"). It equals expected_expiration_time on
  131,265 of the 135,585 rows. On sports game markets it is the scheduled
  event time the exchange publishes (for example KXNHLGAME-26OCT20TBVGK
  05:30Z, KXNFLGAME-26OCT19WASSF 03:15Z). It was not checked against an
  external schedule, so whether it is kickoff to the minute is not verified;
  KXNBAGAME-26OCT20OKCSAS carried 04:30Z against an expected_expiration_time
  of 07:30Z.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from common import RECORD, REPO, Http, day, hour, record_run, stamp, utcnow, write_jsonl_gz

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
    # Added 2026-10-21 (appended; the order above is untouched).
    "rules_secondary", "early_close_condition", "occurrence_datetime", "created_time", "custom_strike",
    "settlement_bounds_type", "latest_expiration_time",
]
BOOK_FIELDS = [
    "ticker", "event_ticker", "status", "yes_bid_dollars", "yes_ask_dollars", "no_bid_dollars", "no_ask_dollars",
    "yes_bid_size_fp", "yes_ask_size_fp", "last_price_dollars", "volume_fp", "volume_24h_fp", "open_interest_fp", "close_time",
    "occurrence_datetime",  # added 2026-10-21: lets a book row be read against hours to game time
]
SETTLED_FIELDS = [
    "ticker", "event_ticker", "market_type", "status", "title", "yes_sub_title", "no_sub_title",
    "result", "settlement_value_dollars", "settlement_ts", "expiration_value", "settlement_bounds_type",
    "settlement_timer_seconds", "open_time", "close_time", "expiration_time", "latest_expiration_time",
    "expected_expiration_time", "created_time", "early_close_condition", "can_close_early",
    "occurrence_datetime", "custom_strike", "strike_type", "rules_primary", "rules_secondary",
    "last_price_dollars", "volume_fp", "open_interest_fp", "updated_time",
]
WINDOW_HOURS = 36
MVE_FILTER = "exclude"
SETTLED_PAGE = 1000  # the /markets maximum, verified 2026-10-21 (1001 returns 400)
EVENT_FIELDS = ["event_ticker", "series_ticker", "title", "sub_title", "category", "mutually_exclusive", "strike_period", "collateral_return_type", "settlement_sources", "last_updated_ts"]


def rules_sha256(m: dict) -> str | None:
    """sha256 over rules_primary, a newline, rules_secondary (empty when null). None when the market carries no rules_primary key."""
    if "rules_primary" not in m:
        return None
    text = (m.get("rules_primary") or "") + "\n" + (m.get("rules_secondary") or "")
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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
            row["rules_sha256"] = rules_sha256(m)
            if fields is MARKET_FIELDS:
                row["event"] = ev
            else:
                row["category"] = ev.get("category")
            rows.append(row)
    return rows


def walk_settled(http: Http, min_close_ts: int, max_pages: int = 2000) -> tuple[list[dict], dict]:
    """Settled markets that closed at or after min_close_ts, cursor paginated, ended on an empty cursor."""
    markets: list[dict] = []
    cursor = None
    pages = 0
    short_pages = 0
    while pages < max_pages:
        url = f"{BASE}/markets?limit={SETTLED_PAGE}&status=settled&min_close_ts={min_close_ts}&mve_filter={MVE_FILTER}" + (f"&cursor={cursor}" if cursor else "")
        d = http.get_json(url)
        page = d.get("markets") or []
        pages += 1
        markets.extend(page)
        cursor = d.get("cursor") or None
        if len(page) < SETTLED_PAGE:
            short_pages += 1
        if not cursor:
            break
    return markets, {"pages": pages, "short_pages": short_pages, "page_size": SETTLED_PAGE, "ended_on_empty_cursor": cursor is None}


def compact_settled(markets: list[dict], at: str) -> tuple[list[dict], int]:
    """Settlement rows for single-leg markets, and the count of combo legs skipped."""
    rows = []
    skipped = 0
    for m in markets:
        if m.get("mve_collection_ticker"):
            skipped += 1
            continue
        row = {k: m.get(k) for k in SETTLED_FIELDS}  # a key the API omits is written as null, never left out
        row["rules_sha256"] = rules_sha256(m)
        row["at"] = at
        rows.append(row)
    return rows, skipped


def run_settled(started, http: Http, at: str) -> int:
    mode = "settled"
    min_close_ts = int(started.timestamp()) - WINDOW_HOURS * 3600
    try:
        markets, walk = walk_settled(http, min_close_ts)
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:{mode}", source="unavailable", counts={"window_hours": WINDOW_HOURS, "min_close_ts": min_close_ts}, note=repr(e), http=http, started=started)
        return 1
    rows, skipped = compact_settled(markets, at)
    path = RECORD / SLUG / "settlements" / f"{day(started)}.jsonl.gz"
    n, size = write_jsonl_gz(path, rows)
    counts = {
        "markets_returned": len(markets),
        "markets_settled": n,
        "markets_combo_legs_skipped": skipped,
        "window_hours": WINDOW_HOURS,
        "min_close_ts": min_close_ts,
        "mve_filter": MVE_FILTER,
        "bytes_gz": size,
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        **walk,
    }
    source = "live" if walk["ended_on_empty_cursor"] else "partial"
    record_run(f"{SLUG}:{mode}", source=source, counts=counts, http=http, started=started, store="record")
    return 0 if source == "live" else 2


def run(mode: str, out_root: Path) -> int:
    started = utcnow()
    http = Http(min_interval_s=1.1)
    at = stamp(started)
    if mode == "settled":
        return run_settled(started, http, at)
    try:
        events, walk = walk_events(http)
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:{mode}", source="unavailable", counts={}, note=repr(e), http=http, started=started)
        return 1
    n_markets = sum(len(e.get("markets") or []) for e in events)
    n_mve = sum(1 for e in events for m in (e.get("markets") or []) if m.get("mve_collection_ticker"))
    if mode == "daily":
        rows = compact(events, MARKET_FIELDS, at)
        path = RECORD / SLUG / "listings" / f"{day(started)}.jsonl.gz"
        store = "record"
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
    ap.add_argument("--mode", choices=["daily", "hourly", "settled"], default="hourly")
    ap.add_argument("--out", default=str(REPO / "books"), help="root for hourly book files")
    a = ap.parse_args(argv)
    return run(a.mode, Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
