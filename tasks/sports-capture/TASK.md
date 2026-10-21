# TASK: Capture settlements, rules hashes and combo collections so the record can answer sports questions

Repository: `unblinkr/paddock-ledger`. Branch: `task/sports-capture`. PR mode: `merge on green`.
Run with: CLAUDE.md in this repo: branch per change, tests green, merge locally, push `main`. Write `QUESTIONS.md` and `REPORT.md` next to this file.
Date issued: 2026-10-21. todoist_task: none. closes: none. mockup: none.

Nothing here changes a public page or a published figure. It adds capture. After `git fetch`, confirm local `main` equals `origin/main`, merge locally, push `main`, and confirm the new workflows appear in the Actions tab.

## 1. Goal
After this task the record holds, for every Kalshi market, how it settled and when, a hash of its rules text so any edit is visible, the game time where the platform publishes one, and a daily ledger of Kalshi combo collections with their price structure as served. Gemini settlements are captured the same way. Nothing already captured changes or shrinks.

## 2. Context
This repository is the record behind paddock.finance/venues. The record is the asset. Today the Kalshi collector walks `status=open` only, so a market leaves the record the day it closes and its outcome is never written down. `rules_primary` is captured but `rules_secondary` is not, and there is no hash. Kalshi combo (multivariate) markets are skipped and counted, which is right for the single-leg record, but the collections themselves are not captured at all. Gemini and Polymarket US settlements are not captured either.

Sports is more than 80 percent of volume on every US venue. The three things buyers in sports ask that nothing public records: how did each venue settle the same event, did the rules change after listing, and what did the combos look like. The founder decided on 2026-10-21 to add these to capture now, before any product is built on them. No product, page or analysis is in scope.

Field names marked VERIFIED in the brief were read from live responses on 2026-10-21. Everything else is asserted against a saved response before it is relied on (CLAUDE.md rule 3). If something cannot be built as written, write it to `QUESTIONS.md` and stop that change; ship the others.

## 3. Decisions already made (do not re-ask)
* Settlements are a new append-only file family per platform, `data/<platform>/settlements/YYYY-MM-DD.jsonl.gz`, committed to git like listings. Not merged into listings files.
* Each daily settlements walk covers the last 36 hours, not 24. A row seen twice is a reader's dedupe problem, never a writer's.
* `rules_sha256` is sha256 over the UTF-8 bytes of `rules_primary`, a single `\n`, then `rules_secondary` (empty string when null). Written on listings rows, book rows and settlement rows.
* Combo collections are captured as served. No hold, margin or implied probability. `price_ranges` and `price_level_structure` stored exactly as returned.
* The Kalshi combo ledger lives at `data/kalshi/combos/YYYY-MM-DD.jsonl.gz`. Single-leg listings and books stay as they are.
* Sport and topic labels stay out of ledger rows. No `topic` field.
* Polymarket US resolution capture is Change E. If no bounded walk of resolved markets exists, write that to `QUESTIONS.md` with requests and responses, and ship A to D without it.
* Workflows: 07:10 UTC settlements, 07:40 UTC combos.

## 4. Hard rules
* CLAUDE.md rules 1 to 9 in full. Every run writes a run record with a `source` marker; name every cap and assert the response; append only; prices stay strings; no float arithmetic; no secrets in output; one request a second with backoff; nothing identifies a person.
* No em dashes in README, CLAUDE.md, docstrings, commit messages or issue titles.
* A new file family gets a docstring naming what was verified and when, a saved fixture from a real response, a test, and a row in the README table.
* Existing fixtures and tests keep passing unchanged. Adding fields to `MARKET_FIELDS` or `BOOK_FIELDS` must not change the shape of any field already written.

## 5. Banned terms
none

## 6. Build scope
**Change A: Kalshi settlements walk.** `collectors/kalshi.py --mode settled`. `GET /trade-api/v2/markets?limit=<page>&status=settled&min_close_ts=<now minus 36h>`, cursor paginated. VERIFIED: `/markets` honours `min_close_ts` with `status=settled`. Assert the maximum `limit` and whether `/events?status=settled&with_nested_markets=true` honours `min_close_ts`; record in the docstring. If `/events` honours it, prefer it; if not, walk `/markets` and skip rows with `mve_collection_ticker`, counting `markets_combo_legs_skipped`. Fields: ticker, event_ticker, market_type, status, title, yes_sub_title, no_sub_title, result, settlement_value_dollars, settlement_ts, expiration_value, settlement_bounds_type, settlement_timer_seconds, open_time, close_time, expiration_time, latest_expiration_time, expected_expiration_time, created_time, early_close_condition, can_close_early, occurrence_datetime, custom_strike, strike_type, rules_primary, rules_secondary, last_price_dollars, volume_fp, open_interest_fp, updated_time; plus `rules_sha256`, `at`. Docstring: `settled_time` is absent on a settled market, the stamp is `settlement_ts`; assert whether `occurrence_datetime` carries the game start on sports markets. Output `data/kalshi/settlements/YYYY-MM-DD.jsonl.gz`, store `git`. Run record `kalshi:settled` with counts `markets_settled`, `markets_combo_legs_skipped`, `window_hours: 36`, `min_close_ts`, pages, page size, `ended_on_empty_cursor`, bytes, file.

