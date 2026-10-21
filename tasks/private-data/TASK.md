# TASK: Move the record out of the public repository; the code stays public, the data goes private

**Repository:** `unblinkr/paddock-ledger`
**Save this file to:** `tasks/private-data/TASK.md`
**Branch:** `task/private-data`
**Run with:** CLAUDE.md in this repo: branch per change, tests green, merge locally, push `main`. Write `QUESTIONS.md` and `REPORT.md` next to this file.
**Start this task in a fresh Claude Code session.** Do not continue the sports-capture session; this brief is self-contained.
**Run order:** after `tasks/sports-capture` has merged. If it has not, stop and say so in `QUESTIONS.md`.
**Executor model:** inherit
**Date issued:** 2026-10-21
**todoist_task:** none
**closes:** none
**mockup:** none
**PR mode:** `draft PR, stop` : this changes the data licence and removes files from the public record. Open a draft PR and stop. Do not force-push `main`. Do not rewrite history.

---

## 1. Goal

After this task, the public repository holds the code, the tests, the run records and the CFTC filings ledger, and nothing else. Every platform snapshot (listings, settlements, combos) is written to R2 next to the hourly books, is gitignored, and is served on request. The data licence on anything still public is unchanged (CC BY 4.0); the data on R2 carries no public licence.

## 2. Context (self-contained; this session has no other history)

This repository is the record behind paddock.finance/venues. It was created public on 2026-10-15 so the method could be cited and the record could be seen to exist. On 2026-10-21 the founder decided that the data itself, which is the product, must not be free in a public repository. The code and the method stay public because a desk or a journalist checking the work needs to see how a row was captured, and because "github.com/unblinkr/paddock-ledger at commit <sha>" is the citation format. The rows are what customers pay for and go private.

Today `data/<platform>/listings/` (daily, since 2026-10-20) and, after the sports-capture task, `data/<platform>/settlements/` and `data/kalshi/combos/` are committed to `main` by the scheduled workflows. `books/` already goes to Cloudflare R2 through `collectors/store.py` and is gitignored. The CFTC ledger (`data/cftc/`) is derived from public government filings, is the citation magnet, and stays in git.

Files already pushed to `main` have been public since they were pushed. Two days of Kalshi, Gemini and Polymarket US listings. The founder accepts that; nothing is rewritten.

All wording below is founder-approved. If something here cannot be built as written, write it to `QUESTIONS.md` and stop that change; ship the others.

## 3. Decisions already made (do not re-ask)

- The repository stays public. Making it private is a one-click setting the founder can flip later; it is not this task.
- What stays in git: `collectors/`, `tests/`, `.github/`, `data/cftc/`, `data/platforms/`, `data/runs/`, `tasks/`, README, CLAUDE.md, LICENSE.
- What leaves git: `data/<platform>/listings/`, `data/<platform>/settlements/`, `data/kalshi/combos/`. New path on R2: `record/<platform>/listings/YYYY-MM-DD.jsonl.gz`, `record/<platform>/settlements/YYYY-MM-DD.jsonl.gz`, `record/kalshi/combos/YYYY-MM-DD.jsonl.gz`, in the same bucket as `books/`.
- Already-committed files under those three paths are removed from `main` with an ordinary commit (`git rm`), never a history rewrite. They remain in history. The founder accepts this.
- Run records stay in git and keep their counts. A run record is proof a run happened; it holds no prices.
- `data/platforms/platforms.json` stays in git. It is a registry, not a record.
- Licence: the LICENSE file keeps MIT for code and CC BY 4.0 for the data that remains in the repository (the CFTC ledger, the registry, run records). Data on R2 is "available under licence from Paddock; contact paddock.finance/venues". Nothing on R2 is CC BY.
- The README "access on request" line that today covers only books now covers the whole record.
- Local runs without R2 keys still work: the collectors write to a local `record/` directory (gitignored) exactly as they write `books/` today, and `store.py` uploads when keys exist.

## 4. Hard rules (violating any fails the task)

- CLAUDE.md rules 1 to 9. Rule 1 in particular: this task moves data; it must not lose a single row. Every file removed from git is confirmed present on R2 first (section 8, check 3).
- No history rewrite, no force-push, no `filter-repo`, no `BFG`.
- No em dashes in README, CLAUDE.md, docstrings or commit messages.
- No secrets in output. R2 keys live only in repository secrets.

## 5. Banned terms

none

## 6. Build scope

### Change A: collectors write the record locally, not into `data/`

`collectors/common.py`: add `RECORD = REPO / "record"` beside the existing `DATA`. `collectors/kalshi.py`, `collectors/gemini.py`, `collectors/polymarket_us.py`, `collectors/kalshi_combos.py`: every path that today starts `DATA / SLUG / "listings"`, `DATA / SLUG / "settlements"` or `DATA / SLUG / "combos"` now starts `RECORD / SLUG / ...`. The run record's `file` field reports the R2 key (`record/...`) and `store` is `record`. The CFTC collector is untouched.

