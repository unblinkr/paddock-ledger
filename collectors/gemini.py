"""Gemini Predictions: active events with nested contracts and top-of-book.

Endpoint: GET https://api.gemini.com/v1/prediction-markets/events
  limit     up to 500 (a larger value is silently reduced to 500)
  offset    pages; `page` is accepted and IGNORED by the server (verified
            2026-10-20: pages 1, 2, 11 and 30 returned identical ids)
  category  filters (Sports, Weather, Crypto, Commodities, ...)
  status    active | settled

The cap: every query reports `pagination.total: 1000` whatever the filter,
and offset 1000 returns nothing, so no single query can see more than 1,000
events. The collector walks each known category separately and records,
per category, whether it hit the cap. A category at the cap is flagged
`truncated: true` in the run record; that is the disclosure, not a guess at
what was missed. Add a category to CATEGORIES when a new one appears in the
uncategorized walk (the run record lists any it finds).

Each contract carries bestBid, bestAsk, lastTradePrice and buy/sell prices,
so one walk is both the listings snapshot and the hourly book. Depth exists
at GET /v1/book/{instrumentSymbol} but is one request per contract and is not
captured in this version.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from common import DATA, REPO, FetchError, Http, day, record_run, stamp, utcnow, write_jsonl_gz

BASE = "https://api.gemini.com/v1/prediction-markets"
LIMIT = 500
CAP = 1000  # the server's own ceiling per query, asserted below
SLUG = "gemini"
# Valid on 2026-10-20 (the API 400s on any other name; the run record lists
# the names it rejected so a new category is noticed, never guessed).
CATEGORIES = ["Sports", "Weather", "Crypto", "Commodities", "Politics", "Economics", "Finance", "Culture", "Business", "Esports", "Other"]

EVENT_FIELDS = ["id", "ticker", "slug", "title", "type", "category", "subcategory", "series", "status", "isLive", "createdAt", "startTime", "effectiveDate", "expiryDate", "volume", "volume24h", "source", "tags", "eventTags"]
CONTRACT_FIELDS = ["id", "ticker", "instrumentSymbol", "label", "abbreviatedName", "status", "marketState", "isCombo", "effectiveDate", "expiryDate", "strike", "priceIncrement", "quantityMinimum", "termsAndConditionsUrl"]


def walk(http: Http, category: str | None, status: str = "active") -> tuple[list[dict], dict]:
    events: list[dict] = []
    offset = 0
    pages = 0
    total_reported = None
    while True:
        url = f"{BASE}/events?limit={LIMIT}&offset={offset}&status={status}" + (f"&category={category}" if category else "")
        d = http.get_json(url)
        page = d.get("data") or []
        pag = d.get("pagination") or {}
        total_reported = pag.get("total")
        pages += 1
        events.extend(page)
        if len(page) < LIMIT:
            break
        offset += LIMIT
        if offset >= CAP:
            break
    return events, {"pages": pages, "returned": len(events), "total_reported": total_reported, "truncated": len(events) >= CAP}


def compact(events: list[dict], at: str, hourly: bool) -> list[dict]:
    rows = []
    for e in events:
        ev = {k: e.get(k) for k in EVENT_FIELDS if k in e}
        for c in e.get("contracts") or []:
            p = c.get("prices") or {}
            row = {
                "event_id": e.get("id"),
                "instrument": c.get("instrumentSymbol"),
                "contract_ticker": c.get("ticker"),
                "market_state": c.get("marketState"),
                "is_combo": c.get("isCombo"),
                "best_bid": p.get("bestBid"),
                "best_ask": p.get("bestAsk"),
                "last_trade_price": p.get("lastTradePrice"),
                "buy_yes": (p.get("buy") or {}).get("yes"),
                "sell_yes": (p.get("sell") or {}).get("yes"),
                "at": at,
            }
            if hourly:
                row["category"] = e.get("category")
                row["expiry"] = c.get("expiryDate")
            else:
                row["contract"] = {k: c.get(k) for k in CONTRACT_FIELDS if k in c}
                row["event"] = ev
            rows.append(row)
    return rows


def run(mode: str, out_root: Path) -> int:
    started = utcnow()
    http = Http(min_interval_s=0.6)
    at = stamp(started)
    per_cat: dict[str, dict] = {}
    seen: dict[str, dict] = {}
    unknown_categories: set[str] = set()
    try:
        base_events, base_walk = walk(http, None)
        per_cat["(all)"] = base_walk
        for e in base_events:
            seen[e["id"]] = e
            if e.get("category") and e["category"] not in CATEGORIES:
                unknown_categories.add(e["category"])
        rejected: list[str] = []
        for cat in CATEGORIES + sorted(unknown_categories):
            try:
                evs, w = walk(http, cat)
            except FetchError as fe:
                if "400 " in str(fe):
                    rejected.append(cat)  # the API does not know this category name
                    continue
                raise
            per_cat[cat] = w
            for e in evs:
                seen[e["id"]] = e
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:{mode}", source="unavailable", counts={"per_category": per_cat}, note=repr(e), http=http, started=started)
        return 1
    events = list(seen.values())
    rows = compact(events, at, hourly=(mode == "hourly"))
    if mode == "daily":
        path = DATA / SLUG / "listings" / f"{day(started)}.jsonl.gz"
        store = "git"
    else:
        path = out_root / SLUG / day(started) / f"{started.strftime('%H')}.jsonl.gz"
        store = "books"
    n, size = write_jsonl_gz(path, rows)
    # "(all)" is only the discovery pass for category names; coverage comes
    # from the per-category walks, so only a category at the cap is a gap.
    truncated = [c for c, w in per_cat.items() if w.get("truncated") and c != "(all)"]
    counts = {
        "events": len(events),
        "contracts": n,
        "combos": sum(1 for r in rows if r.get("is_combo")),
        "bytes_gz": size,
        "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
        "query_cap": CAP,
        "categories_at_cap": truncated,
        "unknown_categories_seen": sorted(unknown_categories),
        "categories_rejected_by_api": rejected,
        "per_category": per_cat,
    }
    source = "partial" if truncated else "live"
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
