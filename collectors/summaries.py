"""Small daily summaries the site reads, built from the record already on disk.

  data/summaries/filings-recent.json
      Event-contract filings from the last 120 days by every exchange mapped in
      data/cftc/orgs.json: id, date, organization code, platform slug, product
      name, and a topic label from collectors/topics.py (a reading aid; the
      product name is kept beside it so any label can be checked).

  data/summaries/kalshi-series/YYYY-MM-DD.json
      From that day's Kalshi listings snapshot: per series, its topic, Kalshi
      category, market count, the summed 24-hour contract volume, and the three
      busiest markets. Volume is Kalshi's own `volume_24h_fp` (contracts) at
      snapshot time; combos are not in the snapshot.

  data/summaries/kalshi-week.json
      Kalshi volume by topic over the last seven snapshots, the latest day's
      market counts and volume by topic, and the health of the topic map:
      `sports_other_share` is the summed volume_24h of series with category
      "Sports" and topic "Other" divided by the summed volume_24h of all
      series with category "Sports", on the latest day. Topic "Other sports"
      (rugby, darts, cycling and the like) is a label, so it counts as mapped;
      only "Other" is unmapped. Topics are re-derived from the committed series
      files at read time for series stored as Other or Other sports, so a rule
      change in topics.py takes effect without the local listings. The stored
      files for past days are never rewritten.

  data/summaries/weeks/<YYYY-MM-DD>/ and weeks/latest.json
      The three files above, byte for byte, frozen under the ISO Monday of the
      week of the first run that passes the gate (sports_other_share <= 0.02).
      Never rewritten. A run that fails the gate writes the daily files, no
      week folder, and records source "gate_failed". The share and threshold
      are pipeline facts: they live in kalshi-week.json, meta.json and run
      records, never on a page.

No fetches. Reads data/cftc/*.jsonl and the Kalshi listings under record/
(the local copy written by that day's run; earlier days' series files are
already in git and are not rewritten).
"""

from __future__ import annotations

import gzip
import json
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import DATA, RECORD, iso_monday, record_run, utcnow, write_atomic
from topics import is_sport, topic

OUT = DATA / "summaries"
GATE_MAX_OTHER_SHARE = 0.02  # a week folder is written only at or below this share of unmapped Kalshi sports volume
DAILY_FILES = ("filings-recent.json", "org-topics.json", "kalshi-week.json")


