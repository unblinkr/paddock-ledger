"""Parser tests on responses saved from the live sources on 2026-10-20.

Each fixture is a real response. The tests pin what the collectors rely on,
so an upstream shape change fails here before it quietly empties a day.
"""

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

import cftc  # noqa: E402
import gemini  # noqa: E402
import kalshi  # noqa: E402
import kalshi_combos  # noqa: E402
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


# ---- Settlements, rules hashes and combo collections (fixtures saved 2026-10-21) ----

def _sha(primary, secondary):
    return hashlib.sha256(((primary or "") + "\n" + (secondary or "")).encode("utf-8")).hexdigest()


def _no_float_where_string(row, served):
    """No value in `row` is a float where the API served a string for that key."""
    for k, v in row.items():
        if k in served and isinstance(served[k], str):
            assert isinstance(v, str), k
        assert not isinstance(v, float) or not isinstance(served.get(k), str), k


def test_kalshi_settled_walk_skips_and_counts_combo_legs():
    markets = json.loads((FX / "kalshi-settled-page1.json").read_text())["markets"]
    rows, skipped = kalshi.compact_settled(markets, "x")
    combos = sum(1 for m in markets if m.get("mve_collection_ticker"))
    assert skipped == combos and len(rows) == len(markets) - combos
    assert combos > 0
    assert all(not r.get("mve_collection_ticker") for r in rows)


def test_kalshi_settled_rows_carry_every_field_and_a_matching_hash():
    markets = json.loads((FX / "kalshi-settled-singles.json").read_text())["markets"]
    assert markets and not any(m.get("mve_collection_ticker") for m in markets)
    rows, skipped = kalshi.compact_settled(markets, "2026-10-21T07:10:00Z")
    assert skipped == 0 and len(rows) == len(markets)
    for r, m in zip(rows, markets):
        for k in kalshi.SETTLED_FIELDS:
            assert k in r, k  # null is fine, missing is a failure
        assert re.fullmatch(r"[0-9a-f]{64}", r["rules_sha256"])
        assert r["rules_sha256"] == _sha(m["rules_primary"], m.get("rules_secondary"))
        assert r["at"] == "2026-10-21T07:10:00Z"
        assert r["status"] == "finalized"
        for k in ("last_price_dollars", "volume_fp", "open_interest_fp", "settlement_value_dollars"):
            assert isinstance(r[k], str), k
        _no_float_where_string(r, m)


def test_kalshi_rules_hash_is_on_daily_and_book_rows_and_matches_settled():
    d = json.loads((FX / "kalshi-events.json").read_text())["events"]
    daily = kalshi.compact(d, kalshi.MARKET_FIELDS, "x")
    book = kalshi.compact(d, kalshi.BOOK_FIELDS, "x")
    assert len(daily) == len(book)
    for r in daily + book:
        assert re.fullmatch(r"[0-9a-f]{64}", r["rules_sha256"])
    m = d[0]["markets"][0]
    assert daily[0]["rules_sha256"] == book[0]["rules_sha256"] == _sha(m["rules_primary"], m.get("rules_secondary"))


def test_kalshi_new_fields_are_appended_and_old_order_is_untouched():
    old = ["ticker", "event_ticker", "market_type", "status", "title", "yes_sub_title", "no_sub_title"]
    assert kalshi.MARKET_FIELDS[:len(old)] == old
    assert kalshi.MARKET_FIELDS[-7:] == ["rules_secondary", "early_close_condition", "occurrence_datetime", "created_time",
                                         "custom_strike", "settlement_bounds_type", "latest_expiration_time"]
    assert kalshi.BOOK_FIELDS[-1] == "occurrence_datetime"
    assert kalshi.BOOK_FIELDS[-2] == "close_time"


def test_kalshi_combo_collections_round_trip_price_structure_as_served():
    items = json.loads((FX / "kalshi-combos.json").read_text())["multivariate_contracts"]
    rows = kalshi_combos.compact(items, "2026-10-21T07:40:00Z")
    assert len(rows) == len(items) and rows
    for r, c in zip(rows, items):
        for k in kalshi_combos.COLLECTION_FIELDS:
            assert k in r, k
        assert r["price_ranges"] == c["price_ranges"]
        assert r["price_level_structure"] == c["price_level_structure"]
        assert r["at"] == "2026-10-21T07:40:00Z"
    assert any(isinstance(r["price_ranges"], list) and r["price_ranges"] for r in rows)
    for rng in rows[0]["price_ranges"]:
        assert all(isinstance(rng[k], str) for k in ("start", "end", "step"))
    assert not any(isinstance(v, float) for r in rows for v in r.values())


def test_gemini_settled_rows_keep_every_key_and_the_outcome():
    events = json.loads((FX / "gemini-settled-weather.json").read_text())["data"]
    rows = gemini.compact_settled(events, "x")
    assert len(rows) == sum(len(e["contracts"]) for e in events)
    for r, c in zip(rows, [c for e in events for c in e["contracts"]]):
        assert r["contract"] == c  # nothing dropped, nothing derived
        assert r["resolution_side"] == c["resolutionSide"] in ("yes", "no")
        assert r["resolved_at"] == c["resolvedAt"]
        for k in gemini.CONTRACT_FIELDS:
            assert k in r["contract"] or k == "strike", k
    ev = rows[0]["event"]
    assert "contracts" not in ev and "resolvedAt" in ev and "settlement" in ev
    for k in ("id", "ticker", "title", "category", "status", "resolvedAt", "settlement"):
        assert k in ev, k  # every key the API served is kept, so only keys it served are asserted
    assert gemini.CAP == 1000


def test_polymarket_us_resolved_rows_keep_status_and_final_side_prices():
    markets = json.loads((FX / "polymarket-us-resolved.json").read_text())["markets"]
    rows = polymarket_us.compact_resolved(markets, "x")
    assert len(rows) == len(markets) and rows
    for r, m in zip(rows, markets):
        for k in polymarket_us.RESOLVED_FIELDS:
            assert k in r, k
        assert r["status"] == "MARKET_STATUS_RESOLVED"
        assert r["sides"] and all(isinstance(s["price"], str) for s in r["sides"])
        assert r["outcomePrices"] == m["outcomePrices"]
