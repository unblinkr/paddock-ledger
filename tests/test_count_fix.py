"""Filings are counted once, on the day they were first filed; Rothera's event
contracts count; a week folder is replaced only by --repin with a reason.

The fixture holds six real lines copied from data/cftc/products.jsonl:
  63035  DKeX  Event, Certified 2026-08-20, then Withdrawn 2026-10-21 (two lines)
  65288  Kalshi Event, Certified 2026-10-16
  65312  Rothera "Financial Instrument": "Will the Chicago Bulls win ... Event Contract", 2026-10-16
  41865  Rothera 2019 "USD-BTC Day-Ahead Swaps" (LedgerX; not an event contract)
  60439  Crypto.com "Solana Event Contract", "Financial Instrument", 2026-04-11
"""

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

import pytest  # noqa: E402

import summaries  # noqa: E402
import topics  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "cftc-count-fix-lines.jsonl"
ORGS = {"orgs": {
    "REX": {"slug": "dkex", "name": "DKeX"},
    "KEX": {"slug": "kalshi", "name": "Kalshi"},
    "ROTHDCM": {"slug": "rothera", "name": "Rothera"},
    "CDNA": {"slug": "cdna", "name": "Crypto.com"},
}}


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    d = tmp_path / "cftc"
    d.mkdir()
    (d / "orgs.json").write_text(json.dumps(ORGS))
    shutil.copy(FIXTURE, d / "products.jsonl")
    monkeypatch.setattr(summaries, "DATA", tmp_path)
    monkeypatch.setattr(summaries, "utcnow", lambda: datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc))
    return tmp_path


def _by_id(fr):
    return {r["id"]: r for r in fr["rows"]}


def test_withdrawal_counts_once_on_the_first_date(ledger):
    rows = [r for r in summaries.filings_recent(120)["rows"] if r["id"] == 63035]
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-08-20"
    assert rows[0]["status"] == "Withdrawn"


def test_withdrawal_of_an_older_filing_is_not_new_in_the_window(ledger):
    ids = _by_id(summaries.filings_recent(10))  # cutoff 2026-10-16; the withdrawal line is dated 2026-10-21
    assert 63035 not in ids
    assert 65288 in ids


def test_rothera_event_contract_filed_as_financial_instrument_is_counted(ledger):
    r = _by_id(summaries.filings_recent(10))[65312]
    assert r["platform"] == "rothera"
    assert r["topic"] == "Other"  # the topic rules read league names; "Bulls" is not one (follow-up, not this task)
    assert topics.is_event_contract({"category": "Financial Instrument", "product_name": "Will the Bulls win? Event Contract"})
    assert topics.is_event_contract({"category": "Financial Instrument", "product_name": "Solana Event Contract"})


def test_old_rothera_bitcoin_swaps_are_not_event_contracts(ledger):
    assert not topics.is_event_contract({"category": "Financial Instrument", "product_name": "USD-BTC Day-Ahead Swaps"})
    cells = summaries.org_topics()["orgs"]["ROTHDCM"]
    assert cells == {"Other": {"count": 1, "last": "2026-10-16"}}  # the 2019 swap row is not in it


def test_org_topics_counts_crypto_com_event_contract_once(ledger):
    cdna = summaries.org_topics()["orgs"]["CDNA"]
    assert cdna == {"Crypto": {"count": 1, "last": "2026-04-11"}}
    assert summaries.org_topics()["orgs"]["REX"]["College football"] == {"count": 1, "last": "2026-08-20"}


def _week(out, monday="2026-10-26", pinned_share=0.011):
    """A pinned week with an old filings summary, and a daily Kalshi file whose
    share is different (0.5) so a test can tell which one the re-pin used."""
    (out / "weeks" / monday).mkdir(parents=True)
    for name in summaries.DAILY_FILES:
        (out / "weeks" / monday / name).write_text("old")
    pinned = json.dumps({"generated": "2026-10-26T05:43:44Z", "days": ["2026-10-26"], "sports_other_share": pinned_share})
    (out / "weeks" / monday / "kalshi-week.json").write_text(pinned)
    (out / "weeks" / monday / "meta.json").write_text(json.dumps({"monday": monday, "generated": "2026-10-26T05:43:44Z"}))
    (out / "weeks" / "latest.json").write_text(json.dumps({"monday": monday}))
    (out / "kalshi-week.json").write_text(json.dumps({"generated": "2026-10-26T20:00:00Z", "days": ["2026-10-26"], "sports_other_share": 0.5}))
    (out / "filings-recent.json").write_text(json.dumps({"generated": "2026-10-26T20:00:01Z", "rows": []}))
    (out / "org-topics.json").write_text(json.dumps({"generated": "2026-10-26T20:00:02Z", "orgs": {}}))


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(summaries, "OUT", tmp_path)
    return tmp_path


def test_repin_replaces_the_filings_files_keeps_kalshi_and_records_why(out):
    _week(out)
    r = summaries.repin_week("2026-10-26", "count each filing once")
    assert r["source"] == "live" and r["week_reason"] == "repinned" and r["repin"] == "2026-10-26"
    meta = json.loads((out / "weeks" / "2026-10-26" / "meta.json").read_text())
    assert meta["repinned"]["reason"] == "count each filing once"
    assert meta["repinned"]["previous_generated"] == "2026-10-26T05:43:44Z"
    assert meta["generated"] == "2026-10-26T05:43:44Z"  # the pinned Kalshi stamp, kept
    assert (out / "weeks" / "2026-10-26" / "org-topics.json").read_text() != "old"
    assert (out / "weeks" / "2026-10-26" / "filings-recent.json").read_text() != "old"
    assert json.loads((out / "weeks" / "2026-10-26" / "kalshi-week.json").read_text())["generated"] == "2026-10-26T05:43:44Z"
    assert json.loads((out / "weeks" / "latest.json").read_text()) == {"monday": "2026-10-26"}
    left = sorted(p.name for p in (out / "weeks").iterdir())
    assert left == ["2026-10-26", "latest.json"]  # no .old, .tmp or kept-file leftovers


def test_plain_run_still_never_rewrites_an_existing_week(out):
    _week(out)
    before = (out / "weeks" / "2026-10-26" / "meta.json").read_bytes()
    r = summaries.pin_week("2026-10-26")
    assert r["week_written"] is False and r["week_reason"] == "exists"
    assert (out / "weeks" / "2026-10-26" / "meta.json").read_bytes() == before
    assert (out / "weeks" / "2026-10-26" / "org-topics.json").read_text() == "old"


def test_repin_does_nothing_when_the_pinned_gate_fails_or_the_week_is_missing(out):
    _week(out, pinned_share=0.5)
    assert summaries.repin_week("2026-10-26", "x")["source"] == "gate_failed"
    assert (out / "weeks" / "2026-10-26" / "org-topics.json").read_text() == "old"
    assert sorted(p.name for p in (out / "weeks").iterdir()) == ["2026-10-26", "latest.json"]
    with pytest.raises(ValueError):
        summaries.repin_week("2026-11-02", "x")


def test_repin_without_reason_exits_nonzero_and_writes_nothing(tmp_path, monkeypatch):
    target = tmp_path / "summaries"
    monkeypatch.setattr(summaries, "OUT", target)
    with pytest.raises(SystemExit) as e:
        summaries.main(["--repin", "2026-10-26"])
    assert e.value.code != 0
    with pytest.raises(SystemExit) as e2:
        summaries.main(["--reason", "x"])
    assert e2.value.code != 0
    assert not target.exists()