def _num(x) -> float:
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def filings_recent(days: int = 120) -> dict:
    orgs = json.loads((DATA / "cftc" / "orgs.json").read_text())["orgs"]
    cutoff = (utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    latest: dict[int, dict] = {}
    with (DATA / "cftc" / "products.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("date", "") < cutoff or r.get("organization") not in orgs:
                continue
            if r.get("category") != "Event":
                continue
            latest[r["id"]] = r  # later lines win: the newest status
    rows = []
    for r in sorted(latest.values(), key=lambda r: (r["date"], r["id"]), reverse=True):
        t = topic(r["product_name"])
        rows.append({
            "id": r["id"], "date": r["date"], "org": r["organization"], "platform": orgs[r["organization"]]["slug"],
            "name": r["product_name"], "status": r["status"], "topic": t, "sport": is_sport(t), "url": r["url"],
        })
    return {"generated": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "window_days": days, "since": cutoff, "rows": rows,
            "orgs": {k: {"slug": v["slug"], "name": v["name"]} for k, v in orgs.items()}}


def org_topics() -> dict:
    """All-time event-filing counts per exchange per topic, with the last
    filing date. Answers 'has this exchange ever filed in this topic', which a
    120-day window cannot: an exchange lists for years on one old filing."""
    orgs = json.loads((DATA / "cftc" / "orgs.json").read_text())["orgs"]
    out: dict[str, dict[str, dict]] = {k: {} for k in orgs}
    seen: set[int] = set()
    with (DATA / "cftc" / "products.jsonl").open() as f:
        for line in f:
            r = json.loads(line)
            if r.get("organization") not in orgs or r.get("category") != "Event" or r["id"] in seen:
                continue
            seen.add(r["id"])
            t = topic(r["product_name"])
            cell = out[r["organization"]].setdefault(t, {"count": 0, "last": ""})
            cell["count"] += 1
            cell["last"] = max(cell["last"], r["date"])
    return {"generated": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"), "orgs": out}


def kalshi_series(day_file: Path) -> dict:
    series: dict[str, dict] = defaultdict(lambda: {"markets": 0, "volume_24h": 0.0, "top": []})
    with gzip.open(day_file, "rt") as f:
        for line in f:
            m = json.loads(line)
            ev = m.get("event") or {}
            key = ev.get("series_ticker") or m["event_ticker"].split("-")[0]
            s = series[key]
            if "topic" not in s:
                s["topic"] = topic(key, ev.get("title"), m.get("title"))
                s["category"] = ev.get("category")
                s["title"] = ev.get("title")
            v = _num(m.get("volume_24h_fp"))
            s["markets"] += 1
            s["volume_24h"] += v
            s["top"].append((v, m["ticker"], m.get("title") or "", ev.get("title") or ""))
    out = {}
    for k, s in series.items():
        if s["volume_24h"] <= 0:
            continue  # a series with no trades in the window adds nothing a reader can use
        s["top"] = [{"ticker": t, "title": ti, "event": et, "volume_24h": round(v)} for v, t, ti, et in sorted(s["top"], reverse=True)[:3] if v > 0]
        s["volume_24h"] = round(s["volume_24h"])
        s["sport"] = is_sport(s["topic"])
        out[k] = s
    return {"snapshot": day_file.name.split(".")[0], "series": out}


def effective_topic(key: str, s: dict) -> str:
    """A series' topic as of the current rule list. A series stored as Other or
    Other sports is re-read with the ticker and event title it was stored with,
    so a new rule applies to days already in git without rewriting them. A
    topic that was already mapped is kept: the stored label was derived with
    the market title too, which the series file does not carry."""
    stored = s["topic"]
    if stored in ("Other", "Other sports"):
        t = topic(key, s.get("title"))
        if t != "Other":
            return t
    return stored


def kalshi_week(n_days: int = 7, top_per_topic: int = 10) -> dict:
    """Kalshi volume by topic over the last n daily snapshots (the sum of each
    day's 24-hour volume), and the busiest markets per topic on the latest
    day. Small enough for a page to read on every render.

    Also on the latest day: markets_by_topic, volume_by_topic_last_day and the
    topic map's health (sports_other_share, sports_other_top; see the module
    docstring). sports_other_share is None when the latest day has no sports
    volume, which fails the gate: absent is not zero."""
    files = sorted((OUT / "kalshi-series").glob("2*.json"))[-n_days:]
    totals: dict[str, float] = defaultdict(float)
    latest_top: dict[str, list] = defaultdict(list)
    markets: dict[str, int] = defaultdict(int)
    last_vol: dict[str, float] = defaultdict(float)
    sports_total = 0.0
    other: list[dict] = []
    for i, f in enumerate(files):
        d = json.loads(f.read_text())
        last = i == len(files) - 1
        for key, s in d["series"].items():
            t = effective_topic(key, s)
            totals[t] += s["volume_24h"]
            if last:
                markets[t] += s["markets"]
                last_vol[t] += s["volume_24h"]
                for m in s["top"]:
                    latest_top[t].append({**m, "series": key})
                if s.get("category") == "Sports":
                    sports_total += s["volume_24h"]
                    if t == "Other":
                        other.append({"series": key, "title": s.get("title"), "volume_24h": s["volume_24h"]})
    other.sort(key=lambda r: (-r["volume_24h"], r["series"]))
    share = round(sum(r["volume_24h"] for r in other) / sports_total, 4) if sports_total > 0 else None
    return {
        "generated": utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "days": [f.name.split(".")[0] for f in files],
        "volume_by_topic": {k: round(v) for k, v in totals.items()},
        "markets_by_topic": dict(markets),
        "volume_by_topic_last_day": {k: round(v) for k, v in last_vol.items()},
        "sports_other_share": share,
        "sports_other_top": other[:10],
        "top_by_topic": {k: sorted(v, key=lambda m: -m["volume_24h"])[:top_per_topic] for k, v in latest_top.items()},
    }


def gate_passes(share: float | None) -> bool:
    return share is not None and share <= GATE_MAX_OTHER_SHARE


def pin_week(monday: str) -> dict:
    """Freeze the three daily files under weeks/<monday>/ if this week has no
    folder yet and the gate passes. Returns the run-record fields. Never touches
    an existing folder; latest.json changes only when a folder is written."""
    kw = json.loads((OUT / "kalshi-week.json").read_text())
    share = kw.get("sports_other_share")
    weeks = OUT / "weeks"
    final = weeks / monday
    if final.exists():
        return {"source": "live", "week_written": False, "week_reason": "exists", "week": monday, "sports_other_share": share}
    if not gate_passes(share):
        return {"source": "gate_failed", "week_written": False, "week_reason": "gate", "week": monday, "sports_other_share": share}
    tmp = weeks / f"{monday}.tmp"  # built beside the final name, renamed in one step, so a killed run never leaves a partial week
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)
    for name in DAILY_FILES:
        shutil.copyfile(OUT / name, tmp / name)
    fr = json.loads((OUT / "filings-recent.json").read_text())
    meta = {"monday": monday, "generated": kw["generated"], "filings_generated": fr["generated"], "kalshi_days": kw["days"], "sports_other_share": share}
    (tmp / "meta.json").write_bytes(json.dumps(meta, ensure_ascii=False, sort_keys=True).encode())
    tmp.rename(final)
    write_atomic(weeks / "latest.json", json.dumps({"monday": monday}).encode())
    return {"source": "live", "week_written": True, "week_reason": "written", "week": monday, "sports_other_share": share}


def main() -> int:
    started = utcnow()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        fr = filings_recent()
        write_atomic(OUT / "filings-recent.json", json.dumps(fr, ensure_ascii=False, sort_keys=True).encode())
        write_atomic(OUT / "org-topics.json", json.dumps(org_topics(), ensure_ascii=False, sort_keys=True).encode())
        days = sorted((RECORD / "kalshi" / "listings").glob("*.jsonl.gz"))
        written = 0
        for d in days:
            target = OUT / "kalshi-series" / f"{d.name.split('.')[0]}.json"
            write_atomic(target, json.dumps(kalshi_series(d), ensure_ascii=False, sort_keys=True).encode())
            written += 1
        write_atomic(OUT / "kalshi-week.json", json.dumps(kalshi_week(), ensure_ascii=False, sort_keys=True).encode())
        idx = sorted(p.name.split(".")[0] for p in (OUT / "kalshi-series").glob("*.json") if p.name != "index.json")
        write_atomic(OUT / "kalshi-series" / "index.json", json.dumps({"days": idx}).encode())
        pin = pin_week(iso_monday(utcnow().date()))
        counts = {"filings": len(fr["rows"]), "kalshi_days_written": written, **{k: v for k, v in pin.items() if k != "source"}}
        record_run("summaries", source=pin["source"], counts=counts, started=started)
        return 0
    except Exception as e:  # noqa: BLE001
        record_run("summaries", source="unavailable", counts={}, note=repr(e), started=started)
        return 1


if __name__ == "__main__":
    sys.exit(main())
