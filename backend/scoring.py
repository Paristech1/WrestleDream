"""Wrestling Match Score — adapted from NBA Showdown Game Score."""

from __future__ import annotations

import re
from typing import Any


WIN_METHOD_BONUS = {
    "pinfall": 3.0,
    "submission": 3.5,
    "countout": 2.0,
    "dq": 1.5,
    "disqualification": 1.5,
    "no contest": 0.0,
    "draw": 1.0,
    "referee": 2.5,
    "other": 2.0,
}


def parse_length_minutes(length_str: str | None) -> float:
    if not length_str:
        return 0.0
    s = str(length_str).strip()
    m = re.match(r"(\d+):(\d+)", s)
    if m:
        return int(m.group(1)) + int(m.group(2)) / 60.0
    m2 = re.match(r"(\d+)\s*min", s, re.I)
    if m2:
        return float(m2.group(1))
    return 0.0


def infer_win_method(result_line: str) -> str:
    low = (result_line or "").lower()
    if "submission" in low or "tap out" in low:
        return "submission"
    if "count" in low and "out" in low:
        return "countout"
    if "disqualif" in low or " dq" in low:
        return "dq"
    if "no contest" in low:
        return "no contest"
    if "referee" in low:
        return "referee"
    if "draw" in low:
        return "draw"
    return "pinfall"


def compute_match_score(w: dict[str, Any]) -> float:
    """
    Match Score formula (documented in README):
      (STAR_RATING × 15) + (LENGTH_MINUTES × 0.5) + WIN_BONUS + (5 if title match)
    WIN_BONUS applies only when WON is True.
    """
    stars = float(w.get("STAR_RATING") or 3.0)
    length = float(w.get("LENGTH_MINUTES") or parse_length_minutes(w.get("MATCH_LENGTH")))
    method = (w.get("WIN_METHOD") or "other").lower()
    win_bonus = WIN_METHOD_BONUS.get(method, WIN_METHOD_BONUS["other"]) if w.get("WON") else 0.0
    title_bonus = 5.0 if w.get("TITLE_MATCH") else 0.0
    return round(stars * 15 + length * 0.5 + win_bonus + title_bonus, 1)
