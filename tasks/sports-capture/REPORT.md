# REPORT: sports capture

Date 2026-10-21. Branch task/sports-capture.

## 1. pytest
```
..................                                                       [100%]
18 passed in 0.12s
```
## 2. Run records (data/runs/2026-10-21/)
```
{"collector": "polymarket-us:resolved", "counts": {"bytes_gz": 2188443, "end_date_max": "2026-10-21T14:18:14Z", "end_date_min": "2026-10-20T02:18:14Z", "ended_on_short_page": true, "file": "data/polymarket-us/settlements/2026-10-21.jsonl.gz", "markets_resolved": 39805, "page_size": 500, "pages": 80, "rows_outside_window": 0, "window_hours": 36}, "finished": "2026-10-21T14:19:39Z", "http": {"requests": 80, "retries": 0}, "source": "live", "started": "2026-10-21T14:18:14Z", "store": "git"}
{"collector": "gemini:settled", "counts": {"bytes_gz": 1622328, "categories_at_cap": ["Weather", "Crypto", "Commodities"], "categories_failed": {"Sports": "503 https://api.gemini.com/v1/prediction-markets/events?limit=500&offset=0&status=settled&category=Sports"}, "categories_rejected_by_api": [], "combos": 0, "contracts": 17998, "events": 3081, "file": "data/gemini/settlements/2026-10-21.jsonl.gz", "per_category": {"(all)": {"pages": 2, "returned": 1000, "total_reported": 1000, "truncated": true}, "Business": {"pages": 1, "returned": 6, "total_reported": 6, "truncated": false}, "Commodities": {"pages": 2, "returned": 1000, "total_reported": 1000, "truncated": true}, "Crypto": {"pages": 2, "returned": 1000, "total_reported": 1000, "truncated": true}, "Culture": {"pages": 1, "returned": 14, "total_reported": 14, "truncated": false}, "Economics": {"pages": 1, "returned": 23, "total_reported": 23, "truncated": false}, "Esports": {"pages": 1, "returned": 0, "total_reported": 0, "truncated": false}, "Finance": {"pages": 1, "returned": 0, "total_reported": 0, "truncated": false}, "Other": {"pages": 1, "returned": 18, "total_reported": 18, "truncated": false}, "Politics": {"pages": 1, "returned": 20, "total_reported": 20, "truncated": false}, "Weather": {"pages": 2, "returned": 1000, "total_reported": 1000, "truncated": true}}, "query_cap": 1000, "unknown_categories_seen": []}, "finished": "2026-10-21T14:22:57Z", "http": {"requests": 21, "retries": 5}, "source": "partial", "started": "2026-10-21T14:19:44Z", "store": "git"}
{"collector": "kalshi:settled", "counts": {"bytes_gz": 11378560, "ended_on_empty_cursor": true, "file": "data/kalshi/settlements/2026-10-21.jsonl.gz", "markets_combo_legs_skipped": 0, "markets_returned": 135585, "markets_settled": 135585, "min_close_ts": 1792464252, "mve_filter": "exclude", "page_size": 1000, "pages": 136, "short_pages": 1, "window_hours": 36}, "finished": "2026-10-21T15:00:43Z", "http": {"requests": 221, "retries": 85}, "source": "live", "started": "2026-10-21T14:44:12Z", "store": "git"}
{"collector": "kalshi-combos:daily", "counts": {"bytes_gz": 210814, "collections": 1406, "ended_on_empty_cursor": true, "file": "data/kalshi/combos/2026-10-21.jsonl.gz", "page_size": 1000, "pages": 2}, "finished": "2026-10-21T14:18:14Z", "http": {"requests": 2, "retries": 0}, "source": "live", "started": "2026-10-21T14:18:13Z", "store": "git"}
```
## 3. New files, row counts, first row (long text truncated for this report only)
```
data/gemini/settlements/2026-10-21.jsonl.gz 17998
{"at": "2026-10-21T14:19:44Z", "contract": {"abbreviatedName": ">$82,600", "color": "#4CAF50", "createdAt": "2026-10-20T23:55:38.680Z", "description": {"content": [{"data": {}, "marks": [], "nodeType": "text", "value": "If the price of Bitcoin (BTC) is $82,600 or above on October 20, 2026 ..."}], "data": {}, "nodeType": "document"}, "effectiveDate": "2026-10-21T01:00:00.000Z", "expiryDate": "2026-10-21T02:00:00.000Z", "id": "369114-865125", "instrumentSymbol": "GEMI-BTC2610210200-HI82600", "isCombo": false, "label": "$82,600 or above", "marketState": "closed", "priceIncrement": "0.01", "priceMinimum": "0.01", "prices": {"buy": {}, "sell": {}}, "quantityIncrement": "0.01", "quantityMinimum": "0.01", "quoteAssetPrecision": 2, "resolutionSide": "yes", "resolvedAt": "2026-10-21T02:00:06.382Z", "settlementValue": "82925.81416666666", "sortOrder": 0, "source": "LS-LRRR-XBTUSD", "status": "settled", "strike": {"type": "above", "value": "82600"}, "termsAndConditionsUrl": "https://assets.gemini.com/predictions/terms_and_conditions/btc_398860b...", "ticker": "HI82600"}, "contract_ticker": "HI82600", "event": {"category": "Crypto", "createdAt": "2026-10-20T23:55:38.680Z", "description": "Interval BTC price prediction event expiring on October 20, 2026 at 10...", "effectiveDate": "2026-10-20T23:55:38.680Z", "eventTags": [{"id": 13, "name": "Hourly", "slug": "hourly"}, {"id": 18, "name": "Reference", "slug": "reference"}], "expiryDate": "2026-10-21T02:00:00.000Z", "featuredImageUrl": "https://assets.gemini.com/predictions/images/Top_10_-_Bitcoin_1_23ea2d...", "id": "369114", "imageUrl":

data/kalshi/combos/2026-10-21.jsonl.gz 1406
{"associated_event_tickers": ["KXNFLGAME-26OCT22NECHI", "KXNFLSPREAD-26OCT22NECHI", "KXNFLTOTAL-26OCT22NECHI"], "associated_events": [{"active_quoters": [], "is_yes_only": false, "size_max": 1, "ticker": "KXNFLGAME-26OCT22NECHI"}, {"active_quoters": [], "is_yes_only": false, "size_max": 1, "ticker": "KXNFLSPREAD-26OCT22NECHI"}, {"active_quoters": [], "is_yes_only": false, "size_max": 1, "ticker": "KXNFLTOTAL-26OCT22NECHI"}], "at": "2026-10-21T14:18:13Z", "close_date": "2029-11-07T15:00:00Z", "collection_ticker": "KXMVESPORTSMULTIGAMEEXTENDED-R", "description": "Choose any combination of game stats and props.", "exchange_index": 1, "functional_description": "The resulting market will only resolve to YES if every associated mark...", "is_all_yes": false, "is_ordered": false, "is_single_market_per_event": false, "open_date": "2026-10-21T08:10:31Z", "price_level_structure": "center_deci_edge_centi_cent", "price_ranges": [{"end": "0.0100", "start": "0.0000", "step": "0.0001"}, {"end": "0.9900", "start": "0.0100", "step": "0.0010"}, {"end": "1.0000", "start": "0.9900", "step": "0.0001"}], "series_ticker": "KXMVESPORTSMULTIGAMEEXTENDED", "size_max": 0, "size_min": 2, "title": "What will happen across all games?"}

data/kalshi/settlements/2026-10-21.jsonl.gz 135585
{"at": "2026-10-21T14:44:12Z", "can_close_early": true, "close_time": "2026-10-21T14:41:56Z", "created_time": "2026-10-20T19:03:34.789165Z", "custom_strike": {"tennis_competitor": "576e6df5-67d1-4623-a6e1-a5b69a44ed03"}, "early_close_condition": "This market will close and expire after a winner is declared.", "event_ticker": "KXITFWMATCH-26OCT21GIRRUA", "expected_expiration_time": "2026-10-21T17:00:00Z", "expiration_time": "2026-11-04T11:00:00Z", "expiration_value": "Zi Ying Ruan", "last_price_dollars": "0.9900", "latest_expiration_time": "2026-11-04T11:00:00Z", "market_type": "binary", "no_sub_title": "Zi Ying Ruan", "occurrence_datetime": "2026-10-21T17:00:00Z", "open_interest_fp": "50016.03", "open_time": "2026-10-20T19:12:00Z", "result": "yes", "rules_primary": "If Zi Ying Ruan wins the Giraldi Requena vs Ruan professional tennis m...", "rules_secondary": "The following market refers to the Giraldi Requena vs Ruan professiona...", "rules_sha256": "4bff7242b367bdaffd753c14a8978363ff99f17663734332d2965022f149d2b5", "settlement_bounds_type": "default", "settlement_timer_seconds": 60, "settlement_ts": "2026-10-21T14:43:57.578805Z", "settlement_value_dollars": "1.0000", "status": "finalized", "strike_type": "structured", "ticker": "KXITFWMATCH-26OCT21GIRRUA-RUA", "title": "Zi Ying Ruan wins", "updated_time": "2026-10-21T14:43:57.650182Z", "volume_fp": "82015.30", "yes_sub_title": "Zi Ying Ruan"}

data/polymarket-us/settlements/2026-10-21.jsonl.gz 39805
{"active": true, "archived": false, "at": "2026-10-21T14:18:14Z", "category": "sports", "closed": true, "comboEnabled": false, "createdAt": "2026-03-19T14:41:53Z", "description": "Will Cleveland Guardians win the 2026 MLB World Series, scheduled for ...", "endDate": "2026-10-20T03:13:37Z", "ep3Status": "EXPIRED", "ep3SyncedAt": "2026-10-20T03:13:37Z", "feeCoefficient": 0.0695, "gameStartTime": "2026-09-07T00:00:00Z", "hidden": false, "id": "7927", "marketType": "futures", "minimumTradeQty": 1, "orderPriceMinTickSize": 0.001, "outcomePrices": "[\"0\",\"1\"]", "outcomes": "[\"No\",\"Yes\"]", "question": "World Series Champion", "sides": [{"description": "Yes", "id": "15853", "identifier": "tec-mlb-champ-2026-09-27-cle", "long": true, "price": "0"}, {"description": "No", "id": "15854", "identifier": "tec-mlb-champ-2026-09-27-cle", "long": false, "price": "1"}], "slug": "tec-mlb-champ-2026-09-27-cle", "sportsMarketType": "futures", "sportsMarketTypeV2": "SPORTS_MARKET_TYPE_FUTURE", "startDate": "2026-03-19T14:32:24Z", "status": "MARKET_STATUS_RESOLVED", "tags": [], "updatedAt": "2026-10-21T03:12:31Z"}

```
Price fields: Kalshi settled `last_price_dollars`, `volume_fp`, `open_interest_fp`, `settlement_value_dollars` are strings on all 135,585 rows (checked on 5,000, tests pin it on the fixture). Combo `price_ranges` start/end/step are strings. Gemini prices/`settlementValue` are as served (strings). Polymarket `sides[].price` strings; `orderPriceMinTickSize` is a JSON number as the gateway serves it and is kept as served.

