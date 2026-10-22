"""kalshi_week topic-map health, the Monday pin and the gate, on a two-day fixture."""

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

import pytest  # noqa: E402

import common  # noqa: E402
import health  # noqa: E402
import summaries  # noqa: E402


def _series(vol, topic="Soccer", category="Sports", markets=2, title="t"):
    return {"category": category, "markets": markets, "sport": True, "title": title, "topic": topic, "volume_24h": vol,
            "top": [{"event": "e", "ticker": "T-1", "title": "m", "volume_24h": vol}]}


def _write_day(out, day, series):
    p = out / "kalshi-series" / f"{day}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"snapshot": day, "series": series}))


@pytest.fixture
def out(tmp_path, monkeypatch):
    monkeypatch.setattr(summaries, "OUT", tmp_path)
    return tmp_path


def _two_days(out, other_vol):
    _write_day(out, "2026-10-21", {"KXA": _series(1000, "Other", title="old")})
    _write_day(out, "2026-10-22", {
        "KXGOLF": _series(9000, "Golf", markets=3),
        "KXODD": _series(other_vol, "Other", markets=5, title="Odd event"),
        "KXES": _series(500, "Esports", markets=4),
        "KXPOL": _series(7777, "Elections and politics", category="Elections"),
    })


def test_iso_monday():
    assert common.iso_monday(date(2026, 10, 22)) == "2026-10-19"  # Thursday
    assert common.iso_monday(date(2026, 10, 26)) == "2026-10-26"  # Monday maps to itself
    assert common.iso_monday(date(2026, 10, 25)) == "2026-10-19"  # Sunday


def test_kalshi_week_health_fields(out):
    _two_days(out, 100)
    kw = summaries.kalshi_week()
    assert kw["days"] == ["2026-10-21", "2026-10-22"]
    assert kw["markets_by_topic"]["Esports"] == 4
    assert kw["markets_by_topic"]["Golf"] == 3
    assert kw["volume_by_topic_last_day"]["Golf"] == 9000
    assert kw["volume_by_topic"]["Other"] == 1100  # sum across days stays
    assert kw["sports_other_share"] == round(100 / 9600, 4)  # non-sports category excluded
    assert kw["sports_other_top"] == [{"series": "KXODD", "title": "Odd event", "volume_24h": 100}]
    assert kw["generated"].endswith("Z")


def test_other_sports_counts_as_mapped(out):
    _write_day(out, "2026-10-22", {"KXG": _series(900, "Golf"), "KXR": _series(100, "Other sports")})
    assert summaries.kalshi_week()["sports_other_share"] == 0.0


def test_rule_change_applies_to_stored_other(out):
    _write_day(out, "2026-10-22", {"KXDPWORLDTOUR": _series(100, "Other", title="Genesis Championship Winner"),
                                   "KXKEEP": _series(100, "Props", title="Football stat anchor")})
    kw = summaries.kalshi_week()
    assert kw["volume_by_topic_last_day"] == {"Golf": 100, "Props": 100}
    assert kw["sports_other_share"] == 0.0


def test_no_sports_volume_is_absent_not_zero(out):
    _write_day(out, "2026-10-22", {"KXPOL": _series(10, "Elections and politics", category="Elections")})
    kw = summaries.kalshi_week()
    assert kw["sports_other_share"] is None
    assert not summaries.gate_passes(None)


def test_gate_boundary():
    assert summaries.gate_passes(0.02)
    assert not summaries.gate_passes(0.0201)


def _daily(out, share, generated="2026-10-22T12:00:00Z"):
    (out / "filings-recent.json").write_text(json.dumps({"generated": generated, "rows": []}))
    (out / "org-topics.json").write_text(json.dumps({"generated": generated, "orgs": {}}))
    (out / "kalshi-week.json").write_text(json.dumps({"generated": generated, "days": ["2026-10-22"], "sports_other_share": share}))


def _tree(root):
    return {str(p.relative_to(root)): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def test_pin_writes_week_and_latest(out):
    _daily(out, 0.02)
    r = summaries.pin_week("2026-10-19")
    assert r["week_written"] is True and r["source"] == "live" and r["week"] == "2026-10-19"
    wk = out / "weeks" / "2026-10-19"
    for n in summaries.DAILY_FILES:
        assert (wk / n).read_bytes() == (out / n).read_bytes()
    meta = json.loads((wk / "meta.json").read_text())
    assert meta == {"monday": "2026-10-19", "generated": "2026-10-22T12:00:00Z", "filings_generated": "2026-10-22T12:00:00Z",
                    "kalshi_days": ["2026-10-22"], "sports_other_share": 0.02}
    assert json.loads((out / "weeks" / "latest.json").read_text()) == {"monday": "2026-10-19"}
    assert not list((out / "weeks").glob("*.tmp"))


def test_second_run_same_week_leaves_folder_byte_identical(out):
    _daily(out, 0.01)
    summaries.pin_week("2026-10-19")
    before = _tree(out / "weeks")
    _daily(out, 0.005, generated="2026-10-23T12:00:00Z")  # a later run, different data
    r = summaries.pin_week("2026-10-19")
    assert r["week_written"] is False and r["week_reason"] == "exists" and r["source"] == "live"
    assert _tree(out / "weeks") == before


def test_gate_failure_writes_no_folder_and_keeps_latest(out):
    _daily(out, 0.01)
    summaries.pin_week("2026-10-12")
    latest = (out / "weeks" / "latest.json").read_bytes()
    _daily(out, 0.0201)
    r = summaries.pin_week("2026-10-19")
    assert r["source"] == "gate_failed" and r["week_written"] is False and r["week_reason"] == "gate"
    assert not (out / "weeks" / "2026-10-19").exists()
    assert (out / "weeks" / "latest.json").read_bytes() == latest


def test_later_passing_run_pins_under_the_monday(out):
    _daily(out, 0.5)
    assert summaries.pin_week("2026-10-19")["source"] == "gate_failed"
    _daily(out, 0.01, generated="2026-10-20T12:00:00Z")
    assert summaries.pin_week("2026-10-19")["week_written"] is True
    meta = json.loads((out / "weeks" / "2026-10-19" / "meta.json").read_text())
    assert meta["monday"] == "2026-10-19" and meta["generated"] == "2026-10-20T12:00:00Z"


def test_health_week_and_gate_checks(tmp_path):
    from datetime import datetime, timezone
    early = datetime(2026, 10, 22, 8, 15, tzinfo=timezone.utc)
    late = datetime(2026, 10, 22, 14, 30, tzinfo=timezone.utc)
    assert health.week_problem(early, tmp_path) is None
    assert health.week_problem(late, tmp_path) == "2026-10-19"
    (tmp_path / "2026-10-19").mkdir()
    (tmp_path / "2026-10-19" / "meta.json").write_text("{}")
    assert health.week_problem(late, tmp_path) is None
    rows = [{"collector": "summaries", "source": "live", "finished": "2026-10-22T05:00:00Z"},
            {"collector": "summaries", "source": "gate_failed", "finished": "2026-10-22T06:00:00Z", "counts": {"sports_other_share": 0.0312}}]
    run = health.gate_problem(rows)
    title, body = health.gate_issue(run, {"sports_other_top": [{"series": "KXZ", "title": "Z", "volume_24h": 5}]}, "2026-10-22")
    assert title == "Kalshi topic map gate failed: 3.12% unmapped on 2026-10-22"
    assert "KXZ" in body
    assert health.gate_problem(rows[:1]) is None
