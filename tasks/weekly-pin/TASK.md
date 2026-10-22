# TASK: Pin the venue reports to a Monday snapshot and gate the Kalshi topic map

**Repository:** `unblinkr/paddock-ledger` (not openclaw-news; follow this repo's CLAUDE.md; the `tasks/` folder exists since sports-capture)
**Save this file to:** `tasks/weekly-pin/TASK.md`
**Branch:** `task/weekly-pin`
**Run with:** CLAUDE.md in this repo: branch per change, tests green, merge locally, push `main`. Write `QUESTIONS.md` and `REPORT.md` next to this file.
**Start this task in a fresh Claude Code session.** Do not continue an existing thread; stale context burns tokens and this brief is self-contained.
**Executor model:** sonnet
**Date issued:** 2026-10-22
**todoist_task:** none
**closes:** none
**mockup:** none
**PR mode:** `merge on green` : nothing here changes a public page by itself (the site reads the new files only after the companion openclaw-news task `venues-report-fix` lands). After `git fetch`, confirm local `main` equals `origin/main`, merge locally, push `main`, and run `python collectors/summaries.py` once from the merged checkout so the first week folder exists.

---

## 1. Goal

After this task the summaries the venue pages read are written once a week into an immutable folder named by its Monday, every Kalshi sports series with volume is mapped to a sport, and a run whose Kalshi topic map leaves more than 2 percent of sports volume unmapped writes no week folder and opens an issue.

## 2. Context (self-contained; this session has no other history)

`collectors/summaries.py` writes `data/summaries/filings-recent.json`, `org-topics.json` and `kalshi-week.json` every day (the Oct 22 run stamped 12:11 UTC). paddock.finance/venues/r/<slug> renders from those three files and revalidates every six hours, so a page the founder emails on Monday shows different numbers by Wednesday. On Oct 21 the Novig page said Novig filed the most WNBA contracts; on Oct 22 the 90-day window rolled, WNBA dropped out and MLB came in. The email drafted against the Oct 21 page was wrong against the Oct 22 page. The founder decided on 2026-10-22 that a report link shows one week's numbers for the whole week, and that the week is named by its Monday.

Second finding, same day: `collectors/topics.py` maps Kalshi series tickers to sports, and on the Oct 22 listings snapshot about 11 percent of Kalshi's Sports-category 24-hour volume landed in `Other`. The biggest unmapped series were `KXDPWORLDTOUR` (golf, 1.89M contracts), `KXTESTMATCH` (cricket, 938K), `KXUELGAME` (soccer, 597K), `KXDPWORLDTOURR1LEAD` (golf, 491K), `KXODIMATCH` (cricket, 282K), `KXWT20MATCH` (cricket, 139K), `KXUECLGAME` (soccer, 121K), `KXNEXTTEAMNFL` (NFL, 81K), `KXUELSCORE`, `KXLIGAMXGAME`, `KXARGPREMDIVGAME`, `KXBRASILEIROGAME`, `KXUELTOTAL`, `KXUECLSCORE`, `KXUECLSPREAD`, `KXUECLTOTAL`, `KXUECLBTTS`, `KXUELBTTS`, `KXIDNSLBTTS`, `KXNFLLASTTOLOSE`, `KXNEXTTEAMNBA`, `KXNEXTTEAMNHL`, `KXNBALASTTOLOSE`. Every Golf, Cricket and Soccer volume figure on a venue page is understated until these map, and a page can say "no open Kalshi market in this topic" for a topic Kalshi trades all day. The founder decided the same day that a week folder is written only when the unmapped share is at or below 2 percent.

Field names below marked VERIFIED were read from the Oct 22 files in `data/summaries/`. If something here cannot be built as written, write it to `QUESTIONS.md` and stop that change; ship the others.

## 3. Decisions already made (do not re-ask)

- Week folders live at `data/summaries/weeks/<YYYY-MM-DD>/` where the date is the ISO Monday of the run day (Monday maps to itself). Each holds `filings-recent.json`, `org-topics.json`, `kalshi-week.json` and `meta.json`, byte-identical copies of what the run wrote to `data/summaries/` plus the meta file.
- A week folder is written by the first summaries run of its week that passes the gate, and is never rewritten. A later run in the same week does not touch it. If the Monday run fails the gate and Tuesday's passes, Tuesday's data is pinned under the Monday name; `meta.json` records the real `generated` stamp.
- `data/summaries/weeks/latest.json` holds `{"monday": "<YYYY-MM-DD>"}` for the newest folder written. It is rewritten only when a new folder is written.
- The daily files in `data/summaries/` keep being written every run exactly as today. Nothing that reads them changes.
- The gate is `sports_other_share <= 0.02`, computed on the latest Kalshi series day: the summed `volume_24h` of series with `category == "Sports"` and `topic in ("Other", "Other sports")`, divided by the summed `volume_24h` of all series with `category == "Sports"`. VERIFIED: `category` and `topic` are keys on every series in `data/summaries/kalshi-series/2026-10-22.json`.
- A failed gate still writes the daily files. It writes no week folder, records the run with `source: "gate_failed"`, and `collectors/health.py` opens an issue titled `Kalshi topic map gate failed: <share> unmapped on <day>` listing the top ten unmapped series.
- Topic rules are extended by ticker prefix and by title words, with the series ticker and event title that motivated each rule written in the PR description, as `collectors/topics.py` already requires. No rule is written for a series without a Sports category.
- The threshold `0.02` and the share are facts about the pipeline. They go in `kalshi-week.json` and run records, never on a page (the site enforces that).

## 4. Hard rules (violating any fails the task)

- CLAUDE.md rules 1 to 9 in this repository, in full. Append only; never rewrite an existing week folder or any daily file already in git; every run writes a run record with a `source` marker; no secrets in output; nothing identifies a person.
- No em dashes in README, CLAUDE.md, docstrings, commit messages or issue titles.
- `topics.py` rule order stays specific-before-generic. A new rule must not change the topic of any series or filing name in the existing fixtures (test it).
- Existing fixtures and tests keep passing unchanged.

## 5. Banned terms

none

## 6. Build scope

### Change A: map the unmapped Kalshi sports series

File: `collectors/topics.py`.

Add, in these positions:
- To the `Golf` rule: `KXDPWORLDTOUR|DP World Tour|european tour|genesis championship`
- To the `Cricket` rule: `KXTESTMATCH|KXODIMATCH|KXWT20|KXT20MATCH|KXBBL|test match|\bODI\b|T20 match|big bash` (note `T20` without word boundaries inside a ticker)
- To the `Soccer` rule: `KXUEL|KXUECL|KXLIGAMX|KXARGPREMDIV|KXBRASILEIRO|KXIDNSL|KXEREDIVISIE|KXSAUDIPRO|europa league|conference league|primera|brasileir|liga pro`
- To the `NFL` rule: `NEXTTEAMNFL|NFLLASTTOLOSE`
- To the `NBA` rule: `NEXTTEAMNBA|NBALASTTOLOSE`
- To the `NHL` rule: `NEXTTEAMNHL`

Then run `python collectors/summaries.py` against the Oct 22 listings already in the record, list every remaining `category == "Sports"` series with topic `Other` or `Other sports` and `volume_24h >= 10000`, and add a rule for each until the share on Oct 22 is at or below 0.02. Write every ticker and title you mapped, and the rule it went to, in the PR description. If a series is a sport the rule list has no label for (rugby, darts, cycling and the like), it belongs in `Other sports`, which counts as mapped for the gate: change the gate's numerator to `topic == "Other"` only, and say so in the docstring.

### Change B: `kalshi_week` carries the map's health and the market counts

File: `collectors/summaries.py`, function `kalshi_week`.

Add to the returned dict, all computed on the latest day in `files`:
- `markets_by_topic`: `{topic: summed markets}` from each series' `markets` (VERIFIED key).
- `volume_by_topic_last_day`: `{topic: summed volume_24h}` for the latest day only (the existing `volume_by_topic` stays the sum across days).
- `sports_other_share`: the gate share from section 3, a float rounded to 4 places.
- `sports_other_top`: the ten highest-volume series counted in the numerator, each `{"series": ticker, "title": event title, "volume_24h": n}`.
- `generated`: the run's UTC stamp, same format as `filings-recent.json`.

### Change C: the week folder and `latest.json`

File: `collectors/summaries.py`, in `main()` after the daily files are written.

1. `monday = iso_monday(utcnow().date())`, Monday mapping to itself.
2. If `OUT / "weeks" / monday` exists: do nothing, record `week_written: false`, `week_reason: "exists"`.
3. Else if `sports_other_share > 0.02`: do nothing to `weeks/`, record `source: "gate_failed"`, `week_written: false`, `week_reason: "gate"`, `sports_other_share`.
4. Else: create the folder, copy the three daily files into it byte for byte (`shutil.copyfile`), write `meta.json` as `{"monday": monday, "generated": <stamp>, "filings_generated": <filings-recent generated>, "kalshi_days": [...], "sports_other_share": n}`, then write `weeks/latest.json` as `{"monday": monday}` with `write_atomic`. Record `week_written: true`, `week: monday`.

Add `iso_monday(d: date) -> str` to `collectors/common.py` with a test for a Monday, a Sunday and a Thursday (2026-10-22 maps to 2026-10-19; 2026-10-26 maps to itself; 2026-10-25 maps to 2026-10-19).

### Change D: health

File: `collectors/health.py`.

Two new checks, same issue-opening path as the existing daily checks:
- After 14:00 UTC on any day, if `weeks/<iso_monday(today)>/meta.json` is missing, open `Week folder missing for <monday>` once per week.
- If the latest summaries run record has `source: "gate_failed"`, open `Kalshi topic map gate failed: <share> unmapped on <day>` with the `sports_other_top` list in the body. One issue per day.

### Change E: README

In the README "What is in the record" table add, exactly:
`| Weekly summaries: the three summary files the venue reports read, frozen under the ISO Monday of the week they were written, never rewritten | the daily summaries run | weekly, first passing run of the week | data/summaries/weeks/YYYY-MM-DD/ |`

In "How to read it" add, exactly:
`A venue report shows one week. data/summaries/weeks/latest.json names the newest week folder; the folder's meta.json carries the real generation stamp and the Kalshi topic map share that gated it.`

### Change F: tests

`tests/test_topics.py` (new if absent): every series ticker and title named in section 2 maps to the sport named there; every existing fixture filing name and Kalshi series in the current tests keeps its topic.
`tests/test_summaries.py`: `kalshi_week` on a two-day fixture returns `markets_by_topic`, `sports_other_share` and `sports_other_top` with the expected values; the gate at exactly 0.02 passes and at 0.0201 fails; a second run in the same week leaves the folder byte-identical; a gate failure writes no folder and leaves `latest.json` unchanged.

## 7. Out of scope (do not do)

- Any change to paddock.finance or the openclaw-news repository (companion brief `venues-report-fix` does that).
- Any change to the collectors' capture, cadence, or file families. This task reads the record; it does not add to it.
- Rewriting `data/summaries/kalshi-series/*.json` already in git for earlier days. The Oct 22 series file may be regenerated by the run in Change A's verification because it is today's file; earlier days are not.
- Topic rules for non-sports categories.

## 8. Verification checks (run them; paste results into REPORT.md)

1. `python -m pytest -q` green. Paste.
2. `python collectors/summaries.py` from the branch: paste the run record line and the `sports_other_share` value before Change A (from `main`) and after. After must be at or below 0.02.
3. `ls data/summaries/weeks/` shows one folder named by this week's Monday and `latest.json`; `cat data/summaries/weeks/latest.json`; `cat data/summaries/weeks/<monday>/meta.json`. Paste.
4. Run `python collectors/summaries.py` a second time: `git status` shows the week folder unchanged and only the daily files modified. Paste.
5. `python -c "import json;k=json.load(open('data/summaries/kalshi-week.json'));print(k['sports_other_share'],k['sports_other_top'][:3],k['markets_by_topic'].get('Esports'))"`. Paste.
6. `LC_ALL=C.UTF-8 grep -rnP "\x{2014}" README.md CLAUDE.md collectors/ tests/` returns nothing. Paste.
7. The `.github/workflows` file that runs `summaries.py` is unchanged (`git diff main -- .github/` is empty). Paste.

## 9. Handback

Write `tasks/weekly-pin/REPORT.md` with: the result of every check in section 8, the full list of series tickers mapped in Change A with their new topics, the share before and after, the files changed, and anything written to `QUESTIONS.md`.

Under `merge on green`: merge locally, push `main`, run `python collectors/summaries.py` once from the merged checkout and commit the week folder it writes, and paste the raw URL of `data/summaries/weeks/latest.json` on `main`.

End the session with this block, exactly this shape:

```
BOARD SYNC
todoist_task: none
closes: none
new issues opened: <#n title> | none
needs_mancy: <one line> | none
live: main at <sha> | draft PR <#n>
```
