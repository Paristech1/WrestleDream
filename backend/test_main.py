"""Backend tests for WrestleDream."""

from datetime import date

from promotions import event_matches_promotion, normalize_promotion_keys
from scoring import compute_match_score, parse_length_minutes
from parsers.result_parser import parse_event_results
from services.matches import fetch_matches, get_default_cutoff, fetch_wrestlers_from_matches


def test_get_default_cutoff():
    # Wednesday May 20 2026 → Tuesday May 19
    assert get_default_cutoff(date(2026, 5, 20)) == date(2026, 5, 19)
    # Monday May 18 2026 → Sunday May 17
    assert get_default_cutoff(date(2026, 5, 18)) == date(2026, 5, 17)
    # Sunday May 24 2026 → Saturday May 23
    assert get_default_cutoff(date(2026, 5, 24)) == date(2026, 5, 23)


def test_parse_raw_1721():
    desc = open(__file__).read()  # placeholder — use inline
    _ = desc
    result = (
        "Street Fight\r\nFinn Balor defeats JD McDonagh (14:15)\r\n\r\n"
        "Singles Match\r\nSeth Rollins defeats Austin Theory (w/Logan Paul) (12:55)"
    )
    rows = parse_event_results(
        "Street Fight\r\nFinn Balor vs. JD McDonagh\r\n\r\nSingles Match\r\nSeth Rollins vs. Austin Theory",
        result,
        promotion="WWE",
        brand="RAW",
        event_name="RAW #1721",
        event_date="2026-05-18",
        source="test",
    )
    names = {r["WRESTLER_NAME"] for r in rows}
    assert "Finn Balor" in names
    assert "JD McDonagh" in names
    assert "Seth Rollins" in names


def test_match_score_winner_bonus():
    w = {
        "STAR_RATING": 4.0,
        "LENGTH_MINUTES": 15,
        "WON": True,
        "WIN_METHOD": "pinfall",
        "TITLE_MATCH": True,
    }
    score = compute_match_score(w)
    assert score > 60


def test_fetch_seed_only():
    matches = fetch_matches(
        ["WWE", "RAW"],
        before_date=date(2026, 5, 18),
        reference_date=date(2026, 5, 20),
        use_thesportsdb=False,
        use_seed=True,
    )
    assert len(matches) >= 10
    pool = fetch_wrestlers_from_matches(matches)
    assert len(pool) >= 4


def test_promotion_filter():
    assert event_matches_promotion("RAW #1721", "RAW")
    assert not event_matches_promotion("NXT #821", "RAW")
    assert normalize_promotion_keys(["raw", "sd"]) == ["RAW", "SMACKDOWN"]


def test_parse_length():
    assert parse_length_minutes("14:15") == 14.25
