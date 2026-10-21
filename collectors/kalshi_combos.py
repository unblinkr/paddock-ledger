"""Kalshi combo (multivariate) collections: what each collection spans and the price structure it publishes.

The single-leg Kalshi record skips combo markets and counts them. This module
captures the collections themselves, once a day, as served. No hold, margin or
implied probability is computed here; `price_ranges` and `price_level_structure`
are stored exactly as the API returns them (lists and strings, nothing rounded
or flattened). Analysis happens elsewhere.

Endpoint: GET https://api.elections.kalshi.com/trade-api/v2/multivariate_event_collections
  Response: {"cursor": ..., "multivariate_contracts": [...]}
Verified 2026-10-21:
  limit   limit=200 and 1000 returned that many rows with a cursor; limit=1001
          returned 1001; limit=5000 returned 1,406 rows and no cursor. No
          maximum was found up to 5000. The collector asks for 1000 (PAGE) and
          asserts the walk ended on an empty cursor.
  status  `status=open` is honoured (3 rows). Unknown values such as
          status=bogus are silently ignored (100 rows and a cursor, as with no
          filter). The collector sends no status filter: closed collections are
          part of the record.
  total   1,406 collections on 2026-10-21, 3 of them very large (about 340 KB
          each, 800+ associated events); the rest about 1.2 KB.
Pagination is cursor based and the walk ends on an empty cursor.
"""

from __future__ import annotations

import sys

from common import RECORD, REPO, Http, day, record_run, stamp, utcnow, write_jsonl_gz

BASE = "https://api.elections.kalshi.com/trade-api/v2"
PAGE = 1000
SLUG = "kalshi-combos"

COLLECTION_FIELDS = [
    "collection_ticker", "series_ticker", "title", "description", "functional_description",
    "associated_event_tickers", "associated_events", "is_all_yes", "is_ordered", "is_single_market_per_event",
    "size_min", "size_max", "price_level_structure", "price_ranges", "open_date", "close_date", "exchange_index",
]


def walk(http: Http, max_pages: int = 100) -> tuple[list[dict], dict]:
    items: list[dict] = []
    cursor = None
    pages = 0
    while pages < max_pages:
        url = f"{BASE}/multivariate_event_collections?limit={PAGE}" + (f"&cursor={cursor}" if cursor else "")
        d = http.get_json(url)
        items.extend(d.get("multivariate_contracts") or [])
        pages += 1
        cursor = d.get("cursor") or None
        if not cursor:
            break
    return items, {"pages": pages, "page_size": PAGE, "ended_on_empty_cursor": cursor is None}


def compact(items: list[dict], at: str) -> list[dict]:
    rows = []
    for c in items:
        row = {k: c.get(k) for k in COLLECTION_FIELDS if k in c}
        row["at"] = at
        rows.append(row)
    return rows


def run() -> int:
    started = utcnow()
    http = Http(min_interval_s=1.1)
    at = stamp(started)
    try:
        items, w = walk(http)
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:daily", source="unavailable", counts={}, note=repr(e), http=http, started=started)
        return 1
    rows = compact(items, at)
    path = RECORD / "kalshi" / "combos" / f"{day(started)}.jsonl.gz"
    n, size = write_jsonl_gz(path, rows)
    counts = {
        "collections": n,
        "bytes_gz": size,
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        **w,
    }
    source = "live" if w["ended_on_empty_cursor"] else "partial"
    record_run(f"{SLUG}:daily", source=source, counts=counts, http=http, started=started, store="record")
    return 0 if source == "live" else 2


def main(argv: list[str] | None = None) -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
