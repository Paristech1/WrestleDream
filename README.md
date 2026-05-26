# WrestleDream

**A daily wrestling performance showdown — pick who had the better week until one wrestler remains.**
 two performers face off, you pick a winner, the winner returns to the deck, and the last wrestler standing wins.

## How it works

1. The backend builds a deck from **confirmed real match results** only.
2. The VS pool includes wrestlers who **actually wrestled** on selected promotions/brands, with match date **on or before the previous Monday** relative to your reference date (or today).
3. You pick the better performance; the winner stays in the deck.
4. Repeat until one champion remains.

### Monday cutoff

Given reference date **D** (default: today):

- **Previous Monday** = the Monday before **D** (if **D** is Monday, use the prior week’s Monday).
- Include only events where `dateEventLocal` (or `dateEvent`) ≤ that Monday.

Example: reference **2026-05-20** (Wednesday) → cutoff **2026-05-18** → includes **RAW #1721** (aired locally 2026-05-18).

## Promotions & brands

| Filter   | Model |
|----------|--------|
| **WWE**  | Parent company; all WWE brands |
| **RAW**, **SMACKDOWN**, **NXT** | WWE brands (filter by show name prefix) |
| **AEW** | Separate promotion |
| **TNA** | Separate promotion (Impact) |

RAW and SmackDown are **brands** under WWE, not separate parent companies.

## Match Score (adapted Game Score)

Single performance rating — higher is better:

```
Match Score = (STAR_RATING × 15) + (LENGTH_MINUTES × 0.5) + WIN_BONUS + (5 if title match)
```

- **STAR_RATING**: default `3.0` when not supplied by source (TheSportsDB does not provide Cagematch-style stars).
- **LENGTH_MINUTES**: parsed from `(MM:SS)` in results.
- **WIN_BONUS** (winners only): pinfall `3`, submission `3.5`, countout `2`, DQ `1.5`, referee decision `2.5`, etc.
- **Title match**: `+5` when match type contains “title”.

## Data sources (authoritative)

| Source | Role | Why |
|--------|------|-----|
| **[TheSportsDB](https://www.thesportsdb.com/)** (free API, league `4444` WWE) | Primary live results for WWE / Raw / SmackDown / NXT | Community-maintained event cards with `strResult` text from finished shows; event IDs traceable on site |
| **`backend/data/seed_matches.json`** | Fallback & AEW/TNA when API unavailable | Hand-verified JSON; each event must include a `source` URL (TheSportsDB event page or Cagematch) |
| **[Cagematch.net](https://www.cagematch.net/)** | Documented manual source | Industry-standard results DB; **automated access blocked** (Sucuri/captcha) — paste verified cards into seed file |
| **[TheSportsDB](https://www.thesportsdb.com/)** (player search) | Wrestler profile images | `strCutout` / `strRender` / `strThumb` — roster-style assets for WWE league wrestlers |
| **[Wikipedia](https://en.wikipedia.org/)** (summary thumbnail) | Portrait when SportsDB has no asset | Infobox-style headshots via REST summary API |
| **[Wikidata](https://www.wikidata.org/) + [Wikimedia Commons](https://commons.wikimedia.org/)** | Last resort headshots | `P18` with portrait-like filenames preferred over event photos |

We **do not** invent match outcomes. If an event is not in TheSportsDB or seed data, it is excluded.

### Image fallback

1. **TheSportsDB** `searchplayers.php` — prefer `strCutout`, then `strRender`, then `strThumb` (Fighting / Wrestler entries).
2. **Wikipedia** summary thumbnail (opensearch title → REST `page/summary`).
3. **Wikidata** `P18` → Commons `Special:FilePath` (`?width=500`), ranking filenames that look like portraits/headshots.
4. Neutral SVG silhouette in the UI if all sources miss (never a wrong person’s photo).

URLs are cached in memory for 24 hours. TheSportsDB image lookups share the same rate limit throttle as match fetches.

## Local development

### Prerequisites

- Node.js 18+
- Python 3.9+

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api/*` to `http://127.0.0.1:8000`.

### Tests

```bash
cd backend && source venv/bin/activate && pytest -q
cd frontend && npm test
```

### Environment

Copy `.env.example` to `.env` (optional). Key flags:

- `USE_SEED=true` — load `seed_matches.json`
- `USE_THESPORTSDB=true` — fetch WWE season from TheSportsDB (rate-limited; ~1.2s between calls)
- `THESPORTSDB_MIN_INTERVAL` — seconds between API requests

### Adding AEW / TNA results

1. Confirm results on [Cagematch](https://www.cagematch.net/) or an official recap.
2. Copy `backend/data/seed_matches.example.json` format into `seed_matches.json`.
3. Set `source` to the verification URL.

## Project layout

```
WrestleDream/
├── api/index.py          # Vercel entry
├── backend/
│   ├── main.py           # FastAPI /api/daily-deck
│   ├── promotions.py
│   ├── scoring.py
│   ├── parsers/result_parser.py
│   ├── services/matches.py, images.py
│   └── data/seed_matches.json
├── frontend/             # React + Vite + Framer Motion
└── README.md
```

## Known limitations

- **Cagematch scraping**: blocked for bots; use manual seed or browser export.
- **TheSportsDB**: free tier rate limits (HTTP 429); WWE-centric; AEW/TNA need seed data.
- **Star ratings**: not in TheSportsDB; defaults to 3.0 unless you add `STAR_RATING` in seed.
- **Tag teams**: each participant gets a row; six-man tags add many wrestlers.

## License

MIT (structure adapted from NBA Showdown).
