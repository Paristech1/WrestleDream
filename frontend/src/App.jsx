import { useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FaChevronDown,
  FaChevronUp,
  FaHistory,
  FaTwitter,
  FaFire,
  FaFilter,
} from 'react-icons/fa';
import { MdVerified } from 'react-icons/md';
import { GiMuscleUp } from 'react-icons/gi';
import React from 'react';
import { parseWrestlers, computeMatchScore, promotionLabel } from './lib/deckUtils';
import { fetchDailyDeck } from './lib/fetchDeck';
import './App.css';

const DAILY_DECK_URL = '/api/daily-deck';
const STORAGE_KEY = 'wrestledream_state';

const ALL_PROMOS = ['WWE', 'RAW', 'SMACKDOWN', 'NXT', 'AEW', 'TNA'];

const PLACEHOLDER_SVG =
  "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 500' fill='%23333'%3E%3Crect width='400' height='500' fill='%231a1a1a'/%3E%3Ccircle cx='200' cy='160' r='70' fill='%23444'/%3E%3Cellipse cx='200' cy='380' rx='90' ry='70' fill='%23444'/%3E%3C/svg%3E";

function saveToStorage(state) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    /* ignore */
  }
}

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY);
}

function buildShareText(winner, ms) {
  return `🤼 My WrestleDream Champion: ${winner.WRESTLER_NAME} (${promotionLabel(winner)}) — Match Score ${ms}! #WrestleDream`;
}

