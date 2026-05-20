/**
 * Deck parsing and Match Score utilities.
 */

export function parseWrestlers(data) {
  const wrestlers = [];
  const pairs = Array.isArray(data) ? data : (data?.pairs ?? []);
  for (const pair of pairs) {
    if (pair?.wrestler_left) wrestlers.push(pair.wrestler_left);
    if (pair?.wrestler_right) wrestlers.push(pair.wrestler_right);
    // Legacy NBA shape fallback
    if (pair?.player_left) wrestlers.push(pair.player_left);
    if (pair?.player_right) wrestlers.push(pair.player_right);
  }
  return wrestlers.filter(Boolean);
}

export function parseLengthMinutes(lengthStr) {
  if (!lengthStr) return 0;
  const m = String(lengthStr).match(/(\d+):(\d+)/);
  if (m) return parseInt(m[1], 10) + parseInt(m[2], 10) / 60;
  return 0;
}

const WIN_BONUS = {
  pinfall: 3,
  submission: 3.5,
  countout: 2,
  dq: 1.5,
  disqualification: 1.5,
  referee: 2.5,
  draw: 1,
  other: 2,
};

/** Match Score — mirrors backend/README formula */
export function computeMatchScore(w) {
  const stars = Number(w.STAR_RATING ?? 3);
  const length = Number(w.LENGTH_MINUTES ?? parseLengthMinutes(w.MATCH_LENGTH));
  const method = (w.WIN_METHOD || 'other').toLowerCase();
  const winBonus = w.WON ? (WIN_BONUS[method] ?? WIN_BONUS.other) : 0;
  const titleBonus = w.TITLE_MATCH ? 5 : 0;
  return +(stars * 15 + length * 0.5 + winBonus + titleBonus).toFixed(1);
}

export function promotionLabel(w) {
  if (w.BRAND && w.BRAND !== w.PROMOTION) return `${w.PROMOTION} · ${w.BRAND}`;
  return w.PROMOTION || w.BRAND || '—';
}
