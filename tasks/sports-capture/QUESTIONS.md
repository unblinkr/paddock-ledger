# Questions

Nothing blocked a change. These need a decision (each also has a GitHub issue):

1. Gemini `status=settled&category=Sports` returns 503 on every request (limits 1 to 500, offsets 0/500/990). Sports settlements are not captured until Gemini fixes it or we find another route. Issue #8.
2. Gemini settled has no date filter and a 1,000 cap per category; Crypto's 1,000 spans about 15 hours, so a daily run loses older hourly crypto events. Should the settled walk run more often than daily? Issue #8.
3. Polymarket US: resolutions are bounded by `endDateMin`/`endDateMax` only (shipped). Markets closed before their endDate are missed. Issue #9.
4. Kalshi settlements are 11.4 MB gzipped a day in git. When do they move to R2? Issue #10.
5. Brief said count Kalshi combo legs skipped in the settled walk. A full unfiltered walk ran over 30 minutes without finishing, so the walk sends `mve_filter=exclude` (server honours it) and `markets_combo_legs_skipped` is 0 by construction. The number of combos held back is not counted. Say if you want a periodic count.
6. `gemini:settled` is `partial` by construction (cap, Sports 503), so health.py accepts `partial` for it only (otherwise it would open an issue every day).

Polymarket US requests tried for Change E (all `closed=true&limit=5`, one second apart): `updatedAfter`, `updatedAtMin`, `endDateAfter`, `since`, `order=updatedAt&direction=desc`, `orderBy=updatedAt&ascending=false` returned the same ids as no filter (ignored). `endDateMin` and `startDateMin` changed the result; with a 36 hour `endDateMin`, 0 of 500 rows had endDate below the cut. `endDateMin`+`endDateMax` returned 39,805 rows over 80 pages, all inside the window.