const WrestlerCard = ({
  wrestler,
  onClick,
  isWinner,
  isLoser,
  showFullStats,
  onToggleStats,
  variant = 'full',
}) => {
  const imgUrl = wrestler.IMAGE_URL || PLACEHOLDER_SVG;
  const matchScore = wrestler.MATCH_SCORE ?? computeMatchScore(wrestler);
  const isSimple = variant === 'simple';

  return (
    <motion.div
      className={`card-wrap pointer ${isWinner ? 'winner-card' : ''} ${isLoser ? 'loser-card' : ''}`}
      onClick={onClick}
      initial={{ opacity: 0, y: 40, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -40, scale: 0.95 }}
      whileHover={{ scale: isSimple ? 1.05 : 1.02 }}
      whileTap={{ scale: 0.98 }}
      transition={{ duration: 0.28, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className={`card ${variant}`}>
        <div className="card-holo" />
        <img
          src={imgUrl}
          alt={wrestler.WRESTLER_NAME}
          className="card-bg"
          onError={(e) => {
            e.currentTarget.src = PLACEHOLDER_SVG;
          }}
        />
        <div className="card-filter" />
        <div className="card-status">
          <div className={`status-dot ${isLoser ? 'loser-dot' : 'online'}`} />
          <div className="status-text">{isLoser ? 'ELIMINATED' : 'ACTIVE'}</div>
        </div>
        <div className="game-score-badge">
          <span className="gs-label">MATCH SCORE</span>
          <span className="gs-value">{matchScore}</span>
        </div>
        <div className="card-content">
          <div className="card-name-wrap">
            <div className="card-name">{wrestler.WRESTLER_NAME}</div>
            <MdVerified className="card-verification" color="#e11d48" size={20} />
          </div>
          <div className="card-team">{promotionLabel(wrestler)}</div>
          <div className="card-stats">
            <div className={`stat-pill ${wrestler.WON ? 'stat-green' : ''}`}>
              <span className="stat-label">RESULT</span>
              <span className="stat-value">{wrestler.WON ? 'WIN' : 'LOSS'}</span>
            </div>
            <div className="stat-pill">
              <span className="stat-label">STARS</span>
              <span className="stat-value">{wrestler.STAR_RATING ?? '—'}</span>
            </div>
            <div className="stat-pill">
              <span className="stat-label">TIME</span>
              <span className="stat-value">{wrestler.MATCH_LENGTH || '—'}</span>
            </div>
            <div className="stat-pill">
              <span className="stat-label">TYPE</span>
              <span className="stat-value">{(wrestler.MATCH_TYPE || '').slice(0, 12)}</span>
            </div>
          </div>
          {!isSimple && (
            <button
              type="button"
              className="toggle-stats-btn"
              onClick={(e) => {
                e.stopPropagation();
                onToggleStats?.();
              }}
            >
              {showFullStats ? <FaChevronUp size={10} /> : <FaChevronDown size={10} />}
              <span>{showFullStats ? 'Hide Details' : 'Match Details'}</span>
            </button>
          )}
          {showFullStats && !isSimple && (
            <motion.div
              className="full-stats"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
            >
              <div className="full-stats-grid">
                <div className="fs-item">
                  <span className="fs-label">Event</span>
                  <span className="fs-val">{wrestler.EVENT_NAME}</span>
                </div>
                <div className="fs-item">
                  <span className="fs-label">Date</span>
                  <span className="fs-val">{wrestler.EVENT_DATE}</span>
                </div>
                <div className="fs-item">
                  <span className="fs-label">Opponent</span>
                  <span className="fs-val">{wrestler.OPPONENT}</span>
                </div>
                <div className="fs-item">
                  <span className="fs-label">Method</span>
                  <span className="fs-val">{wrestler.WIN_METHOD || '—'}</span>
                </div>
              </div>
            </motion.div>
          )}
          {!isWinner && !isLoser && !isSimple && (
            <div className="card-button">
              <div className="btn-text">Pick Winner</div>
              <div className="btn-icon">
                <GiMuscleUp />
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
};

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="container">
          <div className="error-card">
            <h2>Something went wrong</h2>
            <button type="button" className="reset-btn" onClick={() => window.location.reload()}>
              Refresh
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const _saved = loadFromStorage();
const _hasSaved = !!(_saved?.leftWrestler && _saved?.rightWrestler);

function App() {
  const [allWrestlers, setAllWrestlers] = useState(() => (_hasSaved ? _saved.allWrestlers || [] : []));
  const [deck, setDeck] = useState(() => (_hasSaved ? _saved.deck || [] : []));
  const [leftWrestler, setLeftWrestler] = useState(() => (_hasSaved ? _saved.leftWrestler : null));
  const [rightWrestler, setRightWrestler] = useState(() => (_hasSaved ? _saved.rightWrestler : null));
  const [loading, setLoading] = useState(() => !_hasSaved);
  const [error, setError] = useState(null);
  const [winner, setWinner] = useState(() => (_hasSaved ? _saved.winner : null));
  const [matchLog, setMatchLog] = useState(() => (_hasSaved ? _saved.matchLog : []));
  const [expandedLeft, setExpandedLeft] = useState(false);
  const [expandedRight, setExpandedRight] = useState(false);
  const [matchLogExpanded, setMatchLogExpanded] = useState(false);
  const [screen, setScreen] = useState('home');
  const [selectedPromos, setSelectedPromos] = useState(ALL_PROMOS);
  const [cutoffInfo, setCutoffInfo] = useState(null);

  function applyFetchedData(data) {
    const wrestlers = parseWrestlers(data);
    if (wrestlers.length < 2) {
      setError(data.message || 'Not enough wrestlers for a showdown.');
      setLoading(false);
      return;
    }
    setCutoffInfo({
      cutoff: data.cutoff_date,
      reference: data.reference_date,
    });
    setAllWrestlers(wrestlers);
    const shuffled = [...wrestlers].sort(() => Math.random() - 0.5);
    setLeftWrestler(shuffled[0]);
    setRightWrestler(shuffled[1]);
    setDeck(shuffled.slice(2));
    setWinner(null);
    setMatchLog([]);
    setError(null);
    clearStorage();
    setLoading(false);
  }

  function loadDeck() {
    setLoading(true);
    setError(null);
    fetchDailyDeck(DAILY_DECK_URL, { promotions: selectedPromos })
      .then(applyFetchedData)
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  useEffect(() => {
    if (_hasSaved) return undefined;
    let cancelled = false;
    fetchDailyDeck(DAILY_DECK_URL, { promotions: selectedPromos })
      .then((data) => {
        if (!cancelled) applyFetchedData(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!loading && leftWrestler) {
      saveToStorage({
        allWrestlers,
        deck,
        leftWrestler,
        rightWrestler,
        winner,
        matchLog,
        selectedPromos,
      });
    }
  });

  function handlePick(side) {
    if (winner) return;
    const selected = side === 'left' ? leftWrestler : rightWrestler;
    const eliminated = side === 'left' ? rightWrestler : leftWrestler;
    const newLog = [
      ...matchLog,
      {
        winner: selected.WRESTLER_NAME,
        winnerId: selected.WRESTLER_ID,
        winnerScore: computeMatchScore(selected),
        loser: eliminated.WRESTLER_NAME,
        loserId: eliminated.WRESTLER_ID,
        loserScore: computeMatchScore(eliminated),
      },
    ];
    setMatchLog(newLog);
    if (deck.length < 1) {
      setWinner(selected);
      return;
    }
    const updatedDeck = [...deck, selected].sort(() => Math.random() - 0.5);
    setLeftWrestler(updatedDeck[0]);
    setRightWrestler(updatedDeck[1]);
    setDeck(updatedDeck.slice(2));
    setExpandedLeft(false);
    setExpandedRight(false);
  }

  function resetGame() {
    clearStorage();
    setWinner(null);
    setMatchLog([]);
    setScreen('game');
    loadDeck();
  }

  function togglePromo(key) {
    setSelectedPromos((prev) =>
      prev.includes(key) ? prev.filter((p) => p !== key) : [...prev, key],
    );
  }

  const deckAvgScore =
    allWrestlers.length > 0
      ? +(
          allWrestlers.reduce((s, w) => s + computeMatchScore(w), 0) / allWrestlers.length
        ).toFixed(1)
      : 0;

  const topPerformers = useMemo(
    () =>
      [...allWrestlers]
        .sort((a, b) => computeMatchScore(b) - computeMatchScore(a))
        .slice(0, 5),
    [allWrestlers],
  );

  const filtersBar = (
    <div className="filters-bar">
      <div className="filter-group promo-chips">
        <FaFilter size={12} />
        {ALL_PROMOS.map((p) => (
          <button
            key={p}
            type="button"
            className={`promo-chip ${selectedPromos.includes(p) ? 'active' : ''}`}
            onClick={() => togglePromo(p)}
          >
            {p}
          </button>
        ))}
      </div>
      <button type="button" className="hub-btn hub-btn-secondary filter-apply" onClick={loadDeck}>
        Load deck
      </button>
      {cutoffInfo?.cutoff && (
        <p className="cutoff-hint">
          Matches on or before {cutoffInfo.cutoff} (previous Monday)
        </p>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="container">
        <header className="header">
          <button type="button" className="logo-text logo-home-trigger">
            WRESTLE<span className="logo-accent">DREAM</span>
          </button>
          <div className="subtitle">Loading this week&apos;s performers...</div>
        </header>
        {filtersBar}
        <div className="arena">
          <div className="skeleton-card">
            <div className="skeleton-shine" />
          </div>
          <div className="vs-badge">VS</div>
          <div className="skeleton-card">
            <div className="skeleton-shine" />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container">
        <header className="header">
          <button type="button" className="logo-text">
            WRESTLE<span className="logo-accent">DREAM</span>
          </button>
        </header>
        {filtersBar}
        <div className="error-card">
          <h2>Could not build deck</h2>
          <p>{error}</p>
          <button type="button" className="reset-btn" onClick={loadDeck}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (winner) {
    const ms = computeMatchScore(winner);
    return (
      <div className="victory-screen">
        <div className="victory-content container">
          <header className="header">
            <div className="victory-title">Champion of the Week</div>
            <div className="victory-subheader">{winner.WRESTLER_NAME}</div>
          </header>
          <div className="arena">
            <WrestlerCard wrestler={winner} isWinner variant="simple" />
          </div>
          <p className="victory-deck-comparison">
            Match Score {ms} · Deck avg {deckAvgScore}
          </p>
          {matchLog.length > 0 && (
            <div className="match-log-wrapper">
              <button
                type="button"
                className="match-log-toggle"
                onClick={() => setMatchLogExpanded((p) => !p)}
              >
                <FaHistory size={14} />
                {matchLogExpanded ? 'Hide path' : 'Show path to victory'}
              </button>
              {matchLogExpanded && (
                <div className="match-log">
                  {matchLog.map((m, i) => (
                    <div key={i} className="log-entry">
                      <span className="log-winner">{m.winner}</span>
                      <span className="log-score">{m.winnerScore}</span>
                      <span className="log-vs">beat</span>
                      <span className="log-loser">{m.loser}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          <button type="button" className="share-btn twitter" onClick={() => {
            window.open(
              `https://twitter.com/intent/tweet?text=${encodeURIComponent(buildShareText(winner, ms))}`,
              '_blank',
            );
          }}>
            <FaTwitter size={18} /> Share
          </button>
          <button type="button" className="victory-btn-primary" onClick={resetGame}>
            PLAY AGAIN
          </button>
        </div>
      </div>
    );
  }

  if (!leftWrestler || !rightWrestler) {
    return (
      <div className="container">
        <header className="header">
          <button type="button" className="logo-text">
            WRESTLE<span className="logo-accent">DREAM</span>
          </button>
        </header>
        {filtersBar}
        <button type="button" className="reset-btn" onClick={loadDeck}>
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="container">
      <AnimatePresence mode="wait">
        {screen === 'home' && (
          <motion.section
            key="home"
            className="home-hub"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -40 }}
          >
            <header className="header">
              <button type="button" className="logo-text" onClick={() => setScreen('home')}>
                WRESTLE<span className="logo-accent">DREAM</span>
              </button>
            </header>
            <p className="home-hub-copy">
              Pick who had the better week — real matches, real results. Last wrestler standing wins.
            </p>
            {filtersBar}
            <div className="home-hub-actions">
              <button type="button" className="hub-btn hub-btn-primary" onClick={() => setScreen('game')}>
                Start Showdown
              </button>
              <button type="button" className="hub-btn hub-btn-secondary" onClick={() => setScreen('leaders')}>
                <FaFire size={14} /> Top Match Scores
              </button>
            </div>
          </motion.section>
        )}

        {screen === 'game' && (
          <motion.section key="game" className="screen-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <header className="header">
              <button type="button" className="logo-text" onClick={() => setScreen('home')}>
                WRESTLE<span className="logo-accent">DREAM</span>
              </button>
              <div className="subtitle">Who had the better performance?</div>
            </header>
            {filtersBar}
            <div className="scoreboard">
              <div className="score-item">
                <div className="score-label">In deck</div>
                <div className="score-value">{deck.length}</div>
              </div>
              <div className="score-item">
                <div className="score-label">Bouts</div>
                <div className="score-value">{matchLog.length}</div>
              </div>
            </div>
            <div className="arena">
              <div className="arena-slot">
                <AnimatePresence mode="wait">
                  <WrestlerCard
                    key={leftWrestler.WRESTLER_ID}
                    wrestler={leftWrestler}
                    onClick={() => handlePick('left')}
                    showFullStats={expandedLeft}
                    onToggleStats={() => setExpandedLeft((p) => !p)}
                  />
                </AnimatePresence>
              </div>
              <div className="vs-badge">VS</div>
              <div className="arena-slot">
                <AnimatePresence mode="wait">
                  <WrestlerCard
                    key={rightWrestler.WRESTLER_ID}
                    wrestler={rightWrestler}
                    onClick={() => handlePick('right')}
                    showFullStats={expandedRight}
                    onToggleStats={() => setExpandedRight((p) => !p)}
                  />
                </AnimatePresence>
              </div>
            </div>
            <button type="button" className="restart-btn" onClick={resetGame}>
              Restart
            </button>
          </motion.section>
        )}

        {screen === 'leaders' && (
          <motion.section key="leaders" className="screen-panel" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
            <header className="header">
              <button type="button" className="logo-text" onClick={() => setScreen('home')}>
                WRESTLE<span className="logo-accent">DREAM</span>
              </button>
              <div className="subtitle">Top Match Scores this deck</div>
            </header>
            <div className="leaders-flow">
              {topPerformers.map((w) => (
                <div key={w.WRESTLER_ID} className="leaders-flow-item">
                  <WrestlerCard wrestler={w} variant="simple" />
                </div>
              ))}
            </div>
            <button type="button" className="hub-btn hub-btn-primary" onClick={() => setScreen('game')}>
              Start Showdown
            </button>
          </motion.section>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function AppWrapper() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}
