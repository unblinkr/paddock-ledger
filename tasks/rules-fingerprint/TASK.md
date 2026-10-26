# Dated rules fingerprints on every venue

Branch: task/rules-fingerprint. Executor: Claude Code. PR mode: draft PR, stop.
Start in a fresh Claude Code session.

1. Goal: Gemini and Polymarket US rows carry `rules_sha256`, as Kalshi's do, so a rules change is visible as a changed hash.
2. Done here: `collectors/rules.py` (definitions in its docstring), hash on daily, hourly and settled rows, tests on saved fixtures, README line.
3. Do not change: Kalshi `rules_sha256`; any existing field; capture volume.
4. Open decision for the owner: the Gemini definition is permanent once rows exist. It covers contract description, event description and terms URL; it does not fetch the terms PDF.
5. Not done: a rules-changes ledger (needs an R2 download helper), a second brief.
