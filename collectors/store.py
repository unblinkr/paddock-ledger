"""Where the hourly books go.

Books are too large for git (Kalshi alone is about 2.5 MB gzipped an hour).
They go to Cloudflare R2 when the four R2_* secrets are set. When they are
not, the workflow keeps the hour as a GitHub Actions artifact instead (free
on a public repository, 90-day retention) and the run record says so, so a
missing hour is never silent and nothing is lost before the keys exist. A
backfill job moves artifact hours into R2 once the keys land.

Usage: python collectors/store.py books/   (uploads every file under books/)
Exit 0 when uploaded, 3 when R2 is not configured (the workflow then uploads
the artifact), 1 on an upload error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from common import record_run, utcnow

R2_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")


def r2_configured() -> bool:
    return all(os.environ.get(v) for v in R2_VARS)


def upload_dir(root: Path) -> dict:
    import boto3  # installed by the workflow only when R2 is configured

    account = os.environ["R2_ACCOUNT_ID"]
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    bucket = os.environ["R2_BUCKET"]
    n = 0
    total = 0
    for p in sorted(root.rglob("*.jsonl.gz")):
        key = str(p.relative_to(root.parent)).replace(os.sep, "/")
        s3.upload_file(str(p), bucket, key, ExtraArgs={"ContentType": "application/gzip"})
        n += 1
        total += p.stat().st_size
    return {"files": n, "bytes": total, "bucket_set": True}


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:] or ["books"])[0]).resolve()
    started = utcnow()
    files = sorted(root.rglob("*.jsonl.gz")) if root.exists() else []
    if not files:
        record_run("store", source="unavailable", counts={"files": 0}, note="no book files to store", started=started)
        return 1
    if not r2_configured():
        record_run("store", source="live", counts={"files": len(files)}, note="R2 not configured; hour kept as an Actions artifact", started=started, store="actions_artifact")
        return 3
    try:
        counts = upload_dir(root)
    except Exception as e:  # noqa: BLE001
        record_run("store", source="unavailable", counts={"files": len(files)}, note=f"R2 upload failed: {type(e).__name__}", started=started, store="r2")
        return 1
    record_run("store", source="live", counts=counts, started=started, store="r2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
