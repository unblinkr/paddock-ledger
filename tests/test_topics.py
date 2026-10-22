"""Topic rules: the series named in the 2026-10-22 weekly-pin brief map to their sport,
and the new rules move nothing that was already labelled."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))

import pytest  # noqa: E402

from topics import topic  # noqa: E402

# (series ticker, event title, expected topic). From the Oct 22 Kalshi listings.
NEW = [
    ("KXDPWORLDTOUR", "Genesis Championship Winner", "Golf"),
    ("KXDPWORLDTOURR1LEAD", "Genesis Championship End of Round 1 Leader", "Golf"),
    ("KXCHAMPTOUR", "Stifel Charity Classic Winner", "Golf"),
    ("KXTESTMATCH", "New Zealand A vs India A", "Cricket"),
    ("KXODIMATCH", "Namibia vs Ireland", "Cricket"),
    ("KXWODIMATCH", "India vs Zimbabwe", "Cricket"),
    ("KXWT20MATCH", "Sydney Thunder Women vs Perth Scorchers Women", "Cricket"),
    ("KXUELGAME", "Torreense vs Ararat-Armenia", "Soccer"),
    ("KXUECLGAME", "Enschede vs Pafos", "Soccer"),
    ("KXUELSCORE", "FC Viktoria Plzen vs PFC Levski Sofia: Correct Score", "Soccer"),
    ("KXLIGAMXGAME", "Cruz Azul vs Leon", "Soccer"),
    ("KXARGPREMDIVGAME", "Union Santa Fe vs Estudiantes La Plata", "Soccer"),
    ("KXBRASILEIROGAME", "Palmeiras vs Remo", "Soccer"),
    ("KXUELTOTAL", "Plzen vs Levski Sofia: Total Goals", "Soccer"),
    ("KXUECLSCORE", "FC Thun vs HNK Hajduk Split: Correct Score", "Soccer"),
    ("KXUECLSPREAD", "Thun vs Hajduk: Spread", "Soccer"),
    ("KXUECLTOTAL", "Thun vs Hajduk: Total Goals", "Soccer"),
    ("KXUECLBTTS", "Thun vs Hajduk: BTTS", "Soccer"),
    ("KXUELBTTS", "Plzen vs Levski Sofia: BTTS", "Soccer"),
    ("KXIDNSLBTTS", "Madura United vs Persib Bandung: BTTS", "Soccer"),
    ("KXCONMEBOLLIBGAME", "Flamengo vs Estudiantes La Plata: Regulation Time Moneyline", "Soccer"),
    ("KXNEXTTEAMNFL", "Josh Allen's Next Team", "NFL"),
    ("KXNFLLASTTOLOSE", "Last undefeated team", "NFL"),
    ("KXNEXTTEAMNBA", "Jayson Tatum's Next Team", "NBA"),
    ("KXNBALASTTOLOSE", "Last undefeated team", "NBA"),
    ("KXNEXTTEAMNHL", "Zach Werenski's Next Team", "NHL"),
    ("KXKBLGAME", "Samsung Thunders vs Daegu Pegasus", "Other basketball"),
    ("KXLIGAPROMATCH", "Klimentev Vladimir vs CHagaev Aleksei", "Table tennis"),
]


@pytest.mark.parametrize("ticker,title,expected", NEW)
def test_new_series_map_to_their_sport(ticker, title, expected):
    assert topic(ticker, title) == expected


def test_company_names_with_brasileiro_are_not_soccer():
    assert topic("Petroleo Brasileiro S.A. ADR") == "Other"
    assert topic("Cia Brasileira de Distribuicao SA") == "Other"


def test_existing_labels_do_not_move():
    base = json.loads((ROOT / "tests" / "fixtures" / "topics-baseline.json").read_text())
    moved = [(n, t, topic(n)) for n, t in base["filings"].items() if topic(n) != t]
    moved += [(k, o, topic(k, title)) for k, title, o in base["series"] if topic(k, title) != o]
    assert moved == []
