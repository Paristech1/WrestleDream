"""Fetch confirmed wrestling match results."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import requests

from promotions import (
    PROMOTIONS,
    event_matches_promotion,
    normalize_promotion_keys,
)
from parsers.result_parser import parse_event_results
from scoring import compute_match_score

THESPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json/3"
HTTP_TIMEOUT = 20
USER_AGENT = "WrestleDream/1.0 (educational; contact via README)"
SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed_matches.json"
LOOKBACK_DAYS = 21

_last_request = 0.0
_min_interval = float(os.environ.get("THESPORTSDB_MIN_INTERVAL", "1.2"))


def _throttle() -> None:
    global _last_request
    elapsed = time.time() - _last_request
    if elapsed < _min_interval:
        time.sleep(_min_interval - elapsed)
    _last_request = time.time()


def _get_json(path: str, params: dict | None = None) -> dict:
    _throttle()
    url = f"{THESPORTSDB_BASE}/{path}"
    r = requests.get(
        url,
        params=params or {},
        timeout=HTTP_TIMEOUT,
        headers={"User-Agent": USER_AGENT},
    )
    r.raise_for_status()
    return r.json()


def previous_monday(ref: date) -> date:
    """Most recent Monday strictly before ref (if ref is Monday, use prior week)."""
    if ref.weekday() == 0:
        return ref - timedelta(days=7)
    return ref - timedelta(days=ref.weekday())


def _event_date(ev: dict) -> date:
    raw = ev.get("dateEventLocal") or ev.get("dateEvent") or ""
    try:
        return datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return date.today()


def _brand_from_event(event_name: str, promotion_filter: str) -> str:
    name = (event_name or "").upper()
    if name.startswith("RAW"):
        return "RAW"
    if name.startswith("SMACKDOWN") or name.startswith("SD"):
        return "SMACKDOWN"
    if name.startswith("NXT"):
        return "NXT"
    if promotion_filter in ("RAW", "SMACKDOWN", "NXT"):
        return promotion_filter
    return promotion_filter if promotion_filter != "WWE" else "WWE"


def _fetch_wwe_events_season(year: int) -> list[dict]:
    info = PROMOTIONS["WWE"]
    if not info.thesportsdb_league_id:
        return []
    try:
        data = _get_json(
            "eventsseason.php",
            {"id": info.thesportsdb_league_id, "s": str(year)},
        )
        return data.get("events") or []
    except Exception as e:
        print(f"TheSportsDB season fetch failed: {e}")
        return []


def _load_seed_events() -> list[dict]:
    if not SEED_PATH.exists():
        return []
    with open(SEED_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("events", [])


def fetch_matches(
    promotions: list[str] | None = None,
    before_date: date | None = None,
    reference_date: date | None = None,
    *,
    use_seed: bool = True,
    use_thesportsdb: bool = True,
) -> list[dict[str, Any]]:
    """
    Return match-level records with wrestler appearances.
    Only includes events with date <= before_date (default: previous Monday vs reference).
    """
    promo_keys = normalize_promotion_keys(promotions)
    ref = reference_date or date.today()
    cutoff = before_date or previous_monday(ref)

    events: list[dict] = []

    if use_thesportsdb and any(
        PROMOTIONS[k].thesportsdb_league_id for k in promo_keys if k in ("WWE", "RAW", "SMACKDOWN", "NXT")
    ):
        for year in {cutoff.year, ref.year}:
            events.extend(_fetch_wwe_events_season(year))

    if use_seed:
        events.extend(_load_seed_events())

    matches: list[dict[str, Any]] = []
    seen_events: set[str] = set()

    for ev in events:
        event_name = ev.get("strEvent") or ev.get("event_name", "")
        event_key = f"{ev.get('idEvent') or ev.get('id')}:{event_name}"
        if event_key in seen_events:
            continue
        seen_events.add(event_key)

        ev_date = _event_date(ev) if "dateEvent" in ev or "dateEventLocal" in ev else datetime.strptime(
            ev.get("event_date", "")[:10], "%Y-%m-%d"
        ).date()

        if ev_date > cutoff:
            continue

        promo = (ev.get("strLeague") or ev.get("promotion") or "WWE").upper()
        if promo == "WWE":
            matched_promo = None
            for pk in promo_keys:
                if pk in ("WWE", "RAW", "SMACKDOWN", "NXT") and event_matches_promotion(event_name, pk):
                    matched_promo = pk
                    break
            if not matched_promo:
                continue
            brand = _brand_from_event(event_name, matched_promo)
            parent = "WWE"
        else:
            pk = promo.replace(" ", "")
            if "AEW" in pk and "AEW" not in promo_keys:
                continue
            if ("TNA" in pk or "IMPACT" in pk) and "TNA" not in promo_keys:
                continue
            if "AEW" in pk:
                parent, brand = "AEW", "AEW"
            elif "TNA" in pk or "IMPACT" in pk:
                parent, brand = "TNA", "TNA"
            else:
                continue

        source = ev.get("source") or f"thesportsdb:{ev.get('idEvent', '')}"
        wrestlers = parse_event_results(
            ev.get("strDescriptionEN") or ev.get("description", ""),
            ev.get("strResult") or ev.get("result", ""),
            promotion=parent,
            brand=brand,
            event_name=event_name,
            event_date=ev_date.isoformat(),
            source=source,
        )
        for w in wrestlers:
            w["MATCH_SCORE"] = compute_match_score(w)
            matches.append(w)

    return matches


def fetch_wrestlers_from_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Best single appearance per wrestler in the pool (highest Match Score)."""
    by_id: dict[str, dict] = {}
    for m in matches:
        wid = m["WRESTLER_ID"]
        if wid not in by_id or m["MATCH_SCORE"] > by_id[wid]["MATCH_SCORE"]:
            by_id[wid] = m
    return list(by_id.values())
