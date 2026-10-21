"""Novig (Ludlow Exchange): the two daily exchange files Novig publishes.

Source: https://data.novig.com/reporting/trade-data/ (docs:
https://docs.novig.com/public-data/overview.md). Public static files behind
CloudFront, no key, no account.

  index.json                 the manifest: `dates` (days with a trades file)
                             and `marketDates` (days with a markets file);
                             a missing `marketDates` reads as an empty list
  <date>/trades.csv          every executed trade that day, anonymized
  <date>/markets.csv         every market that day: open interest, daily
                             volume, open/high/low/close, status

Verified 2026-10-21: the manifest listed 79 trade days (2026-08-03 to
2026-10-20) and 78 market days (2026-08-04 to 2026-10-20). One day is
midnight to midnight Eastern and publishes around 09:06 UTC the next morning.
A trades file is about 130 MB and 860,000 rows; a markets file about 15 MB
and 160,000 rows. Every response carries an ETag (S3); HEAD is answered.
Novig says past files do not change except for an announced correction,
which republishes the date in place, and that columns may be added, so the
header row is read rather than assumed.

What this collector keeps: the file exactly as served, gzipped, never parsed
into rows and never rewritten. A file is identified by (kind, date, ETag).
A date seen for the first time is written as
`record/novig/<kind>/<date>.csv.gz`; a date whose ETag later changes (a
correction) is written as a NEW file `record/novig/<kind>/<date>.<etag8>.csv.gz`
beside the first, so both versions are kept. `data/novig/etags.json` is the
public list of (kind, date, ETag, bytes) already captured; it holds no
data, and the workflow commits it only after the upload to R2 succeeds.

Combos: Novig's trades file includes parlay legs (`tradeType` COMBO, with
`contractSeries` Parlay). They stay in the file as served; the run record
counts them per file (rule 6: counted, never mixed into anything derived).

Pacing: one request a second. HEAD for every listed file each run (about
160 requests), GET only for what is new or changed. A run downloads at most
`--max-files` files (default 60, about 4.5 GB) so the first backfill spreads
over a few days instead of one long job; the run record says how many are
still pending.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from common import DATA, RECORD, REPO, USER_AGENT, record_run, utcnow

BASE = "https://data.novig.com/reporting/trade-data"
SLUG = "novig"
KINDS = ("trades", "markets")
STATE = DATA / SLUG / "etags.json"
MIN_INTERVAL_S = 1.0
TRIES = 6


class Paced:
    def __init__(self) -> None:
        self._last = 0.0
        self.requests = 0
        self.retries = 0

    def _req(self, url: str, method: str):
        for attempt in range(TRIES):
            wait = MIN_INTERVAL_S - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.requests += 1
            try:
                return urllib.request.urlopen(urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT}), timeout=120)
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < TRIES - 1:
                    self.retries += 1
                    time.sleep(min(60, 3 * (attempt + 1) ** 2))
                    continue
                raise
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if attempt < TRIES - 1:
                    self.retries += 1
                    time.sleep(min(60, 3 * (attempt + 1) ** 2))
                    continue
                raise
        raise RuntimeError(f"gave up {url}")

    def json(self, url: str):
        with self._req(url, "GET") as r:
            return json.loads(r.read().decode("utf-8"))

    def head(self, url: str) -> dict:
        with self._req(url, "HEAD") as r:
            return {"etag": (r.headers.get("ETag") or "").strip('"'), "bytes": int(r.headers.get("Content-Length") or 0),
                    "last_modified": r.headers.get("Last-Modified")}

    def fetch_to_gz(self, url: str, path: Path) -> dict:
        """Stream the body into a gzip file, byte for byte. Counts rows and combo rows
        on the way through without changing what is written."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        raw = 0
        with self._req(url, "GET") as r, gzip.open(tmp, "wb", compresslevel=6) as gz:
            etag = (r.headers.get("ETag") or "").strip('"')
            declared = int(r.headers.get("Content-Length") or 0)
            counter = RowCounter()
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                gz.write(chunk)
                counter.feed(chunk)
                raw += len(chunk)
        counter.close()
        if declared and raw != declared:
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"short read {url}: {raw} of {declared} bytes")
        os.replace(tmp, path)
        return {"etag": etag, "bytes": raw, "bytes_gz": path.stat().st_size, "rows": counter.rows,
                "combo_rows": counter.combo_rows, "columns": counter.header}


class RowCounter:
    """Counts data rows, and rows whose tradeType is COMBO when that column exists.
    Reads the header row (columns may be added); never alters the bytes."""

    def __init__(self) -> None:
        self._buf = b""
        self.header: list[str] | None = None
        self._combo_ix: int | None = None
        self.rows = 0
        self.combo_rows = 0

    def _line(self, line: bytes) -> None:
        if not line.strip():
            return
        fields = next(csv.reader([line.decode("utf-8", "replace")]))
        if self.header is None:
            self.header = fields
            self._combo_ix = fields.index("tradeType") if "tradeType" in fields else None
            return
        self.rows += 1
        if self._combo_ix is not None and len(fields) > self._combo_ix and fields[self._combo_ix] == "COMBO":
            self.combo_rows += 1

    def feed(self, chunk: bytes) -> None:
        self._buf += chunk
        *lines, self._buf = self._buf.split(b"\n")
        for line in lines:
            self._line(line)

    def close(self) -> None:
        if self._buf:
            self._line(self._buf)
            self._buf = b""