**Change B: rules hash, rules_secondary and game time on existing Kalshi rows.** Append to `MARKET_FIELDS`: rules_secondary, early_close_condition, occurrence_datetime, created_time, custom_strike, settlement_bounds_type, latest_expiration_time. Append to `BOOK_FIELDS`: occurrence_datetime. In `compact()`, set `row["rules_sha256"]` on daily, settlement and book rows.

**Change C: Kalshi combo collections ledger.** New `collectors/kalshi_combos.py`. `GET /trade-api/v2/multivariate_event_collections?limit=<page>`, cursor paginated; response `{"cursor", "multivariate_contracts"}`. Assert and record the maximum `limit`, whether a `status` filter exists, and the total count. Fields: collection_ticker, series_ticker, title, description, functional_description, associated_event_tickers, associated_events, is_all_yes, is_ordered, is_single_market_per_event, size_min, size_max, price_level_structure, price_ranges, open_date, close_date, exchange_index; plus `at`. Output `data/kalshi/combos/YYYY-MM-DD.jsonl.gz`. Run record `kalshi-combos:daily` with `collections`, pages, page size, `ended_on_empty_cursor`, bytes, file.
CLAUDE.md rule 6 becomes, exactly: `**Combos are counted, never mixed in.** Kalshi multivariate markets are skipped from the single-leg record and counted; the collections themselves are captured daily in data/kalshi/combos/. Gemini combos are flagged; Polymarket US comboEnabled is kept as a field.`
README "How to read it", the Kalshi combo sentence becomes, exactly: `Kalshi multivariate (combo) markets are not in the Kalshi single-leg record; each run counts how many it skipped. The collections themselves (which events a combo spans, its size limits and the price structure the exchange publishes) are in data/kalshi/combos/, one file a day. Gemini combos are kept with is_combo: true. Polymarket US rows carry quote_kind: "outcome_prices" because the gateway publishes a price per side, not a quote from the book.`

**Change D: Gemini settlements walk.** `collectors/gemini.py --mode settled`. Existing per-category walk with `status=settled`. Truncation at the 1,000 cap is `truncated: true` in the run record. Keep existing `EVENT_FIELDS` and `CONTRACT_FIELDS` plus every contract key that carries the outcome; list every key not already in `CONTRACT_FIELDS` in the docstring. Output `data/gemini/settlements/YYYY-MM-DD.jsonl.gz`. Run record `gemini:settled`.

**Change E: Polymarket US resolutions walk (verify first).** `collectors/polymarket_us.py --mode resolved`. Try `closed=true` with each of `updatedAt`, `endDate`, or a `since` parameter as a filter, one request each, one second apart, and record which the gateway honours by asserting the response. If one is honoured, walk the last 36 hours, keep `DAILY_FIELDS` plus every key naming a resolution, write `data/polymarket-us/settlements/YYYY-MM-DD.jsonl.gz`, run record `polymarket-us:resolved`. If none, write requests and responses to `QUESTIONS.md`, do not add the mode.

**Change F: workflows, health and README.** `.github/workflows/settlements-daily.yml` at `10 7 * * *` UTC running the settled modes; `.github/workflows/combos-daily.yml` at `40 7 * * *` UTC running `kalshi_combos.py`; both commit to `main` with the `[bot]` identity as `listings-daily.yml` does. `collectors/health.py` checks the new jobs like the existing daily jobs. README "What is in the record" gets two rows (settlements; combo collections) and "Running it" gets the new commands.

**Change G: fixtures and tests.** One real response each for: Kalshi settled markets, Kalshi multivariate collections, Gemini settled events (one category), Polymarket US resolved markets (if shipped). Tests in `tests/test_collectors.py`: every field present, `rules_sha256` 64 lowercase hex and equal to the hash computed in the test, combo legs skipped and counted on the `/markets` path, `price_ranges` round-trips unchanged, no float where the API served a string.

## 7. Out of scope
Any computation on prices; any change to paddock.finance or openclaw-news; new platform collectors; fetching Gemini `termsAndConditionsUrl` or Polymarket US books; backfilling settlements before 2026-10-21; rewriting any existing file.

## 8. Verification checks (paste results into REPORT.md)
1. `python -m pytest -q` green.
2. One real run of each new mode; paste each run record line.
3. `gunzip -c` each new file, count rows, print the first row. Every price field is a JSON string.
4. One Kalshi row present in both the listings and settlements files: the `rules_sha256` matches.
5. `grep -rn "float(" collectors/` returns nothing new compared to `main`.
6. Searching README.md, CLAUDE.md and collectors/ for the em dash character (U+2014, e.g. `grep -rn $'\xe2\x80\x94'`) returns nothing.
7. `python collectors/kalshi.py --mode hourly` into a temp dir on `main` and on the branch; the branch's rows are a superset of main's keys (only new keys: `occurrence_datetime`, `rules_sha256`).
8. Both new workflow files validate with `yaml.safe_load`.
9. Every cap or parameter asserted is named in the relevant docstring with the date.

## 9. Handback
Write `tasks/sports-capture/REPORT.md` with the result of every check, files changed, every parameter asserted and what the server did, fixture file names, and anything written to `QUESTIONS.md`. Under `merge on green`: merge locally, push `main`, paste the Actions URL of the first run of each new workflow. End the session with:

```
BOARD SYNC
todoist_task: none
closes: none
new issues opened: <#n title> | none
needs_mancy: <one line> | none
live: main at <sha> | draft PR <#n>
```
