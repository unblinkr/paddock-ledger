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

No fetches. Reads data/cftc/*.jsonl and data/kalshi/listings/*.jsonl.gz.
"""

from __future__ import annotations

import gzip
import json
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from common import DATA, record_run, utcnow, write_atomic
from topics import is_sport, topic

OUT = DATA / "summaries"


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


def main() -> int:
    started = utcnow()
    OUT.mkdir(parents=True, exist_ok=True)
    try:
        fr = filings_recent()
        write_atomic(OUT / "filings-recent.json", json.dumps(fr, ensure_ascii=False, sort_keys=True).encode())
        write_atomic(OUT / "org-topics.json", json.dumps(org_topics(), ensure_ascii=False, sort_keys=True).encode())
        days = sorted((DATA / "kalshi" / "listings").glob("*.jsonl.gz"))
        written = 0
        for d in days:
            target = OUT / "kalshi-series" / f"{d.name.split('.')[0]}.json"
            write_atomic(target, json.dumps(kalshi_series(d), ensure_ascii=False, sort_keys=True).encode())
            written += 1
        idx = sorted(p.name.split(".")[0] for p in (OUT / "kalshi-series").glob("*.json") if p.name != "index.json")
        write_atomic(OUT / "kalshi-series" / "index.json", json.dumps({"days": idx}).encode())
        record_run("summaries", source="live", counts={"filings": len(fr["rows"]), "kalshi_days_written": written}, started=started)
        return 0
    except Exception as e:  # noqa: BLE001
        record_run("summaries", source="unavailable", counts={}, note=repr(e), started=started)
        return 1


if __name__ == "__main__":
    sys.exit(main())
