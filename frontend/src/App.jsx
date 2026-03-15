import { useEffect, useMemo, useState } from 'react';
import { deleteWishlistItem, evaluateLive, getRankings, getWishlist, recalc, saveWishlistItem, searchStocks, syncData } from './services/api';
import './styles.css';

const defaultWeights = {
  valuation: 0.1,
  leverage: 0.12,
  profitability: 0.18,
  liquidity: 0.08,
  cashflow: 0.1,
  growth: 0.2,
  ownership: 0.1,
  qualitative: 0.12,
};

const factorFields = [
  ['PE Ratio', 'pe_ratio'],
  ['Debt/Equity', 'debt_to_equity'],
  ['ROI', 'roi'],
  ['ROE', 'roe'],
  ['ROA', 'roa'],
  ['Interest Cover', 'interest_coverage'],
  ['Current Ratio', 'current_ratio'],
  ['Quick Ratio', 'quick_ratio'],
  ['Operating Margin', 'operating_margin'],
  ['Net Margin', 'net_margin'],
  ['Revenue Growth', 'revenue_growth'],
  ['Earnings Growth', 'earnings_growth'],
];

function fmt(val, digits = 2) {
  if (val === null || val === undefined || Number.isNaN(Number(val))) {
    return '-';
  }
  return Number(val).toFixed(digits);
}

