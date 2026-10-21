# CLAUDE.md, Paddock Ledger

Repo root file. Read before changing anything.

## What this repository is

The record behind paddock.finance/venues: every US prediction-market platform, what it lists, files, prices and settles, captured on a schedule and kept without gaps. The record is the asset. The code exists to keep it.

Sister repository: `unblinkr/openclaw-news` (paddock.finance, the site). Its CLAUDE.md's rules on secrets, merge policy and communications apply here unchanged.

## Rules that are not negotiable

1. **Never reduce what is captured to solve a storage or runtime problem.** A measurement not taken cannot be taken later. Move it (git to R2), compact it (gzip), split it, never drop it.
2. **Silent failure is a defect.** Every run writes a line to `data/runs/` with a `source` marker (`live` | `partial` | `unavailable`) and its counts. A collector that fails still records that it ran. `collectors/health.py` reads those lines; nothing else does the noticing.
3. **Name every cap and assert the response, not the request.** A server that ignores a parameter does not complain, it uses its default. `page` is ignored by both Gemini and Polymarket US; `limit` is silently reduced by Polymarket US; Gemini caps every query at 1,000. Each collector's docstring records what was verified and when. Re-verify before relying on a parameter that is not listed there.
4. **Append only. Never rewrite history.** Ledger rows are never edited or deleted; a changed status is a new row. Daily and hourly files are new files. If a bug produced bad rows, add a correction file and a note; do not rewrite.
5. **Prices stay strings.** No float arithmetic in a collector. Analysis happens elsewhere.
6. **Combos are counted, never mixed in.** Kalshi multivariate markets are skipped from the single-leg record and counted; the collections themselves are captured daily in data/kalshi/combos/. Gemini combos are flagged; Polymarket US comboEnabled is kept as a field.
7. **No secrets in output.** R2 keys live only in repository secrets, referenced by name in `env:`. Nothing prints an environment variable.
8. **Pace requests.** One a second with backoff is the default. A 429 is a signal to slow down, never to retry faster.
9. **Public repository, private record.** The code, tests, run records, summaries and CFTC ledger are public. Platform snapshots, books, settlements and combos go to R2 under `record/` and `books/` and are never committed. Nothing here may identify a person.

## Layout

```
collectors/      one module per source; common.py is the shared plumbing
data/cftc/       the listings ledger (append-only JSONL) and filing details
data/platforms/  the platform registry
data/summaries/  small daily aggregates the site reads, built from the record
data/runs/       one line per collector run
data/novig/etags.json   which Novig files are captured (kind, date, ETag, bytes); no data
record/<platform>/listings/      daily snapshots, written by the collectors, uploaded to R2, gitignored
record/<platform>/settlements/   daily settlements, 36 hour window, same
record/kalshi/combos/            daily combo collections, same
record/novig/<trades|markets>/   Novig's daily files as served, gzipped, same
books/           hourly books, written by the collectors, uploaded to R2, gitignored
tasks/           Code task briefs with their QUESTIONS.md and REPORT.md
tests/           parser tests on real saved responses
.github/workflows/  the schedules
```

## Working conventions

- Branch per change, tests green, then merge locally and push `main`. Scheduled workflows commit to `main` directly with `[bot]` identity; pull with rebase before pushing.
- A new source gets: a module with a docstring that names its caps and what was verified; a saved fixture; a test; a row in `data/platforms/platforms.json`; a line in the README table.
- A found gap gets a GitHub issue, never only a note in chat.
- Public copy anywhere (README, issue titles, commit messages) uses no em dashes.
