# REPORT: weekly-pin

## NEEDS MANCY

One decision, not blocking. health-daily runs at 08:15 UTC, so the new "Week folder missing" check (after 14:00 UTC) never fires on schedule. Recommendation: add a second cron `20 14 * * *` to `.github/workflows/health-daily.yml`. I left the workflow alone because check 7 requires `.github/` unchanged. The gate-failed issue does fire at 08:15. See QUESTIONS.md item 1.

## What shipped

All six changes (A to F), merged locally with --no-ff and pushed to `main`. Main sha after merge: 2398548 (the week-folder data commit follows it, see the final handback).

- Change A: topic rules. Share on Oct 22 Kalshi sports volume went from 0.1213 (topic `Other` only; 0.1215 counting `Other sports`) to 0.0021. Gate threshold untouched at 0.02.
- Change B: `kalshi_week` returns `markets_by_topic`, `volume_by_topic_last_day`, `sports_other_share`, `sports_other_top`, `generated`.
- Change C: `pin_week` in summaries.py, `iso_monday` in common.py. `record_run` accepts `gate_failed`.
- Change D: `week_problem`, `gate_problem`, `gate_issue`, `issue_exists` in health.py (issues deduped by exact title).
- Change E: two README lines, exact text.
- Change F: `tests/test_topics.py`, `tests/test_summaries.py`, `tests/fixtures/topics-baseline.json`.

Not shipped: nothing from the brief. Workflow change: none. Both workflows that run summaries.py (`listings-daily.yml` adds `data/runs/ data/summaries/`, `cftc-daily.yml` adds `data/`) already pick up `data/summaries/weeks/`.

## Series mapped in Change A (ticker, Oct 22 event title, new topic)

Golf: KXDPWORLDTOUR (Genesis Championship Winner), KXDPWORLDTOURR1LEAD (Genesis Championship End of Round 1 Leader), KXCHAMPTOUR (Stifel Charity Classic Winner; extra)
Cricket: KXTESTMATCH (New Zealand A vs India A), KXODIMATCH (Namibia vs Ireland), KXWT20MATCH (Sydney Thunder Women vs Perth Scorchers Women), KXWODIMATCH (India vs Zimbabwe; extra)
Soccer: KXUELGAME, KXUECLGAME, KXUELSCORE, KXUELTOTAL, KXUELBTTS, KXUELSPREAD, KXUEL1H and siblings, KXUECLSCORE, KXUECLSPREAD, KXUECLTOTAL, KXUECLBTTS, KXLIGAMXGAME (Cruz Azul vs Leon), KXARGPREMDIVGAME (Union Santa Fe vs Estudiantes La Plata), KXBRASILEIROGAME (Palmeiras vs Remo), KXIDNSLGAME, KXIDNSLTOTAL, KXIDNSLBTTS (Madura United vs Persib Bandung), KXCONMEBOLLIB* (Flamengo vs Estudiantes La Plata; extra)
NFL: KXNEXTTEAMNFL (Josh Allen's Next Team), KXNFLLASTTOLOSE
NBA: KXNEXTTEAMNBA (Jayson Tatum's Next Team), KXNBALASTTOLOSE
NHL: KXNEXTTEAMNHL (Zach Werenski's Next Team)
Other basketball: KXKBLGAME (Samsung Thunders vs Daegu Pegasus; extra)
Table tennis: KXLIGAPROMATCH (Klimentev Vladimir vs CHagaev Aleksei; extra, and kept out of Soccer on purpose)

72 Oct 22 sports series changed topic in total. Two rules deviate from the brief's wording (`brasileir` became `brasileir.o`; Liga Pro match series to Table tennis); reasons in QUESTIONS.md item 7. Remaining unmapped Oct 22: 0.0021 of sports volume, top series KXSAUDIPLTOTAL, KXEBASKETBALLGAME, KXVLEAGUE1GAME, all under 7.5K contracts.

## Findings

- `record/` is not on disk, so topics are re-derived at read time from the committed series files (QUESTIONS.md item 2). The Oct 22 file stored 12.15% of sports volume in Other or Other sports.
- The brief's `brasileir` rule would have moved seven single-stock filing names to Soccer. Caught by comparing every product name in `data/cftc/products.jsonl` against main.
- Past-day series labels are kept as stored, so some historical volume (for example KXWT20MATCH once stored as Weather) stays where it was.

## Verification (section 8)

1. `python -m pytest -q`: 66 passed (25 existing, 41 new).
2. Before, from main's committed Oct 22 series (main emits no share field): 0.1213 (Other) / 0.1215 (Other plus Other sports). After, from the branch run: 0.0021. Branch run record:
   `{"collector": "summaries", "counts": {"filings": 1986, "kalshi_days_written": 0, "sports_other_share": 0.0021, "week": "2026-10-19", "week_reason": "written", "week_written": true}, "source": "live", ...}`
   Main's own run record: `{"counts": {"filings": 1986, "kalshi_days_written": 0}, "source": "live"}`.
3. `ls data/summaries/weeks/`: `2026-10-19  latest.json`. `latest.json`: `{"monday": "2026-10-19"}`. `meta.json`: `{"filings_generated": "2026-10-22T17:29:00Z", "generated": "2026-10-22T17:29:01Z", "kalshi_days": ["2026-10-20", "2026-10-21", "2026-10-22"], "monday": "2026-10-19", "sports_other_share": 0.0021}` (branch run; the committed folder is from the post-merge run on main).
4. Second run: run record had `week_written: false, week_reason: "exists"`; `diff -r` of `weeks/` against a copy taken before the second run: identical; `git status` showed only the daily files modified.
5. `0.0021 [KXSAUDIPLTOTAL 7495, KXEBASKETBALLGAME 7296, KXVLEAGUE1GAME 6799] 1091` (share, top three, Esports markets).
6. Em dash grep over README.md, CLAUDE.md, collectors/, tests/ and tasks/weekly-pin/: no matches.
7. `git diff main -- .github/`: empty.

Gate proof: with the threshold set to 0.021, `test_gate_boundary` and `test_gate_failure_writes_no_folder_and_keeps_latest` failed; restored to 0.02, green.

## Files changed

README.md, collectors/common.py, collectors/health.py, collectors/summaries.py, collectors/topics.py, tests/test_topics.py, tests/test_summaries.py, tests/fixtures/topics-baseline.json, tasks/weekly-pin/{TASK,QUESTIONS,REPORT}.md. Post-merge data commit: data/summaries/weeks/, refreshed daily summaries, data/runs/2026-10-22/weekly-pin.jsonl.

Preview URL: none (no page changes; the site reads the new files only after `venues-report-fix`).
PR: none; merged locally per the brief.
