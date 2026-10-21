"""Where the record goes.

The platform record (hourly books under books/, daily listings, settlements
and combo collections under record/) is never committed. It goes to
Cloudflare R2 when the four R2_* secrets are set. When they are not, the
workflow keeps the run's files as a GitHub Actions artifact instead (90-day
retention) and the run record says so, so nothing is lost before the keys
exist and a missing upload is never silent. The CFTC ledger, the platform
registry, the summaries and the run records stay in git.

Usage:
  python collectors/store.py books            uploads every file under books/
  python collectors/store.py record           uploads every file under record/
  python collectors/store.py --migrate-legacy uploads the snapshots that were
      committed under data/<platform>/{listings,settlements,combos}/ before
      2026-10-21 to the same keys they would have under record/, and writes
      the manifest (every file, its size) to the run record. Nothing is
      deleted; removing them from git is a separate, reviewed commit.

The R2 key is the path relative to the repository root (books/... or
record/...), so a file has the same name in git history, on disk and on R2.

Exit 0 when uploaded, 3 when R2 is not configured (the workflow then uploads
the artifact), 1 on an upload error.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from common import DATA, REPO, record_run, utcnow

R2_VARS = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET")
LEGACY_KINDS = ("listings", "settlements", "combos")


def r2_configured() -> bool:
    return all(os.environ.get(v) for v in R2_VARS)


def _client():
    import boto3  # installed by the workflow only when R2 is configured

    account = os.environ["R2_ACCOUNT_ID"]
    return boto3.client(
        "s3",
        endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )


def _upload(s3, bucket: str, pairs: list[tuple[Path, str]]) -> dict:
    n = 0
    total = 0
    for p, key in pairs:
        s3.upload_file(str(p), bucket, key, ExtraArgs={"ContentType": "application/gzip"})
        n += 1
        total += p.stat().st_size
    return {"files": n, "bytes": total, "bucket_set": True}


def upload_dir(root: Path) -> dict:
    pairs = [(p, str(p.relative_to(root.parent)).replace(os.sep, "/")) for p in sorted(root.rglob("*.jsonl.gz"))]
    return _upload(_client(), os.environ["R2_BUCKET"], pairs)


def legacy_files() -> list[tuple[Path, str]]:
    """The snapshots committed under data/ before the record moved to R2, with the
    record/ key each one gets. Only the three snapshot kinds; never data/cftc,
    data/platforms, data/runs or data/summaries."""
    pairs: list[tuple[Path, str]] = []
    for platform_dir in sorted(DATA.iterdir()) if DATA.exists() else []:
        if not platform_dir.is_dir() or platform_dir.name in ("cftc", "platforms", "runs", "summaries"):
            continue
        for kind in LEGACY_KINDS:
            for p in sorted((platform_dir / kind).glob("*.jsonl.gz")):
                pairs.append((p, f"record/{platform_dir.name}/{kind}/{p.name}"))
    return pairs


def migrate_legacy() -> int:
    started = utcnow()
    pairs = legacy_files()
    manifest = [{"path": str(p.relative_to(REPO)), "key": key, "bytes": p.stat().st_size} for p, key in pairs]
    if not pairs:
        record_run("store:migrate-legacy", source="live", counts={"files": 0, "manifest": []}, note="no legacy snapshots under data/", started=started)
        return 0
    if not r2_configured():
        record_run("store:migrate-legacy", source="unavailable", counts={"files": len(pairs), "manifest": manifest}, note="R2 not configured; nothing uploaded, nothing removed", started=started)
        return 3
    try:
        counts = _upload(_client(), os.environ["R2_BUCKET"], pairs)
    except Exception as e:  # noqa: BLE001
        record_run("store:migrate-legacy", source="unavailable", counts={"files": len(pairs), "manifest": manifest}, note=f"R2 upload failed: {type(e).__name__}", started=started, store="r2")
        return 1
    record_run("store:migrate-legacy", source="live", counts={**counts, "manifest": manifest}, started=started, store="r2")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] == "--migrate-legacy":
        return migrate_legacy()
    name = (args or ["books"])[0]
    root = Path(name).resolve()
    started = utcnow()
    files = sorted(root.rglob("*.jsonl.gz")) if root.exists() else []
    if not files:
        record_run("store", source="unavailable", counts={"files": 0, "root": root.name}, note=f"no files to store under {root.name}/", started=started)
        return 1
    if not r2_configured():
        record_run("store", source="live", counts={"files": len(files), "root": root.name}, note="R2 not configured; run kept as an Actions artifact", started=started, store="actions_artifact")
        return 3
    try:
        counts = upload_dir(root)
    except Exception as e:  # noqa: BLE001
        record_run("store", source="unavailable", counts={"files": len(files), "root": root.name}, note=f"R2 upload failed: {type(e).__name__}", started=started, store="r2")
        return 1
    record_run("store", source="live", counts={**counts, "root": root.name}, started=started, store="r2")
    return 0


if __name__ == "__main__":
    sys.exit(main())
