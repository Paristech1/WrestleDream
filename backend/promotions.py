"""Promotion / brand taxonomy for WrestleDream."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PromotionInfo:
    key: str
    label: str
    parent: Optional[str] = None  # WWE brand → parent promotion
    thesportsdb_league_id: Optional[str] = None
    event_prefixes: tuple[str, ...] = ()


# User-facing filters. RAW/SmackDown/NXT are WWE brands; WWE is the parent company.
PROMOTIONS: dict[str, PromotionInfo] = {
    "WWE": PromotionInfo(
        key="WWE",
        label="WWE (all brands)",
        thesportsdb_league_id="4444",
        event_prefixes=("RAW", "SmackDown", "SMACKDOWN", "NXT", "Main Event"),
    ),
    "RAW": PromotionInfo(
        key="RAW",
        label="WWE Raw",
        parent="WWE",
        thesportsdb_league_id="4444",
        event_prefixes=("RAW",),
    ),
    "SMACKDOWN": PromotionInfo(
        key="SMACKDOWN",
        label="WWE SmackDown",
        parent="WWE",
        thesportsdb_league_id="4444",
        event_prefixes=("SmackDown", "SMACKDOWN"),
    ),
    "NXT": PromotionInfo(
        key="NXT",
        label="WWE NXT",
        parent="WWE",
        thesportsdb_league_id="4444",
        event_prefixes=("NXT",),
    ),
    "AEW": PromotionInfo(key="AEW", label="All Elite Wrestling"),
    "TNA": PromotionInfo(key="TNA", label="TNA / Impact Wrestling"),
}

DEFAULT_PROMOTIONS = ("WWE", "RAW", "SMACKDOWN", "NXT", "AEW", "TNA")


def normalize_promotion_keys(keys: list[str] | None) -> list[str]:
    if not keys:
        return list(DEFAULT_PROMOTIONS)
    out = []
    for k in keys:
        ku = k.strip().upper().replace(" ", "")
        if ku in ("SMACKDOWN", "SD"):
            ku = "SMACKDOWN"
        if ku in PROMOTIONS:
            out.append(ku)
    return out or list(DEFAULT_PROMOTIONS)


def event_matches_promotion(event_name: str, promotion_key: str) -> bool:
    info = PROMOTIONS[promotion_key]
    name = (event_name or "").upper()
    if promotion_key == "WWE":
        return any(name.startswith(p.upper()) for p in info.event_prefixes)
    if info.event_prefixes:
        return any(name.startswith(p.upper()) for p in info.event_prefixes)
    # AEW / TNA: matched via league name or seed metadata
    if promotion_key == "AEW":
        return "AEW" in name or "ALL ELITE" in name
    if promotion_key == "TNA":
        return "TNA" in name or "IMPACT" in name
    return False
