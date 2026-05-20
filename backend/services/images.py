"""Wrestler profile image resolution with layered fallbacks."""

from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Optional

import requests

from services.matches import _get_json

HTTP_TIMEOUT = 12
USER_AGENT = "WrestleDream/1.0 (local dev; +https://github.com/wrestledream)"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_PATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"
WIKIPEDIA_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"

PORTRAIT_HINTS = ("portrait", "headshot", "head shot", "mugshot", "profile", "posed", "studio")

_OVERRIDES_PATH = Path(__file__).resolve().parent.parent / "data" / "image_overrides.json"


def _load_overrides() -> dict[str, str]:
    if not _OVERRIDES_PATH.exists():
        return {}
    with open(_OVERRIDES_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return {k.lower(): v for k, v in data.get("overrides", {}).items()}


_IMAGE_OVERRIDES: dict[str, str] = _load_overrides()

_image_cache: dict[str, tuple[Optional[str], float]] = {}
_image_lock = threading.Lock()
IMAGE_CACHE_TTL = 86400  # 24h


def _cache_get(key: str) -> Optional[str] | object:
    """Return URL, None if cached miss, or _MISSING if not in cache."""
    with _image_lock:
        entry = _image_cache.get(key)
        if not entry:
            return _MISSING
        url, ts = entry
        if time.time() - ts > IMAGE_CACHE_TTL:
            del _image_cache[key]
            return _MISSING
        return url


_MISSING = object()


def _cache_set(key: str, url: Optional[str]) -> None:
    with _image_lock:
        _image_cache[key] = (url, time.time())


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).lower()


def _names_close(a: str, b: str) -> bool:
    na, nb = _normalize_name(a), _normalize_name(b)
    return na == nb or na in nb or nb in na


def _pick_thesportsdb_url(player: dict) -> Optional[str]:
    for field in ("strCutout", "strRender", "strThumb", "strFanart1"):
        url = (player.get(field) or "").strip()
        if url and url.lower() not in ("null", "none"):
            return url
    return None


def _thesportsdb_image(name: str) -> Optional[str]:
    try:
        data = _get_json("searchplayers.php", {"p": name})
        players = data.get("player") or []
        if not isinstance(players, list):
            players = [players] if players else []
        for p in players:
            sport = (p.get("strSport") or "").lower()
            pos = (p.get("strPosition") or "").lower()
            if sport not in ("fighting", "") and "wrestl" not in pos:
                continue
            if not _names_close(name, p.get("strPlayer", "")):
                continue
            url = _pick_thesportsdb_url(p)
            if url:
                return url
        for p in players:
            if _names_close(name, p.get("strPlayer", "")):
                url = _pick_thesportsdb_url(p)
                if url:
                    return url
        if players:
            return _pick_thesportsdb_url(players[0])
    except Exception:
        pass
    return None


def _wikipedia_title(name: str) -> Optional[str]:
    try:
        r = requests.get(
            WIKIPEDIA_API,
            params={
                "action": "opensearch",
                "search": name,
                "limit": 3,
                "namespace": 0,
                "format": "json",
            },
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        titles = r.json()[1]
        for title in titles:
            if _names_close(name, title) or "wrestl" in title.lower():
                return title
        return titles[0] if titles else None
    except Exception:
        return None


def _wikipedia_thumbnail(name: str) -> Optional[str]:
    title = _wikipedia_title(name) or name.replace(" ", "_")
    try:
        r = requests.get(
            f"{WIKIPEDIA_SUMMARY}{requests.utils.quote(title.replace(' ', '_'))}",
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        if r.status_code == 404:
            return None
        r.raise_for_status()
        thumb = r.json().get("thumbnail") or {}
        src = thumb.get("source")
        if src:
            return re.sub(r"/\d+px-", "/500px-", src) if "/thumb/" in src else src
    except Exception:
        pass
    return None


def _wikidata_search(name: str) -> Optional[str]:
    params = {
        "action": "wbsearchentities",
        "search": name,
        "language": "en",
        "format": "json",
        "type": "item",
        "limit": 5,
    }
    try:
        r = requests.get(
            WIKIDATA_API,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        results = r.json().get("search", [])
        for hit in results:
            desc = (hit.get("description") or "").lower()
            if any(
                kw in desc
                for kw in ("wrestler", "professional wrestling", "wwe", "aew", "boxer")
            ):
                return hit.get("id")
        return results[0]["id"] if results else None
    except Exception:
        return None


def _portrait_score(filename: str) -> int:
    low = filename.lower()
    score = 0
    for hint in PORTRAIT_HINTS:
        if hint in low:
            score += 10
    if re.search(r"\(\d{4}\)", low):
        score += 2
    return score


def _wikidata_image_filenames(qid: str) -> list[str]:
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "claims",
        "format": "json",
    }
    try:
        r = requests.get(
            WIKIDATA_API,
            params=params,
            timeout=HTTP_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
        )
        r.raise_for_status()
        ent = r.json().get("entities", {}).get(qid, {})
        claims = ent.get("claims", {})
        p18 = claims.get("P18", [])
        names = []
        for claim in p18:
            try:
                names.append(claim["mainsnak"]["datavalue"]["value"])
            except (KeyError, TypeError):
                continue
        names.sort(key=_portrait_score, reverse=True)
        return names
    except Exception:
        return []


def _commons_url(filename: str) -> str:
    safe = re.sub(r"\s+", "_", filename)
    return f"{COMMONS_PATH}{requests.utils.quote(safe)}?width=500"


def _wikidata_image(name: str) -> Optional[str]:
    qid = _wikidata_search(name)
    if not qid:
        return None
    filenames = _wikidata_image_filenames(qid)
    if not filenames:
        return None
    return _commons_url(filenames[0])


def get_wrestler_image(name: str, promotion: str = "") -> Optional[str]:
    """
    Resolve profile-style headshot URL. Fallback order:
    1. TheSportsDB (strCutout → strRender → strThumb)
    2. Wikipedia infobox / summary thumbnail
    3. Wikidata P18 → Wikimedia Commons (portrait filenames preferred)
    4. None (frontend neutral placeholder)
    """
    cache_key = f"{name}|{promotion}".lower()
    cached = _cache_get(cache_key)
    if cached is not _MISSING:
        return cached  # type: ignore[return-value]

    override = _IMAGE_OVERRIDES.get(name.lower())
    if override:
        _cache_set(cache_key, override)
        return override

    for resolver in (_thesportsdb_image, _wikipedia_thumbnail, _wikidata_image):
        url = resolver(name)
        if url:
            _cache_set(cache_key, url)
            return url

    _cache_set(cache_key, None)
    return None


def attach_images(wrestlers: list[dict]) -> list[dict]:
    for w in wrestlers:
        if not w.get("IMAGE_URL"):
            img = get_wrestler_image(w["WRESTLER_NAME"], w.get("PROMOTION", ""))
            if img:
                w["IMAGE_URL"] = img
    return wrestlers