## 4. rules_sha256 match
`KXNBARETIRE-SCURRY30-2627` is in today's 05:40 listings file and the settlements file (5,339 tickers are). The 05:40 listing was written before this change and is not rewritten (rule 4), so it has no hash. The match was shown with the branch code instead: settlements file `0eb1119b55c96109a930e20a3a536c1fd6a17a93a1c6876ba737ac98ba38d6d2`, daily-mode row `0eb1119b...d6d2`, book-mode row `0eb1119b...d6d2` (same market, live record), and rules_primary equals the 05:40 listing's. Tomorrow's real listings file will carry the hash directly. Tests also pin hash = sha256(primary + "\n" + secondary).

## 5. float(
`grep -rn "float(" collectors/` on branch and on main: only `collectors/summaries.py:35` (existing). Nothing new.

## 6. Em dash
`grep -rn $'\xe2\x80\x94' README.md CLAUDE.md collectors/` (also tasks/, tests/, workflows): no output.

## 7. Hourly key diff, main vs branch (full live walk, 153,967 vs 153,979 rows, 153,936 shared tickers)
```
keys only in main:   []
keys only in branch: ['occurrence_datetime', 'rules_sha256']
type changes on shared keys: 0
```

## 8. Workflows
`yaml.safe_load` on settlements-daily.yml and combos-daily.yml: ok.

