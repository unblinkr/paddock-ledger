"""The listings ledger: the CFTC's own record of what every designated contract
market filed.

Two public lists on cftc.gov, both HTML tables, 50 rows a page, newest first:

  TradingOrganizationProducts  new products (Rule 40.2 certifications, 40.3
                               approvals), one row per product filing
  PTCDCMRules                  product terms-and-conditions rule changes to
                               existing products (amendments, delistings,
                               tick changes), one row per filing

Each row links to a detail page (/IndustryOversight/IndustryFilings/<list>/<id>)
that carries the receipt date, status, remarks and the PDF documents.

What this collector keeps, append-only, keyed by the CFTC's own filing id:

  data/cftc/products.jsonl        one line per product filing, list columns
  data/cftc/product-rules.jsonl   one line per rule filing, list columns
  data/cftc/details/<id>.json     the detail page fields and document links,
                                  fetched once per new filing

Rows are never rewritten. A filing whose Status changes (Approval Pending ->
Certified) appears as a second line with a later `seen` stamp; the ledger is
the history, consumers take the latest line per id.

Pagination: `?page=N`, 0-based. The daily run walks pages until a page has no
id it has not seen, then stops; `--all` walks every page (a one-time backfill,
about 450 pages at one request a second). Truncation is detected by asserting
the row count per page against the table's own `page=last` link.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

from common import DATA, Http, append_jsonl, read_jsonl, record_run, stamp, utcnow, write_atomic

BASE = "https://www.cftc.gov"
LISTS = {
    "products": {
        "path": "/IndustryOversight/IndustryFilings/TradingOrganizationProducts",
        "file": DATA / "cftc" / "products.jsonl",
        "columns": ["organization", "product_name", "type", "status", "date", "category", "subcategory", "remarks", "documents"],
    },
    "product-rules": {
        "path": "/IndustryOversight/IndustryFilings/PTCDCMRules",
        "file": DATA / "cftc" / "product-rules.jsonl",
        "columns": ["organization", "filing_description", "products_affected", "receipt_date", "status", "date", "remarks", "documents"],
    },
}
PAGE_SIZE = 50  # the site's own page size; a page shorter than this is the last page

_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_CELL = re.compile(r"<td[^>]*>(.*?)</td>", re.S)
_HREF = re.compile(r'href="([^"]+)"')
_TAG = re.compile(r"<[^>]+>")
_LAST = re.compile(r'href="\?page=(\d+)"[^>]*title="Go to last page"')


def _text(fragment: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", _TAG.sub(" ", fragment))).strip()


_MDY = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def iso_date(s: str) -> str:
    """The site prints MM/DD/YYYY; the ledger stores YYYY-MM-DD so rows sort."""
    m = _MDY.match(s.strip())
    return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}" if m else s


def parse_list_page(page_html: str, columns: list[str]) -> tuple[list[dict], int | None]:
    """Rows of the filings table plus the last-page index the page advertises."""
    rows = []
    for tr in _ROW.findall(page_html):
        cells = _CELL.findall(tr)
        if len(cells) != len(columns):
            continue
        link = next((h for h in _HREF.findall(tr) if "/IndustryFilings/" in h), None)
        if not link:
            continue
        row = {col: _text(c) for col, c in zip(columns, cells)}
        for col in ("date", "receipt_date"):
            if col in row:
                row[col] = iso_date(row[col])
        row["id"] = int(link.rstrip("/").rsplit("/", 1)[-1])
        row["url"] = BASE + link
        rows.append(row)
    m = _LAST.search(page_html)
    last = int(m.group(1)) if m else None
    return rows, last


_DETAIL_FIELD = re.compile(r"(Organization|Description|Product Name|Official Receipt Date|Status|Date|Remarks|Type|Category|Subcategory):\s*(.*?)\s*(?=(?:Organization|Description|Product Name|Official Receipt Date|Status|Date|Remarks|Type|Category|Subcategory|Associated Documents):|Associated Documents|$)")
_PDF = re.compile(r'<a[^>]*href="(https?://www\.cftc\.gov/filings/[^"]+\.pdf|/filings/[^"]+\.pdf)"[^>]*>(.*?)</a>', re.S)


def parse_detail_page(page_html: str) -> dict:
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", page_html, flags=re.S)
    text = _text(body)
    i = text.find("Organization:")
    fields = {}
    if i >= 0:
        seg = text[i:]
        for k, v in _DETAIL_FIELD.findall(seg):
            key = k.lower().replace(" ", "_")
            if key not in fields:
                fields[key] = v.strip()
    docs = [{"url": (u if u.startswith("http") else BASE + u), "title": _text(t)} for u, t in _PDF.findall(page_html)]
    return {"fields": fields, "documents": docs}


def collect(list_name: str, http: Http, walk_all: bool = False, max_pages: int = 500, details: bool = True) -> dict:
    spec = LISTS[list_name]
    known = read_jsonl(spec["file"])
    seen_ids = {(r["id"], r["status"]) for r in known}
    seen_any = {r["id"] for r in known}
    new_rows: list[dict] = []
    pages = 0
    last_advertised = None
    page = 0
    short_page = False
    while page < max_pages:
        page_html = http.get(f"{BASE}{spec['path']}?page={page}").decode("utf-8", "replace")
        rows, last = parse_list_page(page_html, spec["columns"])
        pages += 1
        if last is not None:
            last_advertised = last
        fresh = [r for r in rows if (r["id"], r["status"]) not in seen_ids]
        for r in fresh:
            r["seen"] = stamp()
            r["list"] = list_name
            seen_ids.add((r["id"], r["status"]))
        new_rows.extend(fresh)
        if len(rows) < PAGE_SIZE:
            short_page = True  # the last page, by the site's own page size
            break
        if not walk_all and not fresh:
            break  # a full page with nothing new: everything older is already on file
        page += 1
    # Detail pages once per filing id we have never fetched a detail for.
    details_dir = DATA / "cftc" / "details"
    details_fetched = 0
    details_failed = 0
    for r in (new_rows if details else []):
        if r["id"] in seen_any:
            continue
        seen_any.add(r["id"])
        out = details_dir / f"{r['id']}.json"
        if out.exists():
            continue
        try:
            d = parse_detail_page(http.get(r["url"]).decode("utf-8", "replace"))
            d.update({"id": r["id"], "list": list_name, "url": r["url"], "fetched": stamp()})
            write_atomic(out, (json.dumps(d, sort_keys=True, ensure_ascii=False, indent=0) + "\n").encode("utf-8"))
            details_fetched += 1
        except Exception as e:  # noqa: BLE001 - a detail miss must not lose the list row
            details_failed += 1
            print(f"detail {r['id']}: {e}", file=sys.stderr)
    # Oldest first within the batch so the file reads chronologically.
    new_rows.sort(key=lambda r: (r["date"], r["id"]))
    append_jsonl(spec["file"], new_rows)
    return {
        "pages_walked": pages,
        "last_page_advertised": last_advertised,
        "reached_last_page": short_page,
        "new_rows": len(new_rows),
        "details_fetched": details_fetched,
        "details_requested": details,
        "details_failed": details_failed,
        "total_rows_on_file": len(known) + len(new_rows),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", choices=sorted(LISTS), action="append", help="default: both")
    ap.add_argument("--all", action="store_true", help="walk every page (backfill)")
    ap.add_argument("--max-pages", type=int, default=500)
    ap.add_argument("--no-details", action="store_true", help="list rows only; detail pages are one request each and a full backfill is 28,000 of them")
    a = ap.parse_args(argv)
    lists = a.list or sorted(LISTS)
    rc = 0
    for name in lists:
        started = utcnow()
        http = Http(min_interval_s=1.0)
        try:
            counts = collect(name, http, walk_all=a.all, max_pages=a.max_pages, details=not a.no_details)
            record_run(f"cftc:{name}", source="live", counts=counts, http=http, started=started)
        except Exception as e:  # noqa: BLE001
            record_run(f"cftc:{name}", source="unavailable", counts={}, note=repr(e), http=http, started=started)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
