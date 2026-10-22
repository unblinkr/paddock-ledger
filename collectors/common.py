"""Shared plumbing for every collector.

Rules this module enforces, because every collector depends on them:

1. A fetch that fails is recorded, never hidden. Every run writes one line to
   data/runs/YYYY-MM-DD/<job>.jsonl with a `source` marker ("live" | "unavailable")
   and the counts it saw. A missing hour is visible in the run log before
   anyone looks at the data.
2. Every pagination cap is named and truncation is detected. A collector that
   pages must say what the page size was and whether it hit the last page.
   Assert the response, not the request: a server that ignores a parameter
   does not complain, it uses its default.
3. Requests are paced. Public APIs rate-limit bursts (Kalshi returns 429 at
   ~20 requests a second). One request a second with backoff on 429 is the
   default for every collector; nothing here is latency-sensitive.
4. Files are written atomically (temp file, then rename), so a killed run
   never leaves a half-written day.
5. Nothing is ever deleted or rewritten. Daily files are new files; the ledger
   is append-only with an id-keyed dedupe.
"""

from __future__ import annotations

import gzip
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
RECORD = REPO / "record"  # platform snapshots: written locally, uploaded to R2, never committed
RUNS = DATA / "runs"

USER_AGENT = "PaddockLedger/0.1 (+https://paddock.finance/venues; hello@paddock.finance)"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def stamp(dt: Optional[datetime] = None) -> str:
    return (dt or utcnow()).strftime("%Y-%m-%dT%H:%M:%SZ")


def day(dt: Optional[datetime] = None) -> str:
    return (dt or utcnow()).strftime("%Y-%m-%d")


def iso_monday(d: date) -> str:
    """The ISO Monday of the week containing d, as YYYY-MM-DD. A Monday maps to itself."""
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def hour(dt: Optional[datetime] = None) -> str:
    return (dt or utcnow()).strftime("%Y-%m-%dT%HZ")


class FetchError(Exception):
    pass


@dataclass
class Http:
    """Paced HTTP with retry on 429/5xx. One instance per collector."""

    min_interval_s: float = 1.0
    timeout_s: int = 60
    max_tries: int = 6
    requests_made: int = 0
    retries: int = 0
    _last: float = field(default=0.0, repr=False)

    def get(self, url: str, headers: Optional[dict[str, str]] = None) -> bytes:
        for attempt in range(self.max_tries):
            wait = self.min_interval_s - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})})
            self._last = time.monotonic()
            self.requests_made += 1
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_s) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_tries - 1:
                    self.retries += 1
                    time.sleep(min(60, 3 * (attempt + 1) ** 2))
                    continue
                raise FetchError(f"{e.code} {url}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                if attempt < self.max_tries - 1:
                    self.retries += 1
                    time.sleep(min(60, 3 * (attempt + 1) ** 2))
                    continue
                raise FetchError(f"{type(e).__name__} {url}") from e
        raise FetchError(f"gave up {url}")

    def get_json(self, url: str, headers: Optional[dict[str, str]] = None) -> Any:
        return json.loads(self.get(url, headers).decode("utf-8"))


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json_gz(path: Path, obj: Any) -> int:
    """Write gzip'd JSON with sorted keys so identical content gives identical bytes."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        gz.write(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    data = buf.getvalue()
    write_atomic(path, data)
    return len(data)


def write_jsonl_gz(path: Path, rows: Iterable[dict]) -> tuple[int, int]:
    buf = io.BytesIO()
    n = 0
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0) as gz:
        for row in rows:
            gz.write((json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8"))
            n += 1
    data = buf.getvalue()
    write_atomic(path, data)
    return n, len(data)


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def append_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
            n += 1
    return n


def record_run(collector: str, *, source: str, counts: dict[str, Any], note: str = "", http: Optional[Http] = None,
               started: Optional[datetime] = None, store: Optional[str] = None) -> dict:
    """One line per run in data/runs/YYYY-MM-DD.jsonl. `source` is the disclosure
    marker: "live" means the fetch succeeded and the data on disk is from this
    run; "unavailable" means it did not, and nothing was written for it. "gate_failed"
    (summaries only) means the daily files were written but the Kalshi topic map
    left too much sports volume unmapped, so no week folder was pinned."""
    assert source in ("live", "unavailable", "partial", "gate_failed")
    row = {
        "collector": collector,
        "started": stamp(started),
        "finished": stamp(),
        "source": source,
        "counts": counts,
    }
    if store:
        row["store"] = store
    if http:
        row["http"] = {"requests": http.requests_made, "retries": http.retries}
    if note:
        row["note"] = note[:500]
    # One file per job per day (RUN_LOG_NAME is set by each workflow), so two
    # jobs never append to the same file and a rebase never conflicts.
    append_jsonl(RUNS / day() / f"{os.environ.get('RUN_LOG_NAME', 'local')}.jsonl", [row])
    print(json.dumps(row, sort_keys=True), file=sys.stderr)
    return row


def platform_meta(slug: str) -> dict:
    """Static metadata for a platform, from data/platforms/platforms.json."""
    reg = json.loads((DATA / "platforms" / "platforms.json").read_text(encoding="utf-8"))
    for p in reg["platforms"]:
        if p["slug"] == slug:
            return p
    raise KeyError(slug)
