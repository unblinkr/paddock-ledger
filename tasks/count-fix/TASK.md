# TASK: Count each CFTC filing once by its first date, count Rothera's event contracts, and re-pin the Oct 26 week

**Repository:** `unblinkr/paddock-ledger`
**Save this file to:** `tasks/count-fix/TASK.md`
**Branch:** `task/count-fix`
**Run with:** CLAUDE.md in this repository: branch per change, tests green, merge locally, push `main`. Write `QUESTIONS.md` and `REPORT.md` next to this file.
**Start this task in a fresh Claude Code session.** Do not continue an existing thread; stale context burns tokens and this brief is self-contained.
**Run this task BEFORE `venues-framing` (openclaw-news). That task reads the files this one writes.**
**Executor model:** sonnet
**Date issued:** 2026-10-26
**todoist_task:** 6hr3mv86Qf8pmMGw
**closes:** none
**mockup:** none
**PR mode:** `merge on green` : the corrected files feed private venue pages that no recipient has seen yet; no price, no corrections-log entry, no index, denylist or firewall change. After `git fetch`, confirm local `main` equals `origin/main`, merge locally, push `main`, then run the re-pin command in Change C once from the merged checkout.

---

## 1. Goal

After this task, every filing count the venue pages read counts a filing once, on the date it was first filed; a withdrawal of an older filing is never counted as a new filing; Rothera's event contracts are counted; and the Oct 26 week folder holds the corrected files.

## 2. Context (self-contained; this session has no other history)

`collectors/summaries.py` builds `filings-recent.json` and `org-topics.json`, which paddock.finance/venues/r/<slug> renders. Two defects were found on Oct 26 by recomputing the Novig page from `data/cftc/products.jsonl` (checked out at commit 1bb7d77).

1. `filings_recent()` keeps the LAST line per filing id ("later lines win: the newest status"). A withdrawal is a later line with a later date, so it replaces the original filing's date and shows as a new filing. The Oct 20 to Oct 26 table said 77 contracts filed. Nine of those rows are withdrawal lines for filings made earlier (ProphetX 5, DKeX 4). The other 68 were first filed that week.
2. Both `filings_recent()` and `org_topics()` keep only `category == "Event"`. Rothera (CFTC code ROTHDCM) files its event contracts as `Financial Instrument` (subcategory `Other Financial Instrument`): 128 of its 131 filings. About 107 are event contracts, named like "Will the Bulls win ... Event Contract". Ten were filed on Oct 22 (college football and college basketball). Rothera therefore shows 0 in every topic on every page. Crypto.com (CDNA) and Kalshi have older non-Event filings of the same form, all dated before June 2026.

Founder decisions, Oct 26: the pages count filings, not shelves; Rothera must appear; a filing that was withdrawn later still counts as filed on its first date.

If something here cannot be built as written, write it to `QUESTIONS.md` and stop that change; ship the others.

## 3. Decisions already made (do not re-ask)

- A filing is a CFTC filing id. Its `date` is the date of the EARLIEST line for that id in `data/cftc/products.jsonl`. Its `status` is the status on the LATEST line.
- A filing counts in a window when its `date` falls in the window, whatever its status later became. A withdrawal line for a filing first made before the window adds nothing to the window.
- An event contract is a row where `category == "Event"`, OR the category is anything else and `product_name` matches the case-insensitive regex `event contract|^will\b`. The helper `is_event_contract(row)` lives in `collectors/topics.py` and both summaries use it. Only organizations already in `data/cftc/orgs.json` are counted, as today.
- Field names in the summary files do not change. `date` now means first-filed date; `status` stays the latest status.
- `data/cftc/` is not touched. CLAUDE.md rule 4 holds: no ledger row is edited.
- CLAUDE.md says a week folder is never rewritten. This task makes ONE exception, behind an explicit flag, because no venue link has been sent. The old files stay in git history.
- `data/summaries/weeks/latest.json` stays `{"monday": "2026-10-26"}`.
- The daily files in `data/summaries/` keep being written every run, with the new rules.

## 4. Hard rules (violating any fails the task)

- CLAUDE.md rules 1 to 9 in this repository, in full.
- No em dashes in README, CLAUDE.md, docstrings, commit messages, issue titles or run records.
- Existing tests and fixtures keep passing unchanged, except a test that pinned the old counting; list each in REPORT.md.
- Every run writes a run record with a `source` marker.
- No secrets in output.

## 5. Banned terms

none

## 6. Build scope

### Change A: `is_event_contract` and first-date counting in `filings_recent()`

`collectors/topics.py`: add `EVENT_FORM = re.compile(r"event contract|^will\b", re.I)` and `is_event_contract(row: dict) -> bool` returning `row.get("category") == "Event" or bool(EVENT_FORM.search(row.get("product_name", "")))`.

