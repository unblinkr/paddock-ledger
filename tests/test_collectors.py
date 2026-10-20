"""Parser tests on responses saved from the live sources on 2026-10-20.

Each fixture is a real response. The tests pin what the collectors rely on,
so an upstream shape change fails here before it quietly empties a day.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

import cftc  # noqa: E402
import gemini  # noqa: E402
import kalshi  # noqa: E402
import polymarket_us  # noqa: E402

FX = ROOT / "tests" / "fixtures"


def test_cftc_products_page_parses_fifty_rows_with_ids_and_iso_dates():
    rows, last = cftc.parse_list_page((FX / "cftc-products-page0.html").read_text(), cftc.LISTS["products"]["columns"])
    assert len(rows) == 50
    assert last == 447
    r = rows[0]
    assert r["organization"] == "KEX"
    assert r["id"] == 65491
    assert r["date"] == "2026-10-20"
    assert r["type"] == "Swap (Binary Option)"
    assert r["url"].endswith("/TradingOrganizationProducts/65491")
    assert {"product_name", "status", "category", "subcategory", "documents"} <= set(r)


def test_cftc_product_rules_page_parses_with_receipt_date():
    rows, last = cftc.parse_list_page((FX / "cftc-product-rules-page0.html").read_text(), cftc.LISTS["product-rules"]["columns"])
    assert len(rows) == 50
    assert last == 121
    assert rows[0]["id"] == 65428
    assert rows[0]["receipt_date"] == "2026-10-19"
    assert rows[0]["status"] == "10 Day Review"


def test_cftc_detail_page_yields_fields_and_pdf_documents():
    d = cftc.parse_detail_page((FX / "cftc-product-rule-65428.html").read_text())
    assert d["fields"]["organization"] == "KEX"
    assert d["fields"]["status"] == "10 Day Review"
    assert len(d["documents"]) == 3
    assert d["documents"][1]["title"] == "Redline"
    assert all(doc["url"].startswith("https://www.cftc.gov/filings/") for doc in d["documents"])


def test_cftc_page_size_is_the_sites_own():
    # A page shorter than this is read as the last page. If the site changes
    # its page size, the walk would stop after page 0 and this catches it.
    assert cftc.PAGE_SIZE == 50


def test_kalshi_compact_keeps_single_leg_markets_and_drops_combo_legs():
    d = json.loads((FX / "kalshi-events.json").read_text())
    events = d["events"]
    nested = sum(len(e["markets"]) for e in events)
    rows = kalshi.compact(events, kalshi.BOOK_FIELDS, "2026-10-20T18:00:00Z")
    assert len(rows) == nested  # no combo legs inside events in this fixture
    assert all("yes_bid_dollars" in r and "yes_ask_dollars" in r for r in rows)
    assert rows[0]["category"] == events[0]["category"]
    # A combo leg injected into an event must be dropped, never recorded.
    events[0]["markets"][0]["mve_collection_ticker"] = "KXMVE-TEST"
    rows2 = kalshi.compact(events, kalshi.BOOK_FIELDS, "x")
    assert len(rows2) == nested - 1


def test_kalshi_prices_stay_strings():
    d = json.loads((FX / "kalshi-events.json").read_text())
    rows = kalshi.compact(d["events"], kalshi.MARKET_FIELDS, "x")
    for r in rows:
        for k in ("yes_bid_dollars", "yes_ask_dollars", "last_price_dollars", "volume_fp"):
            assert isinstance(r[k], str), k


def test_gemini_compact_reads_top_of_book_per_contract():
    d = json.loads((FX / "gemini-events.json").read_text())
    rows = gemini.compact(d["data"], "x", hourly=True)
    assert len(rows) == sum(len(e["contracts"]) for e in d["data"])
    r = rows[0]
    assert r["instrument"].startswith("GEMI-")
    assert r["best_bid"] and r["best_ask"]
    assert r["is_combo"] is False
    assert r["category"] == d["data"][0]["category"]


def test_gemini_cap_is_named():
    assert gemini.CAP == 1000
    assert gemini.LIMIT == 500


def test_polymarket_us_compact_marks_quote_kind():
    d = json.loads((FX / "polymarket-us-markets.json").read_text())
    rows = polymarket_us.compact(d["markets"], "x", hourly=True)
    assert len(rows) == 3
    assert all(r["quote_kind"] == "outcome_prices" for r in rows)
    assert rows[0]["sides"] and "price" in rows[0]["sides"][0]
    daily = polymarket_us.compact(d["markets"], "x", hourly=False)
    assert daily[0]["slug"] == d["markets"][0]["slug"]
    assert daily[0]["quote_kind"] == "outcome_prices"


def test_polymarket_us_book_fixture_shape():
    b = json.loads((FX / "polymarket-us-book.json").read_text())["marketData"]
    assert {"marketSlug", "bids", "offers", "state"} <= set(b)


def test_platform_registry_is_consistent():
    reg = json.loads((ROOT / "data" / "platforms" / "platforms.json").read_text())
    slugs = [p["slug"] for p in reg["platforms"]]
    assert len(slugs) == len(set(slugs))
    for p in reg["platforms"]:
        if p["collector"]:
            assert (ROOT / "collectors" / f"{p['collector']}.py").exists(), p["slug"]
    orgs = json.loads((ROOT / "data" / "cftc" / "orgs.json").read_text())["orgs"]
    for code, o in orgs.items():
        if o["slug"]:
            assert o["slug"] in slugs, code
