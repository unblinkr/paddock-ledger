# QUESTIONS: count-fix

## 1. Re-pin could not replace all three files as written (decided, needs a look)

Change C says the re-pin replaces the Oct 26 week folder with fresh copies of all three files. The first attempt exited with `source: gate_failed`: on today's Kalshi snapshot (Oct 26, taken after the 13:20 UTC run) `sports_other_share` is 0.0204, above the 0.02 gate. Nothing was written.

What was done instead: `--repin` rebuilds `filings-recent.json` and `org-topics.json` (the defect is in those) and keeps the pinned `kalshi-week.json` byte for byte. The gate is judged on the pinned Kalshi file (0.011 when it was pinned). `meta.json` keeps the pinned `generated`, `kalshi_days` and `sports_other_share`, updates `filings_generated`, and adds `repinned` with `kalshi_kept: true`.

Why: the Kalshi file is not defective, and keeping it means the Kalshi figures under links the founder already reviewed do not move. Fixing the topic map to clear the gate would have changed those figures and is outside this brief.

Open for the founder: Kalshi's unmapped sports share is above the gate today (0.0204). If it is still above 0.02 on the next Monday run (Nov 2), that week will not pin and the health check will open an issue. A topic-map brief (`weekly-pin` style) is the fix.

## 2. Rothera topics (not in scope, noted)

`topics.py` reads league names. Rothera's contracts are named by team ("Will the Chicago Bulls win ... Event Contract"), so most of them land in Other. The test fixture pins that (topic "Other"). The brief expected NBA. Rothera now counts, but its topic split stays coarse until team-name rules are added.
