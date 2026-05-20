"""Tests for wrestler image resolution."""

from unittest.mock import patch

from services import images


def test_pick_thesportsdb_prefers_cutout():
    player = {
        "strCutout": "https://example.com/cutout.png",
        "strThumb": "https://example.com/thumb.jpg",
    }
    assert images._pick_thesportsdb_url(player) == "https://example.com/cutout.png"


def test_portrait_score_prefers_headshot():
    assert images._portrait_score("Roman_Reigns_headshot.jpg") > images._portrait_score(
        "Roman_Reigns_at_event.jpg"
    )


@patch("services.images._thesportsdb_image", return_value="https://tsdb/cutout.png")
def test_get_wrestler_image_thesportsdb_first(mock_tsdb):
    images._image_cache.clear()
    url = images.get_wrestler_image("Roman Reigns", "WWE")
    assert url == "https://tsdb/cutout.png"
    mock_tsdb.assert_called_once()


@patch("services.images._thesportsdb_image", return_value=None)
@patch("services.images._wikipedia_thumbnail", return_value="https://wiki/thumb.jpg")
def test_get_wrestler_image_wikipedia_fallback(mock_wiki, _mock_tsdb):
    images._image_cache.clear()
    url = images.get_wrestler_image("Finn Balor", "WWE")
    assert url == "https://wiki/thumb.jpg"


@patch("services.images._thesportsdb_image", return_value=None)
@patch("services.images._wikipedia_thumbnail", return_value=None)
@patch("services.images._wikidata_image", return_value=None)
def test_get_wrestler_image_caches_miss(_wd, _wiki, _tsdb):
    images._image_cache.clear()
    assert images.get_wrestler_image("Unknown Wrestler XYZ") is None
    assert images.get_wrestler_image("Unknown Wrestler XYZ") is None
    _tsdb.assert_called_once()