def manifest_files(index: dict) -> list[tuple[str, str]]:
    """(kind, date) for every file the manifest lists, oldest first."""
    out = [("trades", d) for d in index.get("dates") or []]
    out += [("markets", d) for d in index.get("marketDates") or []]
    return sorted(out, key=lambda kd: (kd[1], kd[0]))


def load_state(path: Path = STATE) -> dict:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"files": []}


def plan(listed: list[tuple[str, str]], heads: dict[tuple[str, str], dict], state: dict) -> list[dict]:
    """What to download: a (kind, date) never captured, or one whose ETag is new.
    Returns items with the target file name; earlier versions are never touched."""
    seen: dict[tuple[str, str], set[str]] = {}
    for f in state.get("files", []):
        seen.setdefault((f["kind"], f["date"]), set()).add(f["etag"])
    todo = []
    for kind, date in listed:
        h = heads.get((kind, date))
        if not h:
            continue
        etags = seen.get((kind, date), set())
        if h["etag"] in etags:
            continue
        name = f"{date}.csv.gz" if not etags else f"{date}.{h['etag'][:8]}.csv.gz"
        todo.append({"kind": kind, "date": date, "etag": h["etag"], "name": name, "correction": bool(etags)})
    return todo


def run(max_files: int) -> int:
    started = utcnow()
    http = Paced()
    try:
        index = http.json(f"{BASE}/index.json")
    except Exception as e:  # noqa: BLE001
        record_run(f"{SLUG}:daily", source="unavailable", counts={}, note=f"manifest: {e!r}", started=started)
        return 1
    listed = manifest_files(index)
    heads: dict[tuple[str, str], dict] = {}
    head_failures: list[str] = []
    for kind, date in listed:
        try:
            heads[(kind, date)] = http.head(f"{BASE}/{date}/{kind}.csv")
        except Exception as e:  # noqa: BLE001
            head_failures.append(f"{kind}/{date}: {type(e).__name__}")
    state = load_state()
    todo = plan(listed, heads, state)
    this_run, pending = todo[:max_files], todo[max_files:]
    captured: list[dict] = []
    failures: list[str] = []
    for item in this_run:
        path = RECORD / SLUG / item["kind"] / item["name"]
        try:
            got = http.fetch_to_gz(f"{BASE}/{item['date']}/{item['kind']}.csv", path)
        except Exception as e:  # noqa: BLE001
            failures.append(f"{item['kind']}/{item['date']}: {e!r}"[:200])
            continue
        if got["etag"] and got["etag"] != item["etag"]:
            # The file changed between HEAD and GET; keep what was served under its own ETag.
            item = {**item, "etag": got["etag"]}
        captured.append({"kind": item["kind"], "date": item["date"], "etag": item["etag"], "bytes": got["bytes"],
                         "file": str(path.relative_to(REPO)) if path.is_relative_to(REPO) else str(path),
                         "correction": item["correction"], "rows": got["rows"], "combo_rows": got["combo_rows"],
                         "columns": got["columns"]})
    if captured:
        state["files"] = state.get("files", []) + [{k: c[k] for k in ("kind", "date", "etag", "bytes")} for c in captured]
        state["files"].sort(key=lambda f: (f["date"], f["kind"], f["etag"]))
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    counts = {
        "manifest_trade_days": len(index.get("dates") or []),
        "manifest_market_days": len(index.get("marketDates") or []),
        "newest_date": max((d for _, d in listed), default=None),
        "files_listed": len(listed),
        "files_new_or_changed": len(todo),
        "files_captured": len(captured),
        "files_pending": len(pending),
        "corrections_captured": sum(1 for c in captured if c["correction"]),
        "max_files": max_files,
        "head_failures": head_failures,
        "download_failures": failures,
        "captured": [{k: c[k] for k in ("kind", "date", "etag", "bytes", "rows", "combo_rows", "file")} for c in captured],
        "columns": {c["kind"]: c["columns"] for c in captured},
    }
    # A capped backfill is by design (files_pending says how many are left); only a failed HEAD or GET is partial.
    source = "live" if not (head_failures or failures) else "partial"
    record_run(f"{SLUG}:daily", source=source, counts=counts, started=started, store="record")
    if http.requests:
        print(json.dumps({"requests": http.requests, "retries": http.retries}), file=sys.stderr)
    return 0 if source == "live" else 2


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--max-files", type=int, default=60)
    a = ap.parse_args(argv)
    return run(a.max_files)


if __name__ == "__main__":
    sys.exit(main())
