# India Stock AlphaScore (NSE/BSE, local-hosted)

React + FastAPI app to scan Indian stocks (NSE/BSE universe), normalize financial indicators, derive transparent AlphaScore rankings for Large/Mid/Small cap, and maintain a persistent wishlist.

## What it includes
- India-only universe split into large/mid/small cap buckets.
- Manual **Sync** button to refresh prices, ratios, growth metrics, news, and metadata from `yfinance`.
- Strict eligibility filter: AlphaScore is computed only for stocks that have all crucial financial datapoints available (no critical missing values).
- Transparent factor scoring and editable weights:
  - valuation (PE), leverage (D/E), profitability (ROE/ROA/margins), liquidity (current/quick ratio), cash flow, growth, ownership, qualitative news signal.
- Top-10 tables for each segment based on latest synced data.
- Professional dark-themed dashboard with expandable/collapsible stock panels, latest price visibility, and factor-level breakdown.
- Search + stock detail evaluation using the exact same AlphaScore model.
- Live search button that evaluates any NSE/BSE ticker in real time and computes AlphaScore immediately if complete data is available.
- Wishlist with add/update/remove and persistent storage (`backend/data/wishlist.json`).
- Last synced timestamp shown in dashboard and stock detail pages.

## Tech stack
- Backend: FastAPI + pandas + yfinance
- Frontend: React (Vite)
- Storage: local CSV/JSON files under `backend/data`

## Run locally (Windows PowerShell)
### 1) Backend
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2) Frontend (new terminal)
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`.

## Single-click launcher (Windows)
From the project root, just double-click `start_app.bat` or run:
```powershell
.\start_app.bat
```
What it does:
- Creates backend virtual environment if missing.
- Installs backend/frontend dependencies (first run).
- Opens two PowerShell windows (backend + frontend).
- Opens the dashboard in your browser.

Faster subsequent launches (skip installs):
```powershell
.\start_app.bat --skip-install
```

## API endpoints
- `POST /sync` - fetches/refreshes NSE/BSE-backed universe data.
- `GET /rankings` - top 10 per cap segment + last sync.
- `POST /recalculate` - recalculates AlphaScore using custom weights.
- `GET /search?q=` - autocomplete/lookup across India universe.
- `GET /evaluate-live?query=` - real-time stock pull (NSE/BSE symbol match) and AlphaScore calculation.
- `GET /stock/{ticker}` - detailed scoring + recent news summaries.
- `GET|POST|DELETE /wishlist` - persistent wishlist operations.

## Notes
- This is designed for local research use and depends on upstream market-data availability.
- Universe is currently seeded with representative NSE tickers and can be expanded easily in `backend/universe.py`.
