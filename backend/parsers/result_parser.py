"""Parse confirmed match result text (TheSportsDB strResult format)."""

from __future__ import annotations

import re
from typing import Any

from scoring import infer_win_method, parse_length_minutes  # noqa: E402 — run from backend/

# "Finn Balor defeats JD McDonagh (14:15)" or "A vs. B — A wins"
LENGTH_RE = re.compile(r"\((\d+:\d+)\)\s*$")
MANAGER_RE = re.compile(r"\s*\(w/[^)]+\)\s*", re.I)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _clean_name(name: str) -> str:
    name = MANAGER_RE.sub("", name).strip()
    name = re.sub(r"\s*\(c\)\s*", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name)
    return name


def _split_participants(side: str) -> list[str]:
    """Expand 'Team (A & B)' and combined sides into individual wrestler names."""
    side = LENGTH_RE.sub("", side).strip()
    side = re.sub(r"\s*\(c\)\s*", " ", side, flags=re.I)
    if not side:
        return []

    names: list[str] = []

    for inner in re.findall(r"\(([^()]+)\)", side):
        if re.search(r"[,&]", inner):
            for part in re.split(r"\s*&\s*|\s*,\s*", inner):
                if part.strip():
                    names.append(_clean_name(part))

    remainder = re.sub(r"\([^()]+\)", "", side)
    for part in re.split(r"\s*&\s*", remainder):
        part = _clean_name(part.strip())
        # Skip bare team labels (no second capitalized word pattern)
        if not part:
            continue
        if " " not in part and len(part) < 12:
            continue
        if re.match(r"^(Los|The)\s", part) and part.count(" ") <= 2:
            continue
        names.append(part)

    if names:
        return names
    return [_clean_name(side)] if side else []


def _parse_defeat_line(result_line: str) -> tuple[list[str], list[str], str]:
    line = result_line.strip()
    low = line.lower()
    sep = None
    for token in (" defeats ", " defeat "):
        if token in low:
            sep = token
            break
    if not sep:
        return [], [], ""
    idx = low.index(sep)
    win_side = line[:idx].strip()
    lose_side = line[idx + len(sep) :].strip()
    lose_side = LENGTH_RE.sub("", lose_side).strip()
    lose_side = re.sub(r"\s+by\s+[^()]+\s*$", "", lose_side, flags=re.I).strip()
    lose_side = MANAGER_RE.sub("", lose_side).strip()
    length_m = LENGTH_RE.search(result_line)
    match_length = length_m.group(1) if length_m else ""
    return _split_participants(win_side), _split_participants(lose_side), match_length


def parse_match_block(
    block: str,
    *,
    promotion: str,
    brand: str,
    event_name: str,
    event_date: str,
    source: str,
    title_match: bool = False,
    star_rating: float = 3.0,
) -> list[dict[str, Any]]:
    """Return one wrestler record per participant in a single match block."""
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    if not lines:
        return []

    match_type = lines[0]
    result_line = lines[-1] if len(lines) > 1 else lines[0]
    if "defeat" not in result_line.lower() and " vs" not in result_line.lower():
        if len(lines) >= 2:
            match_type = lines[0]
            result_line = lines[1]
        else:
            return []

    winner_names, loser_names, match_length = _parse_defeat_line(result_line)
    if not winner_names or not loser_names:
        return []

    length_min = parse_length_minutes(match_length)
    win_method = infer_win_method(result_line)

    records: list[dict[str, Any]] = []
    for name in winner_names + loser_names:
        if not name or len(name) < 2:
            continue
        won = name in winner_names
        records.append({
            "WRESTLER_ID": _slug(name),
            "WRESTLER_NAME": name,
            "PROMOTION": promotion,
            "BRAND": brand,
            "STAR_RATING": star_rating,
            "MATCH_LENGTH": match_length,
            "LENGTH_MINUTES": length_min,
            "WIN_METHOD": win_method if won else "",
            "WON": won,
            "MATCH_TYPE": match_type,
            "TITLE_MATCH": title_match or "title" in match_type.lower(),
            "OPPONENT": ", ".join(loser_names if won else winner_names),
            "EVENT_NAME": event_name,
            "EVENT_DATE": event_date,
            "SOURCE": source,
        })
    return records


def parse_event_results(
    description: str,
    result: str,
    *,
    promotion: str,
    brand: str,
    event_name: str,
    event_date: str,
    source: str,
) -> list[dict[str, Any]]:
    """Parse full event strDescriptionEN + strResult into wrestler rows."""
    text = (result or description or "").strip()
    if not text:
        return []

    blocks = re.split(r"\r?\n\r?\n+", text)
    out: list[dict[str, Any]] = []
    for block in blocks:
        title = "title" in block.lower()[:80]
        out.extend(
            parse_match_block(
                block,
                promotion=promotion,
                brand=brand,
                event_name=event_name,
                event_date=event_date,
                source=source,
                title_match=title,
            )
        )
    return out