## 9. Parameters asserted (also in the docstrings)
| Where | Parameter | Server did |
|---|---|---|
| Kalshi /markets | limit | max 1000; 1001 returns 400; 200 and 500 fine |
| Kalshi /markets | status=settled&min_close_ts | honoured; rows status "finalized" |
| Kalshi /events | status=settled&min_close_ts | NOT honoured (closes 2026-08-01 to 2031-01-01) |
| Kalshi /markets | mve_filter | exclude: 0 combos; only: all combos; unknown value ignored |
| Kalshi /markets | occurrence_datetime | non-null on all 135,585 settled rows; equals expected_expiration_time on 131,265; not verified as kickoff |
| Kalshi collections | limit | no max found to 5000 (1,406 rows, no cursor) |
| Kalshi collections | status | `open` honoured (3 rows); unknown values ignored |
| Gemini | status=settled, date filters, sort params | settled honoured, cap 1000; all date/sort/series params ignored; Sports 503 |
| Polymarket US | closed=true + endDateMin/endDateMax | honoured; updatedAt/since/order variants ignored; no resolution key, status MARKET_STATUS_RESOLVED and ep3Status EXPIRED |

Docstring lines added: see `git diff main -- collectors/` (kalshi.py, kalshi_combos.py, gemini.py, polymarket_us.py module docstrings).

## Files changed
collectors/kalshi.py, kalshi_combos.py (new), gemini.py, polymarket_us.py, health.py; tests/test_collectors.py; .github/workflows/settlements-daily.yml, combos-daily.yml (new); README.md, CLAUDE.md; tasks/sports-capture/{TASK,QUESTIONS,REPORT}.md; first-run data under data/kalshi/settlements, data/kalshi/combos, data/gemini/settlements, data/polymarket-us/settlements, data/runs/2026-10-21.

## Fixtures
tests/fixtures/kalshi-settled-page1.json (real unfiltered first page, limit=200: all combo legs), kalshi-settled-singles.json (real page with mve_filter=exclude, limit=100), kalshi-combos.json (first page, limit=5), gemini-settled-weather.json (Weather, first page, limit=3), polymarket-us-resolved.json (first page, limit=5). Nothing removed. Note: the first page of the walk is entirely combo legs, hence two Kalshi fixtures.

## Other notes
- Daily settled Kalshi walk took 16.5 minutes (136 pages, 85 retries on 429); workflow timeout is 90 minutes.
- Gemini `Weather`, `Crypto`, `Commodities` flagged truncated; Sports failed (issue #8).
- Issues opened: #8, #9, #10. QUESTIONS.md lists the decisions needed.
