# Questions and assumptions: weekly-pin

Format: question / what I assumed / how to reverse it.

## NEEDS MANCY (non-blocking, one decision)

1. health-daily runs at 08:15 UTC, so the new "Week folder missing" check, which only fires after 14:00 UTC, never fires on schedule.
   - Assumed: shipped the check as briefed (it works when run after 14:00, tested) and left `.github/workflows/health-daily.yml` alone, because the brief's check 7 requires `.github/` unchanged apart from the summaries add path.
   - Recommendation: add a second cron `20 14 * * *` to health-daily.yml (one line). Until then, a missing week is noticed only through the gate-failed issue, which does fire at 08:15.
   - Reverse: nothing to reverse.

## Assumptions

2. `record/` is not on disk (gitignored, lives on R2), so `summaries.py` cannot rebuild series from listings here.
   - Assumed: `kalshi_week` re-derives topics at read time from the committed series files. Only a series stored as `Other` or `Other sports` is re-read with `topic(series_ticker, title)`; a series with any other stored topic keeps it, because the stored label was derived with the market title too and the series file does not carry that. No committed series file was rewritten.
   - Side effect: past days keep their old label for series that were wrongly mapped before (for example `KXWT20MATCH` stored as Weather on an earlier day because of "Hurricanes" in a team name). Oct 22 volume_by_topic for Weather and Cricket carries that history. The new rule fixes it going forward.
   - Reverse: delete `effective_topic` and use `s["topic"]` in `kalshi_week`.

3. Workflow add paths. `listings-daily.yml` runs `git add data/runs/ data/summaries/` and `cftc-daily.yml` runs `git add data/`. Both pick up `data/summaries/weeks/`. No workflow change made.

4. Gate numerator is `topic == "Other"` only, per Change A. `Other sports` counts as mapped. Documented in the `summaries.py` docstring.

5. The gate compares the share as recorded (rounded to 4 places), so 0.02004 records as 0.02 and passes. At exactly 0.02 it passes and at 0.0201 it fails, as briefed.

6. No sports volume on the latest day gives `sports_other_share: null`, which fails the gate (absent is not zero).

7. Rule deviations from the brief's list, each to satisfy "a new rule must not change the topic of any filing name":
   - Soccer `brasileir` became `brasileir.o`. The bare form moved seven single-stock filing names (Petroleo Brasileiro, Cia Brasileira de Distribuicao, Empresa Brasileira De Ae) from Other to Soccer. `brasileir.o` still matches Brasileirao and Brasileirão.
   - `KXLIGAPROMATCH` ("Klimentev Vladimir vs CHagaev Aleksei", 7,368 contracts) would have gone to Soccer through `liga pro`. Player names point to the Russian table tennis Liga Pro, so it is in the Table tennis rule, which comes first. Assumption from the names only; `liga pro` stays in Soccer for the Ecuadorian LigaPro (`KXECULPGAME`). Reverse: remove `KXLIGAPROMATCH` from the Table tennis rule.

8. Extra rules beyond the brief's list. With the briefed rules alone the Oct 22 share is already below 0.02, so the brief's "until" condition did not call for more. I still mapped the four series with remaining volume at or above 10,000 that are unambiguous, since the stated purpose is correct Golf, Cricket and Soccer figures: `KXCHAMPTOUR` (Golf), `KXWODIMATCH` (Cricket), `KXKBLGAME` (Other basketball), `KXCONMEBOL` prefix (Soccer; `KXCONMEBOLLIBGAME` 6.3K, `KXCONMEBOLLIBADVANCE` 9.8K). `KXSOLAXQUAL` (10.8K, lacrosse) already maps to Other sports. Reverse: remove the four tokens.

9. Brief item 5 (gate cannot reach 0.02) did not occur.

10. `record_run` now accepts `source: "gate_failed"`. The brief requires that marker; the assert in `common.py` rejected it. README "How to read it" source list left as briefed (only the one added sentence).

11. The extra files `tests/fixtures/topics-baseline.json` (1,016 filing names and 400 Oct 22 series with their pre-change labels) is the "existing fixtures keep their topic" test. It is a sample, stratified by label, not the full 20,809 names. A full pass over every name in `data/cftc/products.jsonl` was run once by hand against main's topics.py: 7 names moved before the `brasileir` fix, 0 after.
