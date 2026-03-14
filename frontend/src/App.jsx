import { useEffect, useMemo, useState } from 'react';
import { deleteWishlistItem, getRankings, getStock, getWishlist, recalc, saveWishlistItem, searchStocks, syncData } from './services/api';
import './styles.css';

const defaultWeights = {
  valuation: 0.1, leverage: 0.12, profitability: 0.18, liquidity: 0.08,
  cashflow: 0.1, growth: 0.2, ownership: 0.1, qualitative: 0.12,
};

function StockCard({ stock, onOpen, onWish }) {
  return (
    <div className="card">
      <h4>{stock.ticker} — {stock.name}</h4>
      <p>AlphaScore: <strong>{Number(stock.alpha_score).toFixed(2)}</strong></p>
      <p>Sector: {stock.sector}</p>
      <div className="row">
        <button onClick={() => onOpen(stock.ticker)}>View</button>
        <button onClick={() => onWish(stock.ticker)}>Wishlist +</button>
      </div>
    </div>
  );
}

export default function App() {
  const [rankings, setRankings] = useState({ large: [], mid: [], small: [] });
  const [search, setSearch] = useState('');
  const [results, setResults] = useState([]);
  const [active, setActive] = useState(null);
  const [wishlist, setWishlist] = useState([]);
  const [note, setNote] = useState('');
  const [tag, setTag] = useState('');
  const [weights, setWeights] = useState(defaultWeights);
  const [lastSynced, setLastSynced] = useState(null);

  const load = async () => {
    const r = await getRankings();
    setRankings(r.rankings || { large: [], mid: [], small: [] });
    setLastSynced(r.last_synced);
    const w = await getWishlist();
    setWishlist(w.items || []);
  };

  useEffect(() => { load().catch(() => {}); }, []);

  const onSearch = async (q) => {
    setSearch(q);
    const r = await searchStocks(q);
    setResults(r.results || []);
  };

  const openStock = async (ticker) => {
    const r = await getStock(ticker);
    setActive(r);
  };

  const addWish = async (ticker) => {
    const res = await saveWishlistItem({ ticker, note, tag });
    setWishlist(res.items || []);
  };

  const removeWish = async (ticker) => {
    const res = await deleteWishlistItem(ticker);
    setWishlist(res.items || []);
  };

  const sync = async () => {
    await syncData();
    await load();
  };

  const applyWeights = async () => {
    await recalc(weights);
    await load();
  };

  const segments = useMemo(() => ['large', 'mid', 'small'], []);

  return (
    <div className="container">
      <h1>India-Only NSE/BSE AlphaScore Dashboard</h1>
      <p>Last synced: {lastSynced || 'Not synced yet'} </p>
      <div className="row">
        <button onClick={sync}>Manual Sync (NSE/BSE refresh)</button>
      </div>

      <section>
        <h2>Ranking Weights</h2>
        <div className="grid">
          {Object.keys(weights).map((k) => (
            <label key={k}>{k}
              <input type="number" step="0.01" value={weights[k]} onChange={(e) => setWeights({ ...weights, [k]: Number(e.target.value) })} />
            </label>
          ))}
        </div>
        <button onClick={applyWeights}>Recalculate AlphaScore</button>
      </section>

      <section>
        <h2>Top 10 by Market Cap Segment</h2>
        {segments.map((seg) => (
          <div key={seg}>
            <h3>{seg.toUpperCase()} CAP</h3>
            <div className="cards">
              {(rankings[seg] || []).map((s) => <StockCard key={s.ticker} stock={s} onOpen={openStock} onWish={addWish} />)}
            </div>
          </div>
        ))}
      </section>

      <section>
        <h2>Stock Search & Evaluation</h2>
        <input value={search} onChange={(e) => onSearch(e.target.value)} placeholder="Search NSE/BSE ticker or company" />
        <div className="cards">
          {results.map((s) => <StockCard key={s.ticker} stock={s} onOpen={openStock} onWish={addWish} />)}
        </div>
      </section>

      {active && (
        <section className="detail">
          <h2>{active.ticker} - {active.name}</h2>
          <p><strong>AlphaScore:</strong> {Number(active.alpha_score).toFixed(2)} | <strong>Last synced:</strong> {active.last_synced}</p>
          <ul>
            <li>PE: {active.pe_ratio}</li><li>Debt/Equity: {active.debt_to_equity}</li><li>ROE: {active.roe}</li>
            <li>ROA: {active.roa}</li><li>ROI: {active.roi}</li><li>Current Ratio: {active.current_ratio}</li>
            <li>Quick Ratio: {active.quick_ratio}</li><li>Op Margin: {active.operating_margin}</li><li>Net Margin: {active.net_margin}</li>
            <li>Revenue Growth: {active.revenue_growth}</li><li>Earnings Growth: {active.earnings_growth}</li>
          </ul>
          <h3>Why selected?</h3>
          <p>Selected by transparent weighted scoring of valuation, leverage, profitability, liquidity, cashflow, growth, ownership, and qualitative news signal.</p>
          <h3>Recent News Summaries</h3>
          <ul>
            {(active.news || []).map((n, i) => <li key={i}><a href={n.link} target="_blank">{n.title}</a> ({n.publisher})</li>)}
          </ul>
        </section>
      )}

      <section>
        <h2>Wishlist</h2>
        <div className="row">
          <input placeholder="note" value={note} onChange={(e) => setNote(e.target.value)} />
          <input placeholder="tag" value={tag} onChange={(e) => setTag(e.target.value)} />
        </div>
        <table>
          <thead><tr><th>Ticker</th><th>Note</th><th>Tag</th><th>Action</th></tr></thead>
          <tbody>
            {wishlist.map((w) => (
              <tr key={w.ticker}>
                <td>{w.ticker}</td><td>{w.note}</td><td>{w.tag}</td>
                <td><button onClick={() => removeWish(w.ticker)}>Remove</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