function StockPanel({ stock, expanded, onToggle, onWish, note, tag }) {
  const priceChange = Number(stock.price_change_pct || 0);

  return (
    <article className="stock-panel">
      <div className="stock-head">
        <div>
          <div className="pill">{stock.exchange}</div>
          <h3>{stock.ticker} · {stock.name}</h3>
          <p>{stock.sector} · {stock.industry}</p>
        </div>
        <div className="score-box">
          <div>
            <span>AlphaScore</span>
            <strong>{fmt(stock.alpha_score, 1)}</strong>
          </div>
          <div>
            <span>Latest Price (INR)</span>
            <strong>₹{fmt(stock.price)}</strong>
            <small className={priceChange >= 0 ? 'up' : 'down'}>{fmt(priceChange)}%</small>
          </div>
        </div>
        <div className="panel-actions">
          <button className="ghost" onClick={() => onWish(stock.ticker, note, tag)}>Wishlist +</button>
          <button onClick={onToggle}>{expanded ? 'Collapse' : 'Expand'}</button>
        </div>
      </div>

      {expanded && (
        <div className="expand-wrap">
          <div className="metrics-grid">
            {factorFields.map(([label, key]) => (
              <div key={key} className="metric-cell">
                <span>{label}</span>
                <strong>{fmt(stock[key])}</strong>
              </div>
            ))}
          </div>
          <div className="details-grid">
            <div>
              <h4>Scoring Breakdown</h4>
              <ul>
                {Object.entries(stock.score_breakdown || {}).map(([k, v]) => (
                  <li key={k}>{k}: {fmt(v, 1)}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4>Market Catalyst & News</h4>
              <ul>
                {(stock.news || []).slice(0, 4).map((item, idx) => (
                  <li key={`${stock.ticker}-${idx}`}>
                    <a href={item.link} target="_blank" rel="noreferrer">{item.title || 'News item'}</a>
                  </li>
                ))}
              </ul>
              <p>
                Sources: <a href={stock.source_references?.nse} target="_blank" rel="noreferrer">NSE</a> ·{' '}
                <a href={stock.source_references?.bse} target="_blank" rel="noreferrer">BSE</a> ·{' '}
                <a href={stock.source_references?.yahoo} target="_blank" rel="noreferrer">Yahoo</a>
              </p>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}

export default function App() {
  const [rankings, setRankings] = useState({ large: [], mid: [], small: [] });
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [liveStock, setLiveStock] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [wishlist, setWishlist] = useState([]);
  const [note, setNote] = useState('');
  const [tag, setTag] = useState('');
  const [weights, setWeights] = useState(defaultWeights);
  const [lastSynced, setLastSynced] = useState(null);
  const [coverage, setCoverage] = useState({});
  const [error, setError] = useState('');

  const load = async () => {
    const rankingResponse = await getRankings();
    setRankings(rankingResponse.rankings || { large: [], mid: [], small: [] });
    setLastSynced(rankingResponse.last_synced);
    setCoverage(rankingResponse.coverage || {});

    const wishlistResponse = await getWishlist();
    setWishlist(wishlistResponse.items || []);
  };

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  const onLocalSearch = async () => {
    try {
      setError('');
      const result = await searchStocks(searchText);
      setSearchResults(result.results || []);
    } catch (e) {
      setError(e.message);
    }
  };

  const onLiveSearch = async () => {
    try {
      setError('');
      const result = await evaluateLive(searchText.trim());
      const stock = result.stock;
      setLiveStock(stock);
      setExpanded((prev) => ({ ...prev, [stock.ticker]: true }));
    } catch (e) {
      setError(e.message);
    }
  };

  const addWish = async (ticker, n, t) => {
    try {
      const res = await saveWishlistItem({ ticker, note: n, tag: t });
      setWishlist(res.items || []);
    } catch (e) {
      setError(e.message);
    }
  };

  const removeWish = async (ticker) => {
    try {
      const res = await deleteWishlistItem(ticker);
      setWishlist(res.items || []);
    } catch (e) {
      setError(e.message);
    }
  };

  const sync = async () => {
    try {
      setError('');
      await syncData();
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const applyWeights = async () => {
    try {
      setError('');
      await recalc(weights);
      await load();
    } catch (e) {
      setError(e.message);
    }
  };

  const segments = useMemo(() => ['large', 'mid', 'small'], []);

  return (
    <div className="app-bg">
      <main className="container">
        <header className="topbar">
          <div>
            <h1>AlphaCap Intelligence</h1>
            <p>India-only NSE/BSE dashboard · last synced: {lastSynced || 'Not synced yet'}</p>
          </div>
          <div className="topbar-actions">
            <button onClick={sync}>Manual Sync</button>
          </div>
        </header>

        <section className="toolbar">
          <input
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search ticker/company (e.g., TCS, RELIANCE, TCS.NS)"
          />
          <button className="ghost" onClick={onLocalSearch}>Search Local Synced Data</button>
          <button onClick={onLiveSearch}>Search Live on NSE/BSE + Calculate AlphaScore</button>
        </section>

        {error && <div className="alert">{error}</div>}

        <section className="coverage-row">
          <div className="coverage-box">Attempted: <strong>{coverage.attempted || 0}</strong></div>
          <div className="coverage-box">Fetched: <strong>{coverage.fetched || 0}</strong></div>
          <div className="coverage-box">Eligible (no crucial missing data): <strong>{coverage.eligible_complete_records || 0}</strong></div>
        </section>

        <section className="panel">
          <h2>AlphaScore Weight Controls</h2>
          <div className="weights-grid">
            {Object.keys(weights).map((k) => (
              <label key={k}>
                {k}
                <input type="number" step="0.01" value={weights[k]} onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })} />
              </label>
            ))}
          </div>
          <button onClick={applyWeights}>Apply Weights</button>
        </section>

        {liveStock && (
          <section className="panel">
            <h2>Live Evaluation Result</h2>
            <StockPanel
              stock={liveStock}
              expanded={!!expanded[liveStock.ticker]}
              onToggle={() => setExpanded((prev) => ({ ...prev, [liveStock.ticker]: !prev[liveStock.ticker] }))}
              onWish={addWish}
              note={note}
              tag={tag}
            />
          </section>
        )}

        <section className="panel">
          <h2>Local Search Results</h2>
          {searchResults.length === 0 && <p className="muted">No local matches yet. Use local or live search above.</p>}
          {searchResults.map((stock) => (
            <StockPanel
              key={`search-${stock.ticker}`}
              stock={stock}
              expanded={!!expanded[stock.ticker]}
              onToggle={() => setExpanded((prev) => ({ ...prev, [stock.ticker]: !prev[stock.ticker] }))}
              onWish={addWish}
              note={note}
              tag={tag}
            />
          ))}
        </section>

        <section className="panel">
          <h2>Top 10 Ranked (Complete Data Only)</h2>
          {segments.map((segment) => (
            <div key={segment}>
              <h3>{segment.toUpperCase()} CAP</h3>
              {(rankings[segment] || []).map((stock) => (
                <StockPanel
                  key={`${segment}-${stock.ticker}`}
                  stock={stock}
                  expanded={!!expanded[stock.ticker]}
                  onToggle={() => setExpanded((prev) => ({ ...prev, [stock.ticker]: !prev[stock.ticker] }))}
                  onWish={addWish}
                  note={note}
                  tag={tag}
                />
              ))}
            </div>
          ))}
        </section>

        <section className="panel">
          <h2>Wishlist</h2>
          <div className="wish-inputs">
            <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="Common note for add to wishlist" />
            <input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="Tag" />
          </div>
          <table>
            <thead>
              <tr><th>Ticker</th><th>Note</th><th>Tag</th><th>Action</th></tr>
            </thead>
            <tbody>
              {wishlist.map((item) => (
                <tr key={item.ticker}>
                  <td>{item.ticker}</td>
                  <td>{item.note}</td>
                  <td>{item.tag}</td>
                  <td><button className="danger" onClick={() => removeWish(item.ticker)}>Remove</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