`collectors/summaries.py`, `filings_recent()`: read every line. For each id keep `first` (smallest `date`; ties by file order) and `last` (final line in file order). Skip ids whose organization is not in `orgs` or where `is_event_contract(first)` is false. A filing is included when `first["date"] >= cutoff`. Each output row takes `date` from `first`, `status` from `last`, and every other field from `last`, as today. The sort order is unchanged.

### Change B: `org_topics()`

Use the same first-line rule and `is_event_contract`. Count and `last` (most recent filing date in the topic) are by first-filed date.

### Change C: one-time re-pin of the Oct 26 week

Add to `collectors/summaries.py` the flags `--repin <monday>` and `--reason "<text>"`. Both are required together. The command runs the normal daily build, then replaces `data/summaries/weeks/<monday>/` with fresh copies of the three files and `meta.json`. `meta.json` gains `"repinned": {"at": "<UTC stamp>", "reason": "<text>", "previous_generated": "<the old meta generated stamp>"}`. It does not touch `latest.json`. Without both flags the existing never-rewrite behaviour is unchanged (add a test that proves a plain run still skips an existing week).

Run it once after merge:
`python collectors/summaries.py --repin 2026-10-26 --reason "count each filing once by first date; count Rothera event contracts"`

The run record for that run has `source: "live"` and a `repin` field in its counts. Commit the result to `main` with the bot identity the workflows use, or as a normal commit, then push.

### Change D: tests (`tests/`)

Add fixtures and tests on real saved lines (copy the ids named below from `data/cftc/products.jsonl` into a small fixture file; do not invent rows):
1. An id with a Certified line and a later Withdrawn line: counts once, on the first date, with `status == "Withdrawn"`.
2. A withdrawal line dated inside the window for an id first filed before the window: not counted in the window.
3. A Rothera `Financial Instrument` row named "Will the Chicago Bulls win the Bulls vs Raptors game on October 21, 2026? Event Contract": counted, topic NBA.
4. A 2019 Rothera row named "USD-BTC Day-Ahead Swaps": not counted.
5. A CDNA row named "Solana Event Contract" (category `Financial Instrument`): counted by `org_topics`, outside any 90-day window.
6. `--repin` without `--reason` exits non-zero and writes nothing.

## 7. Out of scope (do not do)

- `data/cftc/` and the CFTC collector.
- Any change to `kalshi-week.json` or `kalshi_series`.
- `topics.py` topic rules other than adding `is_event_contract`.
- The site repository (companion task `venues-framing`).
- Platform listing data, R2, books, settlements.

## 8. Verification checks (run them; paste results into REPORT.md)

Window for the first three checks: filings with `date` from 2026-10-20 to 2026-10-26 for the week, and 2026-07-28 to 2026-10-26 for 90 days. Expected values were computed by hand on Oct 26 from the ledger; if yours differ, say so in REPORT.md and do not adjust the code to match.

1. Week table from `data/summaries/weeks/2026-10-26/filings-recent.json` after the re-pin: Kalshi 18, Polymarket US 17, ProphetX 15, Gemini 12, Rothera 10, DKeX 4, Novig 2; total 78, 7 exchanges. Paste the count by platform. Paste the before value (77, six exchanges, ProphetX 20, DKeX 8) from the old file in git history.
2. 90-day Esports: ProphetX 35, UDX 16. Golf: UDX 10, Rothera 3, Kalshi 1. Table tennis: DKeX 6, Kalshi 5. Paste the counts.
3. Rothera 90-day filings in `org-topics.json` or the 90-day rows: 94. Paste the count by topic.
4. `meta.json` in the Oct 26 week folder has `repinned` with the reason and `previous_generated`. Paste it. `latest.json` still reads 2026-10-26. Paste it.
5. A plain `python collectors/summaries.py` run afterwards leaves the Oct 26 week folder byte-identical. Paste `git status` showing no change there.
6. `data/cftc/` has no diff against `origin/main` before the re-pin commit. Paste `git diff --stat origin/main -- data/cftc`.
7. Em dash count in changed files, docstrings and the commit messages is 0. Paste the command and output.
8. Full test suite passes. Paste the summary line.

## 9. Handback

Write `tasks/count-fix/REPORT.md` with: the result of every check in section 8, the before and after counts from checks 1 to 3 side by side, the list of files changed, and anything written to `QUESTIONS.md`. Update `docs/STATUS.md` if the repo keeps one.

Report the merge commit and confirm the re-pin commit is on `main`.

End the session with this block, exactly this shape, so the founder can paste it to chat and the board gets updated:

```
BOARD SYNC
todoist_task: 6hr3mv86Qf8pmMGw : complete | keep open (<reason>)
closes: none
new issues opened: <#n title> | none
needs_mancy: <one line> | none
live: main <merge commit>
```
