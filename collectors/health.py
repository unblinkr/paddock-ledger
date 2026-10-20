"""Daily health check: reads the last 24 hours of run records and says what
is missing. Opens one GitHub issue (via the GITHUB_TOKEN the workflow has)
when a collector missed an hour, reported "unavailable", or when books are
still going to Actions artifacts instead of R2.

Reads data/runs/*.jsonl only. Never fetches an upstream. Exit 0 when clean,
2 when something needs a person, 1 on its own failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import timedelta

from common import RUNS, read_jsonl, utcnow

HOURLY = ("kalshi:hourly", "gemini:hourly", "polymarket-us:hourly")
DAILY = ("cftc:products", "cftc:product-rules", "kalshi:daily", "gemini:daily", "polymarket-us:daily")


def last_24h() -> list[dict]:
    now = utcnow()
    rows: list[dict] = []
    for d in (now - timedelta(days=1), now):
        folder = RUNS / d.strftime("%Y-%m-%d")
        for f in sorted(folder.glob("*.jsonl")) if folder.exists() else []:
            rows.extend(read_jsonl(f))
    cutoff = (now - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [r for r in rows if r.get("finished", "") >= cutoff]


def assess(rows: list[dict]) -> list[str]:
    problems: list[str] = []
    for c in HOURLY:
        hours = sorted({r["started"][:13] for r in rows if r["collector"] == c and r["source"] in ("live", "partial")})
        missing = 24 - len(hours)
        if missing > 2:
            problems.append(f"{c}: {len(hours)} of the last 24 hours recorded ({missing} missing)")
        bad = [r for r in rows if r["collector"] == c and r["source"] == "unavailable"]
        if bad:
            problems.append(f"{c}: {len(bad)} unavailable run(s); last note: {bad[-1].get('note', '')}")
        partial = [r for r in rows if r["collector"] == c and r["source"] == "partial"]
        if partial:
            problems.append(f"{c}: {len(partial)} partial run(s) (a cap or an unfinished walk); see counts in data/runs")
    for c in DAILY:
        ok = [r for r in rows if r["collector"] == c and r["source"] == "live"]
        if not ok:
            problems.append(f"{c}: no live run in the last 24 hours")
    stores = [r for r in rows if r["collector"] == "store"]
    if stores and all(r.get("store") == "actions_artifact" for r in stores):
        problems.append("books: every hour went to an Actions artifact (R2 not configured). Artifacts expire after 90 days; set the four R2_* secrets.")
    if any(r.get("store") == "r2" and r["source"] == "unavailable" for r in stores):
        problems.append("books: at least one R2 upload failed in the last 24 hours")
    return problems


def open_issue(title: str, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        print("no GITHUB_TOKEN/GITHUB_REPOSITORY; not opening an issue", file=sys.stderr)
        return
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=json.dumps({"title": title, "body": body, "labels": ["capture"]}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        print(json.loads(r.read())["html_url"])


def main() -> int:
    rows = last_24h()
    problems = assess(rows)
    summary = {"runs_seen": len(rows), "problems": problems}
    print(json.dumps(summary, indent=1))
    if problems:
        day = utcnow().strftime("%Y-%m-%d")
        open_issue(f"Capture check {day}: {len(problems)} problem(s)", "\n".join(f"- {p}" for p in problems) + "\n\nSource: data/runs/. This issue was opened by collectors/health.py.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
