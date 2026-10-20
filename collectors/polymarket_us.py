"""Polymarket US: every open market from the public gateway.

Endpoint: GET https://gateway.polymarket.us/v1/markets
  limit         caps at 500 (2,000 was silently served as 500)
  offset        pages; `page` is accepted and IGNORED (verified 2026-10-20:
                page=1 and page=2 returned identical ids)
  closed=false  the open set; `status=active` is ignored, `active=true` is a
                narrower flag than closed=false
On 2026-10-20 the open set was 78,174 markets over 157 pages.

What each row carries: the market's own price fields (`outcomePrices`, one
price per side) and metadata. That is a price snapshot the exchange
publishes, not a quote from the book. The book itself is one request per
market at GET /v1/markets/{slug}/book (bids, offers, state), which at 78,000
open markets is not capturable hourly at one request a second. This version
records the published prices every hour and marks `quote_kind:
"outcome_prices"` on every row so a consumer never mistakes it for
top-of-book. A sampled book capture is a follow-up.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from common import DATA, REPO, Http, day, record_run, stamp, utcnow, write_jsonl_gz

BASE = "https://gateway.polymarket.us/v1"
LIMIT = 500
SLUG = "polymarket-us"

DAILY_FIELDS = ["id", "slug", "question", "description", "category", "tags", "marketType", "sportsMarketType", "sportsMarketTypeV2",
                "status", "active", "closed", "archived", "hidden", "comboEnabled", "createdAt", "updatedAt", "startDate", "endDate", "gameStartTime",
                "orderPriceMinTickSize", "minimumTradeQty", "feeCoefficient", "outcomes", "outcomePrices"]


def _sides(m: dict) -> list[dict]:
    out = []
    for s in m.get("marketSides") or []:
        out.append({"id": s.get("id"), "identifier": s.get("identifier"), "description": s.get("description"), "price": s.get("price"), "long": s.get("long")})
    return out


def walk(http: Http, max_pages: int = 1000) -> tuple[list[dict], dict]:
    markets: list[dict] = []
    offset = 0
    pages = 0
    while pages < max_pages:
        d = http.get_json(f"{BASE}/markets?limit={LIMIT}&offset={offset}&closed=false")
        page = d.get("markets") or []
        pages += 1
        markets.extend(page)
        if len(page) < LIMIT:
            break
        offset += LIMIT
    return markets, {"pages": pages, "page_size": LIMIT, "ended_on_short_page": pages < max_pages}


def compact(markets: list[dict], at: str, hourly: bool) -> list[dict]:
    rows = []
    for m in markets:
        if hourly:
            row = {"id": m.get("id"), "slug": m.get("slug"), "active": m.get("active"), "closed": m.get("closed"),
                   "outcome_prices": m.get("outcomePrices"), "sides": [{"id": s["id"], "price": s["price"]} for s in _sides(m)],
                   "end_date": m.get("endDate"), "quote_kind": "outcome_prices", "at": at}
        else:
            row = {k: m.get(k) for k in DAILY_FIELDS if k in m}
            row["sides"] = _sides(m)
            row["quote_kind"] = "outcome_prices"
            row["at"] = at
        rows.append(row)
    return rows


def run(mode: str, out_root: Path) -> int:
    started = utcnow()
    http = Http(min_interval_s=0.8)
    at = stamp(started)
    try:
        markets, walk_info = walk(http)
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:{mode}", source="unavailable", counts={}, note=repr(e), http=http, started=started)
        return 1
    rows = compact(markets, at, hourly=(mode == "hourly"))
    if mode == "daily":
        path = DATA / SLUG / "listings" / f"{day(started)}.jsonl.gz"
        store = "git"
    else:
        path = out_root / SLUG / day(started) / f"{started.strftime('%H')}.jsonl.gz"
        store = "books"
    n, size = write_jsonl_gz(path, rows)
    counts = {
        "markets_open": n,
        "combo_enabled": sum(1 for m in markets if m.get("comboEnabled")),
        "bytes_gz": size,
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        "quote_kind": "outcome_prices",
        **walk_info,
    }
    source = "live" if walk_info["ended_on_short_page"] else "partial"
    record_run(f"{SLUG}:{mode}", source=source, counts=counts, http=http, started=started, store=store)
    return 0 if source == "live" else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["daily", "hourly"], default="hourly")
    ap.add_argument("--out", default=str(REPO / "books"))
    a = ap.parse_args(argv)
    return run(a.mode, Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
