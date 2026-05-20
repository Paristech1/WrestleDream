/**
 * Fetch daily deck from API.
 */

export async function fetchDailyDeck(apiUrl, { promotions } = {}) {
  const params = new URLSearchParams();
  if (promotions?.length) params.set('promotions', promotions.join(','));
  const qs = params.toString();
  const url = qs ? `${apiUrl}?${qs}` : apiUrl;

  const res = await fetch(url);
  if (!res.ok) throw new Error(`API returned ${res.status}`);
  const text = await res.text();
  const trimmed = text.trim();
  if (!trimmed.startsWith('{') && !trimmed.startsWith('[')) {
    throw new Error('Invalid response: expected JSON from WrestleDream API.');
  }
  const data = JSON.parse(text);
  if (data.message && (!data.pairs || data.pairs.length === 0)) {
    throw new Error(data.message);
  }
  return data;
}
