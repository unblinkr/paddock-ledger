# REPORT, tasks/private-data

Run 2026-10-21 from the chat session. Draft PR, not merged.

## What changed

- `collectors/common.py`: new `RECORD = REPO / "record"`.
- `collectors/kalshi.py`, `gemini.py`, `polymarket_us.py`, `kalshi_combos.py`: listings, settlements and combos write under `record/<platform>/...`; run records say `store: "record"` and `file: record/...`. Books unchanged.
- `collectors/summaries.py`: reads Kalshi listings from `record/`. `data/summaries/` stays in git (aggregates).
- `collectors/store.py`: `store.py record` uploads `record/` to R2 with the same key layout as `books/`; `store.py --migrate-legacy` uploads the ten committed snapshots to their `record/` keys and writes a manifest. Deletes nothing.
- `collectors/health.py`: store warnings cover books and record.
- `.gitignore`: `record/`.
- Workflows: `listings-daily` commits `data/runs/ data/summaries/`; `settlements-daily` and `combos-daily` commit `data/runs/` only; all three upload `record/` to R2 or keep it as a 90-day artifact. New by-hand `migrate-record`.
- README, LICENSE, CLAUDE.md: wording per the brief; CC BY now covers only the CFTC ledger, registry, summaries and run records.
- Fixtures trimmed (QUESTIONS.md item 2). Three new tests.

## Checks

1. `python -m pytest -q`: 21 passed.
2. Real `python collectors/kalshi.py --mode daily` with no R2 keys: 156,147 markets written to `record/kalshi/listings/2026-10-21.jsonl.gz`; `git status` showed only a new run record under `data/runs/`.
3. Legacy files to migrate (bytes in git). R2 side pending the `migrate-record` run:

| bytes | file |
|---|---|
| 544806 | data/gemini/listings/2026-10-20.jsonl.gz |
| 564265 | data/gemini/listings/2026-10-21.jsonl.gz |
| 1622328 | data/gemini/settlements/2026-10-21.jsonl.gz |
| 209755 | data/kalshi/combos/2026-10-21.jsonl.gz |
| 8922351 | data/kalshi/listings/2026-10-20.jsonl.gz |
| 9003428 | data/kalshi/listings/2026-10-21.jsonl.gz |
| 11378560 | data/kalshi/settlements/2026-10-21.jsonl.gz |
| 4562484 | data/polymarket-us/listings/2026-10-20.jsonl.gz |
| 4608939 | data/polymarket-us/listings/2026-10-21.jsonl.gz |
| 2188443 | data/polymarket-us/settlements/2026-10-21.jsonl.gz |

4. Ordinary commits only, no force-push.
5. Grep for `DATA / SLUG` and `DATA / "kalshi"` paths in collectors: 0.
6. Em dashes in README, CLAUDE.md, LICENSE, collectors, workflows, tests: 0.
7. All workflows parse; `git add` lines: books-hourly `data/runs/`, combos-daily `data/runs/`, settlements-daily `data/runs/`, listings-daily `data/runs/ data/summaries/`, migrate-record `data/runs/`, cftc-daily `data/` (unchanged, see QUESTIONS.md item 4).

## After merge (founder)

1. Merge. From then on no workflow commits a snapshot.
2. Actions, `migrate-record`, Run workflow. Needs the four R2_* secrets.
3. Check the manifest in `data/runs/<day>/migrate-record.jsonl` matches the table above, then the follow-up commit removes the ten files from `main`.
