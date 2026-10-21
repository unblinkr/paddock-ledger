# QUESTIONS, tasks/private-data

Written 2026-10-21 by the chat session that ran this task (not a Code session).

1. **Change D is split in two, because this session has no R2 keys.** The brief says to copy every committed snapshot to R2 and prove it before `git rm`. The keys live only in repository secrets, so the copy cannot run from here. What shipped instead: `collectors/store.py --migrate-legacy` and a by-hand workflow `migrate-record` that uploads the ten committed snapshot files to their `record/` keys and commits a manifest (file, key, bytes) as a run record. Nothing is deleted. The `git rm` is a follow-up commit, made after the manifest in `data/runs/<day>/migrate-record.jsonl` shows all ten files with the sizes listed in REPORT.md. The files are also in git history whatever happens, so rule 1 holds either way.

2. **Fixtures were trimmed.** The founder's instruction on 2026-10-21 (public repository, private record) overrides the sports-capture rule that a fixture is the full saved response: `kalshi-settled-page1.json` 200 to 25 markets, `kalshi-settled-singles.json` 100 to 25, `kalshi-combos.json` keeps its 5 collections but each `associated_events` and `associated_event_tickers` list is cut to 25 entries (three collections carried 2,653 each). The smaller Gemini and Polymarket US fixtures were left whole. Every test still passes against the trimmed files.

3. **`data/summaries/` stays public and is still committed by `listings-daily`.** It holds per-series daily aggregates (volume by topic, top markets) that the site reads. That is the "aggregates public, rows private" line the founder drew; if the summaries should also go private, that is a one-line change to `listings-daily.yml` and `summaries.py` (write under `record/`).

4. **`cftc-daily.yml` still runs `git add data/`.** It is out of scope by the brief and harmless now that nothing writes snapshots under `data/`, but it is the one workflow that would re-commit a stray file if a collector ever regressed. Suggest changing it to `git add data/cftc/ data/runs/` in a later brief.

5. **The combos run dispatched this morning did not land a second file**: `main` holds one combos file, `2026-10-21.jsonl.gz`, so the legacy list is ten files, not eleven.
