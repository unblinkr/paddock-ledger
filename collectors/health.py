"""Daily health check: reads the last 24 hours of run records and says what
is missing. Opens one GitHub issue (via the GITHUB_TOKEN the workflow has)
when a collector missed an hour, reported "unavailable", or when the record
(books or snapshots) is still going to Actions artifacts instead of R2.

Reads data/runs/*.jsonl only. Never fetches an upstream. Exit 0 when clean,
2 when something needs a person, 1 on its own failure.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import timedelta

from common import DATA, RUNS, iso_monday, read_jsonl, utcnow

HOURLY = ("kalshi:hourly", "gemini:hourly", "polymarket-us:hourly")
DAILY = ("cftc:products", "cftc:product-rules", "kalshi:daily", "gemini:daily", "polymarket-us:daily",
         "kalshi:settled", "gemini:settled", "polymarket-us:resolved", "kalshi-combos:daily", "novig:daily")


# Gemini's settled walk is `partial` by construction while its 1,000 per query cap and the
# Sports 503 stand (see gemini.py); the run record discloses it. For this job a partial run
# counts as having run, and only an absent or unavailable run is a missed day.
PARTIAL_OK = ("gemini:settled",)


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
        accepted = ("live", "partial") if c in PARTIAL_OK else ("live",)
        ok = [r for r in rows if r["collector"] == c and r["source"] in accepted]
        if not ok:
            problems.append(f"{c}: no {'/'.join(accepted)} run in the last 24 hours")
    stores = [r for r in rows if r["collector"] == "store"]
    if stores and all(r.get("store") == "actions_artifact" for r in stores):
        problems.append("store: every run went to an Actions artifact (R2 not configured). Artifacts expire after 90 days; set the four R2_* secrets.")
    if any(r.get("store") == "r2" and r["source"] == "unavailable" for r in stores):
        problems.append("store: at least one R2 upload failed in the last 24 hours (books or record)")
    return problems


WEEK_CHECK_AFTER_HOUR_UTC = 14


def week_problem(now, weeks_dir=None) -> str | None:
    """After 14:00 UTC, the ISO Monday's week folder must exist with its meta.json."""
    if now.hour < WEEK_CHECK_AFTER_HOUR_UTC:
        return None
    monday = iso_monday(now.date())
    if (((weeks_dir or DATA / "summaries" / "weeks") / monday / "meta.json")).exists():
        return None
    return monday


def gate_problem(rows: list[dict]) -> dict | None:
    """The newest summaries run in the window, if it failed the Kalshi topic map gate."""
    runs = sorted((r for r in rows if r["collector"] == "summaries"), key=lambda r: r.get("finished", ""))
    if runs and runs[-1]["source"] == "gate_failed":
        return runs[-1]
    return None


def gate_issue(run: dict, kalshi_week: dict, day: str) -> tuple[str, str]:
    share = run.get("counts", {}).get("sports_other_share")
    pct = "n/a" if share is None else f"{share:.2%}"
    top = kalshi_week.get("sports_other_top", [])
    lines = [f"- `{r['series']}`: {r['title']} ({r['volume_24h']:,} contracts)" for r in top] or ["- none listed"]
    body = ("The summaries run wrote its daily files but no week folder, because the unmapped share of Kalshi sports "
            "volume is above the gate.\n\nTop unmapped series:\n" + "\n".join(lines) +
            "\n\nFix: add a rule in collectors/topics.py. Source: data/runs/ and data/summaries/kalshi-week.json. "
            "Opened by collectors/health.py.")
    return f"Kalshi topic map gate failed: {pct} unmapped on {day}", body


def issue_exists(title: str) -> bool:
    """True when an issue with exactly this title is already in the repository, open or closed.
    Fails open (returns False) so a search outage never hides a problem."""
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not (token and repo):
        return False
    q = urllib.parse.quote(f'repo:{repo} in:title type:issue "{title}"')
    req = urllib.request.Request(f"https://api.github.com/search/issues?q={q}&per_page=30",
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return any(i["title"] == title for i in json.loads(r.read()).get("items", []))
    except Exception as e:  # noqa: BLE001
        print(f"issue search failed: {e!r}", file=sys.stderr)
        return False


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
    now = utcnow()
    day = now.strftime("%Y-%m-%d")
    extra = 0
    monday = week_problem(now)
    if monday:
        title = f"Week folder missing for {monday}"
        if not issue_exists(title):
            open_issue(title, f"data/summaries/weeks/{monday}/meta.json does not exist after {WEEK_CHECK_AFTER_HOUR_UTC}:00 UTC. "
                              "Either no summaries run passed the Kalshi topic map gate this week or no run happened. "
                              "Source: data/runs/. Opened by collectors/health.py.")
        extra += 1
    failed = gate_problem(rows)
    if failed:
        kw_path = DATA / "summaries" / "kalshi-week.json"
        kw = json.loads(kw_path.read_text()) if kw_path.exists() else {}
        title, body = gate_issue(failed, kw, day)
        if not issue_exists(title):
            open_issue(title, body)
        extra += 1
    if extra and not problems:
        print(json.dumps({"week_or_gate_problems": extra}))
        return 2
    if problems:
        open_issue(f"Capture check {day}: {len(problems)} problem(s)", "\n".join(f"- {p}" for p in problems) + "\n\nSource: data/runs/. This issue was opened by collectors/health.py.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
