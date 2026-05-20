import { describe, it, expect } from 'vitest';
import { computeMatchScore, parseWrestlers } from './deckUtils';

describe('deckUtils', () => {
  it('parses wrestler pairs', () => {
    const data = {
      pairs: [{ wrestler_left: { WRESTLER_ID: 'a' }, wrestler_right: { WRESTLER_ID: 'b' } }],
    };
    expect(parseWrestlers(data)).toHaveLength(2);
  });

  it('computes match score', () => {
    const score = computeMatchScore({
      STAR_RATING: 4,
      LENGTH_MINUTES: 15,
      WON: true,
      WIN_METHOD: 'pinfall',
      TITLE_MATCH: true,
    });
    expect(score).toBeGreaterThan(60);
  });
});