`.gitignore`: add `record/` beside `books/`.

### Change B: upload

`collectors/store.py`: `upload_dir` already uploads `books/`. Add `record/` to the same upload, same bucket, same key layout (`record/<platform>/<kind>/<file>`). The upload runs at the end of every workflow that produces record files (`listings-daily`, `settlements-daily`, `combos-daily`), exactly as `books-hourly` runs it today. If R2 keys are absent the upload step logs "R2 not configured, record kept locally" and the workflow still succeeds, as `books-hourly` does.

### Change C: the workflows stop committing record files

`listings-daily.yml`, `settlements-daily.yml`, `combos-daily.yml`: the commit step adds only `data/runs/` (and, for `cftc-daily`, `data/cftc/`). Nothing under `record/` is ever added. The commit message stays as it is.

### Change D: remove the already-committed snapshots

One commit: `git rm -r data/kalshi/listings data/gemini/listings data/polymarket-us/listings` and, if present after sports-capture, `data/kalshi/settlements data/gemini/settlements data/polymarket-us/settlements data/kalshi/combos`. Before the `git rm`, copy every one of those files to R2 under the `record/` layout with its original file name (section 8, check 3 proves it). Commit message: `Move platform snapshots to R2; the public repository keeps the method and the filings ledger`.

### Change E: README, CLAUDE.md, LICENSE

README "What is in the record" table: the Listings snapshot row's "Where" becomes `Cloudflare R2 record/<platform>/listings/YYYY-MM-DD.jsonl.gz (access on request)`; the Settlements and Combo rows likewise under `record/`; the Books row is unchanged.

README, after the table, one new paragraph exactly: `The public repository holds the method, the tests, the run records and the CFTC filings ledger. The platform record (listings, books, settlements and combo collections) is kept on R2 and is available under licence; write to the address on paddock.finance/venues.`

README "Citing it" is unchanged. README "Licence" becomes exactly: `Code: MIT. The CFTC filings ledger, the platform registry and the run records in this repository: Creative Commons Attribution 4.0 (CC BY 4.0); attribute Paddock Ledger and the commit. The platform record on R2 is not covered by that licence and is available under licence from Paddock.`

LICENSE: keep the MIT text. Replace the data paragraph with the "Licence" wording above.

CLAUDE.md "Layout": `data/<platform>/listings/` line becomes `record/<platform>/listings/   daily snapshots, written by the collectors, uploaded to R2, gitignored` and add `record/<platform>/settlements/` and `record/kalshi/combos/` on the same pattern. Rule 9 becomes exactly: `**Public repository, private record.** The code, tests, run records and CFTC ledger are public. Platform snapshots, books, settlements and combos go to R2 and are never committed. Nothing here may identify a person.`

### Change F: tests

`tests/test_collectors.py`: every test that asserted an output path under `data/<platform>/` now asserts `record/<platform>/`. Add one test: running each collector in daily mode into a temp root writes nothing under `data/` except `data/runs/`.

## 7. Out of scope (do not do)

- Making the repository private (the founder's one click).
- Rewriting history or scrubbing the two days of listings from past commits.
- Any change to the CFTC collector or `data/cftc/`.
- Any change to what is captured. This task moves files; it never drops a field.
- paddock.finance and the openclaw-news repository.
- Serving the record to anyone (a signed-URL or API step is its own task, after a customer signs).

## 8. Verification checks (run them; paste results into REPORT.md)

1. `python -m pytest -q` green. Paste.
2. From a clean checkout with no R2 keys: `python collectors/kalshi.py --mode daily` writes under `record/kalshi/listings/` and `git status` shows only `data/runs/` changed. Paste both.
3. For every file removed in Change D: its name and byte size in git before removal, and the matching R2 object key and size after upload (from the upload log or an `aws s3 ls`-style listing against R2). Sizes match. Paste the full list.
4. `git log --oneline -5` on the branch shows ordinary commits and `git status` shows no force-push warning. Paste.
5. `grep -rn "DATA / SLUG / \"listings\"\|DATA / SLUG / \"settlements\"\|DATA / SLUG / \"combos\"" collectors/` returns nothing. Paste.
6. Em dash count in README.md, CLAUDE.md, LICENSE and `collectors/` is 0. Paste the grep.
7. Each changed workflow validates as YAML and its commit step lists no `record/` path. Paste the `git add` lines from each.

## 9. Handback

Write `tasks/private-data/REPORT.md` with the result of every check, the files changed, the list of R2 keys created, and anything in `QUESTIONS.md`. Open a draft PR titled `Move the platform record to R2; the public repository keeps the method and the filings ledger` and stop. Do not merge.

End the session with this block:

```
BOARD SYNC
todoist_task: none
closes: none
new issues opened: <#n title> | none
needs_mancy: review and merge the draft PR; flip the repository to private if wanted
live: draft PR <#n>
```
