# Paddock Ledger

A record of every US prediction-market platform: what each one lists, files, prices and settles, captured from public sources on a fixed schedule and kept without gaps.

Maintained by [Paddock](https://paddock.finance/venues). Started October 2026.

## What is in the record

| Part | Source | Cadence | Where |
|---|---|---|---|
| Listings ledger: every product a designated contract market filed with the CFTC (new products, Rule 40.2 and 40.3) and every product rule change | cftc.gov, Industry Filings | daily, 06:30 UTC | `data/cftc/products.jsonl`, `data/cftc/product-rules.jsonl`, `data/cftc/details/<id>.json` |
| Listings snapshot: every open market on each platform with full metadata | each platform's public API | daily, 05:40 UTC | Cloudflare R2 `record/<platform>/listings/YYYY-MM-DD.jsonl.gz` (access on request) |
| Books: top-of-book (or the platform's published price, where no book is exposed) for every open market | each platform's public API | hourly | Cloudflare R2 `books/<platform>/YYYY-MM-DD/HH.jsonl.gz` (access on request) |
| Settlements: every market that closed in the last 36 hours with its outcome, settlement value, settlement stamp and rules hash | each platform's public API | daily, 07:10 UTC | Cloudflare R2 `record/<platform>/settlements/YYYY-MM-DD.jsonl.gz` (access on request) |
| Combo collections: every Kalshi multivariate collection with the events it spans, its size limits and the price structure as published | Kalshi public API | daily, 07:40 UTC | Cloudflare R2 `record/kalshi/combos/YYYY-MM-DD.jsonl.gz` (access on request) |
| Run records: one line per collector run with counts, caps hit, and a `source` marker | this repository | every run | `data/runs/YYYY-MM-DD/<job>.jsonl` |
| Summaries: small daily aggregates the site reads (filings by exchange, Kalshi volume by topic) | built from the record, no fetches | daily, with listings | `data/summaries/` |

The public repository holds the method, the tests, the run records and the CFTC filings ledger. The platform record (listings, books, settlements and combo collections) is kept on R2 and is available under licence; write to the address on paddock.finance/venues.

Platforms with a collector today: Kalshi, Polymarket US, Gemini Predictions. The full list, with the ones not yet captured and why, is `data/platforms/platforms.json`. The CFTC ledger covers every designated contract market whether or not it has a collector.

## How to read it

- A row is never rewritten. A filing whose status changes (Approval Pending to Certified) is a second line with a later `seen`; take the latest line per `id`.
- Every price is the string the platform served. Nothing here is rounded, averaged or converted.
- Kalshi multivariate (combo) markets are not in the Kalshi single-leg record; each run counts how many it skipped. The collections themselves (which events a combo spans, its size limits and the price structure the exchange publishes) are in the record under record/kalshi/combos/, one file a day. Gemini combos are kept with is_combo: true. Polymarket US rows carry quote_kind: "outcome_prices" because the gateway publishes a price per side, not a quote from the book.
- Every pagination limit is named in the collector and the run record says whether it was hit. `source` is `live` when the walk finished, `partial` when a cap or a server-shortened walk left something out, `unavailable` when the fetch failed and nothing was written.
- Platform collectors say what they do and do not capture in their module docstrings (`collectors/*.py`). The constraints found on 2026-10-20 are recorded there: Kalshi rate-limits bursts; Gemini caps every query at 1,000 events and ignores `page`; Polymarket US caps `limit` at 500 and ignores `page`.

## Citing it

Cite as: Paddock Ledger, `<file path>`, pulled `<the row's at or seen stamp>`, github.com/unblinkr/paddock-ledger at commit `<sha>`. The commit is the version.

## Running it

Python 3.12, standard library only (boto3 for the R2 upload, installed by the workflow when the keys exist).

```
python collectors/cftc.py                 # new filings since the last run
python collectors/cftc.py --all --no-details   # backfill the lists
python collectors/kalshi.py --mode hourly  # one hour of books into books/
python collectors/kalshi.py --mode daily   # the day's listings into record/
python collectors/gemini.py --mode daily
python collectors/kalshi.py --mode settled   # last 36 hours of settlements
python collectors/gemini.py --mode settled
python collectors/polymarket_us.py --mode resolved
python collectors/kalshi_combos.py           # combo collections into record/
python collectors/store.py record            # upload record/ to R2 (needs the R2_* variables)
python -m pytest -q
```

Workflows: `cftc-daily`, `listings-daily`, `settlements-daily`, `combos-daily`, `books-hourly`, `health-daily` (opens an issue on a missed hour), `tests`, and `migrate-record` (by hand, once: copies the snapshots committed before 2026-10-21 to R2).

Local runs without the R2 variables still work: the collectors write under `books/` and `record/` (both gitignored) and `store.py` says it is not configured.

## Licence

Code: MIT. The CFTC filings ledger, the platform registry, the summaries and the run records in this repository: Creative Commons Attribution 4.0 (CC BY 4.0); attribute Paddock Ledger and the commit. The platform record on R2 is not covered by that licence and is available under licence from Paddock.
