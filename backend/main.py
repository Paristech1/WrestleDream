"""WrestleDream API — wrestling showdown deck builder."""

from __future__ import annotations

import os
import random
import threading
import time
from datetime import date, datetime
from typing import Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from promotions import DEFAULT_PROMOTIONS, PROMOTIONS
from scoring import compute_match_score
from services.images import attach_images
from services.matches import (
    fetch_matches,
    fetch_wrestlers_from_matches,
    get_default_cutoff,
)

CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "1800"))
MAX_WRESTLERS = int(os.environ.get("MAX_WRESTLERS", "36"))
MIN_WRESTLERS = int(os.environ.get("MIN_WRESTLERS", "4"))
USE_THESPORTSDB = os.environ.get("USE_THESPORTSDB", "true").lower() in ("1", "true", "yes")
USE_SEED = os.environ.get("USE_SEED", "true").lower() in ("1", "true", "yes")

app = FastAPI(title="WrestleDream API")

allowed_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://localhost:3000,https://*.vercel.app",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in allowed_origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def set_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    for header in ["Server", "X-Powered-By", "Via"]:
        if header in response.headers:
            del response.headers[header]
    return response


_cache: dict = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry is None:
            return None
        data, ts = entry
        if time.time() - ts > CACHE_TTL_SECONDS:
            del _cache[key]
            return None
        return data


def _cache_set(key, data):
    with _cache_lock:
        _cache[key] = (data, time.time())


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "WrestleDream"}


@app.get("/api/promotions")
def list_promotions():
    return [
        {
            "key": k,
            "label": v.label,
            "parent": v.parent,
            "is_brand": v.parent is not None,
        }
        for k, v in PROMOTIONS.items()
    ]


@app.get("/api/daily-deck")
def daily_deck(
    ref_date: Optional[str] = Query(default=None, alias="date", description="Reference date YYYY-MM-DD"),
    promotions: Optional[str] = Query(
        default=None,
        description="Comma-separated promotion keys (WWE,RAW,SMACKDOWN,NXT,AEW,TNA)",
    ),
):
    ref = date.today()
    if ref_date:
        try:
            ref = datetime.strptime(ref_date, "%Y-%m-%d").date()
        except ValueError:
            return {
                "message": "Invalid date format. Use YYYY-MM-DD.",
                "pairs": [],
                "cutoff_date": None,
            }

    cutoff = get_default_cutoff(ref)
    promo_list = (
        [p.strip() for p in promotions.split(",") if p.strip()]
        if promotions
        else list(DEFAULT_PROMOTIONS)
    )
    cache_key = f"deck_{ref.isoformat()}_{cutoff.isoformat()}_{','.join(sorted(promo_list))}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    matches = fetch_matches(
        promo_list,
        before_date=cutoff,
        reference_date=ref,
        use_seed=USE_SEED,
        use_thesportsdb=USE_THESPORTSDB,
    )
    pool = fetch_wrestlers_from_matches(matches)
    pool = sorted(pool, key=compute_match_score, reverse=True)[:MAX_WRESTLERS]
    pool = attach_images(pool)

    if len(pool) < MIN_WRESTLERS:
        payload = {
            "message": (
                f"Not enough wrestlers ({len(pool)}) with confirmed matches on or before "
                f"{cutoff.isoformat()} for {', '.join(promo_list)}. "
                "Try enabling USE_SEED, broadening promotions, or adding verified events to "
                "backend/data/seed_matches.json."
            ),
            "pairs": [],
            "cutoff_date": cutoff.isoformat(),
            "reference_date": ref.isoformat(),
            "wrestler_count": len(pool),
        }
        return payload

    random.shuffle(pool)
    pairs = []
    for i in range(0, len(pool) - 1, 2):
        pairs.append({
            "id": i,
            "wrestler_left": pool[i],
            "wrestler_right": pool[i + 1],
        })

    payload = {
        "pairs": pairs,
        "cutoff_date": cutoff.isoformat(),
        "reference_date": ref.isoformat(),
        "wrestler_count": len(pool),
        "promotions": promo_list,
    }
    _cache_set(cache_key, payload)
    return payload
