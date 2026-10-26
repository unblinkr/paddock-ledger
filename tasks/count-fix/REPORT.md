# REPORT: count-fix

Run on 2026-10-26 from the chat session. Merged to `main` and pushed. One deviation from the brief, logged in `QUESTIONS.md`: the re-pin keeps the pinned `kalshi-week.json` (today's Kalshi snapshot fails the 0.02 gate at 0.0204; the pinned one passed at 0.011).

## Checks (section 8)

1. Week Oct 20 to Oct 26, `weeks/2026-10-26/filings-recent.json`
   - Before: 77 filings, 6 exchanges: Kalshi 18, Polymarket US 17, ProphetX 20, Gemini 12, DKeX 8, Novig 2.
   - After: 78 filings, 7 exchanges: Kalshi 18, Polymarket US 17, ProphetX 15, Gemini 12, Rothera 10, DKeX 4, Novig 2. Matches the expected values.
2. 90 days since 2026-07-28
   - Esports: ProphetX 35, UDX 16 (unchanged; a filing withdrawn later still counts on its first date).
   - Golf: UDX 10, Rothera 3, Kalshi 1 (Rothera added).
   - Table tennis: DKeX 6, Kalshi 5 (unchanged).
3. Rothera 90-day filings: 94. By topic: Other 27, NBA 16, NHL 11, College basketball 8, College football 5, NFL 5, Elections and politics 4, Soccer 4, Tennis 4, Golf 3, MLB 3, Financials 3, Companies and tech 1. Novig 90-day event filings: 201 before and after.
4. `weeks/2026-10-26/meta.json` has `repinned: {at: 2026-10-26T20:26:10Z, kalshi_kept: true, previous_generated: 2026-10-26T05:43:44Z, reason: "count each filing once by first date; count Rothera event contracts"}`. `weeks/latest.json` still reads `{"monday": "2026-10-26"}`.
5. A plain `python collectors/summaries.py` after the re-pin returned `week_reason: exists`. The week folder hash was 27f7f12c3f763931 before and after.
6. `git diff --stat origin/main -- data/cftc` is empty before the re-pin commit.
7. Em dash count in changed files: 0 (`summaries.py`, `topics.py`, `tests/test_count_fix.py`, `tasks/count-fix/*`).
8. `python3 -m pytest -q`: 75 passed.

## Files changed

`collectors/topics.py` (`EVENT_FORM`, `is_event_contract`), `collectors/summaries.py` (`_filings`, first-date counting in `filings_recent` and `org_topics`, `_build_week`, `repin_week`, `--repin` and `--reason`), `tests/test_count_fix.py`, `tests/fixtures/cftc-count-fix-lines.jsonl`, `tasks/count-fix/*`, `data/summaries/weeks/2026-10-26/{filings-recent,org-topics,meta}.json`, `data/runs/2026-10-26/local.jsonl` (four run records: the first re-pin attempt that hit the gate, the re-pin, two plain runs).

The daily files in `data/summaries/` were not committed; the scheduled run rewrites them with the new rules.

## Notes

- The brief expected the Rothera "Bulls win" row to read as NBA. The topic rules read league names, so it reads as Other. The test pins Other. Rothera topics stay coarse until team-name rules exist.
- No existing test pinned the old counting.
- Today's Kalshi `sports_other_share` is 0.0204. If it is still above 0.02 on Nov 2 the new week will not pin. See `QUESTIONS.md`.

```
BOARD SYNC
todoist_task: 6hr3mv86Qf8pmMGw : complete
closes: none
new issues opened: none
needs_mancy: Kalshi unmapped sports share is 0.0204, above the 0.02 gate; a topic-map brief is needed before the Nov 2 pin
live: main
```
