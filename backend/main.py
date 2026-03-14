from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from universe import DEFAULT_WEIGHTS, UNIVERSE

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DATA_FILE = DATA_DIR / "latest_dataset.csv"
NEWS_FILE = DATA_DIR / "latest_news.json"
WISHLIST_FILE = DATA_DIR / "wishlist.json"
META_FILE = DATA_DIR / "meta.json"

CRUCIAL_FIELDS = [
    "price",
    "pe_ratio",
    "debt_to_equity",
    "roe",
    "roa",
    "roi",
    "interest_coverage",
    "current_ratio",
    "quick_ratio",
    "operating_margin",
    "net_margin",
    "operating_cashflow",
    "free_cashflow",
    "revenue_growth",
    "earnings_growth",
    "promoter_holding",
    "institutional_holding",
    "one_year_change_pct",
]

app = FastAPI(title="India Stock AlphaScore API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class WeightConfig(BaseModel):
    valuation: float = Field(default=DEFAULT_WEIGHTS["valuation"], ge=0)
    leverage: float = Field(default=DEFAULT_WEIGHTS["leverage"], ge=0)
    profitability: float = Field(default=DEFAULT_WEIGHTS["profitability"], ge=0)
    liquidity: float = Field(default=DEFAULT_WEIGHTS["liquidity"], ge=0)
    cashflow: float = Field(default=DEFAULT_WEIGHTS["cashflow"], ge=0)
    growth: float = Field(default=DEFAULT_WEIGHTS["growth"], ge=0)
    ownership: float = Field(default=DEFAULT_WEIGHTS["ownership"], ge=0)
    qualitative: float = Field(default=DEFAULT_WEIGHTS["qualitative"], ge=0)


class WishlistItem(BaseModel):
    ticker: str
    note: str = ""
    tag: str = ""


def _safe(v: Any, default: float = np.nan) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _is_valid_number(value: Any) -> bool:
    if value is None:
        return False
    try:
        return not bool(pd.isna(value)) and np.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _qualitative_score(texts: list[str]) -> float:
    if not texts:
        return 50.0
    pos_words = ["growth", "expansion", "record", "strong", "guidance", "pipeline", "order"]
    neg_words = ["decline", "weak", "delay", "loss", "downgrade", "concern", "risk"]
    joined = " ".join(t.lower() for t in texts)
    pos = sum(joined.count(w) for w in pos_words)
    neg = sum(joined.count(w) for w in neg_words)
    raw = 50 + (pos - neg) * 5
    return float(max(0, min(100, raw)))


def _extract_news(tk: yf.Ticker) -> list[dict[str, str]]:
    news: list[dict[str, str]] = []
    for n in (tk.news or [])[:8]:
        content = n.get("content", {})
        news.append(
            {
                "title": content.get("title") or n.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName") or n.get("publisher"),
                "link": content.get("canonicalUrl", {}).get("url") or n.get("link"),
            }
        )
    return news


def fetch_stock_row(ticker: str, bucket: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    fast = tk.fast_info or {}

    hist = tk.history(period="1y", interval="1d")
    one_year_change = np.nan
    if not hist.empty and len(hist["Close"]) > 1 and hist["Close"].iloc[0] != 0:
        one_year_change = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100

    close_now = _safe(fast.get("last_price"), _safe(info.get("currentPrice")))
    close_prev = _safe(info.get("previousClose"), close_now)

    row = {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "exchange": "NSE" if ticker.endswith(".NS") else "BSE" if ticker.endswith(".BO") else "NSE/BSE",
        "market_cap_segment": bucket,
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "price": close_now,
        "prev_close": close_prev,
        "price_change_pct": ((close_now - close_prev) / close_prev * 100) if _is_valid_number(close_prev) and close_prev != 0 else np.nan,
        "pe_ratio": _safe(info.get("trailingPE")),
        "debt_to_equity": _safe(info.get("debtToEquity")),
        "roe": _safe(info.get("returnOnEquity")),
        "roa": _safe(info.get("returnOnAssets")),
        "roi": _safe(info.get("returnOnInvestedCapital"), _safe(info.get("returnOnEquity"))),
        "interest_coverage": _safe(info.get("interestCoverage")),
        "current_ratio": _safe(info.get("currentRatio")),
        "quick_ratio": _safe(info.get("quickRatio")),
        "operating_margin": _safe(info.get("operatingMargins")),
        "net_margin": _safe(info.get("profitMargins")),
        "operating_cashflow": _safe(info.get("operatingCashflow")),
        "free_cashflow": _safe(info.get("freeCashflow")),
        "revenue_growth": _safe(info.get("revenueGrowth")),
        "earnings_growth": _safe(info.get("earningsGrowth")),
        "one_year_change_pct": one_year_change,
        "promoter_holding": _safe(info.get("heldPercentInsiders")),
        "institutional_holding": _safe(info.get("heldPercentInstitutions")),
        "market_cap": _safe(info.get("marketCap")),
    }

    news = _extract_news(tk)
    row["qualitative_score"] = _qualitative_score([n.get("title", "") for n in news])
    row["missing_crucial_fields"] = ",".join([f for f in CRUCIAL_FIELDS if not _is_valid_number(row.get(f))])
    row["has_complete_data"] = row["missing_crucial_fields"] == ""

    return row, news


def _ensure_complete_records(df: pd.DataFrame) -> pd.DataFrame:
    complete_df = df.copy()
    complete_df["missing_crucial_fields"] = complete_df.apply(
        lambda r: ",".join([f for f in CRUCIAL_FIELDS if not _is_valid_number(r.get(f))]),
        axis=1,
    )
    complete_df["has_complete_data"] = complete_df["missing_crucial_fields"] == ""
    return complete_df[complete_df["has_complete_data"]].copy()


def compute_scores(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    if df.empty:
        return df

    w_total = sum(weights.values()) or 1
    w = {k: v / w_total for k, v in weights.items()}

    out = df.copy()
    out["valuation_score"] = (1 / out["pe_ratio"]).rank(pct=True) * 100
    out["leverage_score"] = (1 / out["debt_to_equity"]).rank(pct=True) * 100
    out["profitability_score"] = out[["roe", "roa", "operating_margin", "net_margin"]].mean(axis=1).rank(pct=True) * 100
    out["liquidity_score"] = out[["current_ratio", "quick_ratio"]].mean(axis=1).rank(pct=True) * 100
    out["cashflow_score"] = out[["operating_cashflow", "free_cashflow"]].mean(axis=1).rank(pct=True) * 100
    out["growth_score"] = out[["revenue_growth", "earnings_growth", "one_year_change_pct"]].mean(axis=1).rank(pct=True) * 100
    out["ownership_score"] = out[["promoter_holding", "institutional_holding"]].mean(axis=1).rank(pct=True) * 100
    out["qualitative_score"] = out.get("qualitative_score", 50.0)

    out["alpha_score"] = (
        out["valuation_score"] * w["valuation"]
        + out["leverage_score"] * w["leverage"]
        + out["profitability_score"] * w["profitability"]
        + out["liquidity_score"] * w["liquidity"]
        + out["cashflow_score"] * w["cashflow"]
        + out["growth_score"] * w["growth"]
        + out["ownership_score"] * w["ownership"]
        + out["qualitative_score"] * w["qualitative"]
    )
    return out


def load_dataset() -> pd.DataFrame:
    if not DATA_FILE.exists():
        raise HTTPException(status_code=404, detail="Dataset not synced yet. Run /sync first.")
    return pd.read_csv(DATA_FILE)


def load_meta() -> dict[str, Any]:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text())
    return {"last_synced": None, "coverage": {}}


def _scoring_breakdown(row: pd.Series) -> dict[str, float]:
    return {
        "valuation": float(row.get("valuation_score", 0)),
        "leverage": float(row.get("leverage_score", 0)),
        "profitability": float(row.get("profitability_score", 0)),
        "liquidity": float(row.get("liquidity_score", 0)),
        "cashflow": float(row.get("cashflow_score", 0)),
        "growth": float(row.get("growth_score", 0)),
        "ownership": float(row.get("ownership_score", 0)),
        "qualitative": float(row.get("qualitative_score", 0)),
    }


def _candidate_symbols(query: str) -> list[str]:
    raw = query.strip().upper()
    if not raw:
        return []
    if raw.endswith(".NS") or raw.endswith(".BO"):
        return [raw]
    return [f"{raw}.NS", f"{raw}.BO"]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sync")
def sync_data() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    all_news: dict[str, list[dict[str, str]]] = {}
    attempted = 0

    for bucket, tickers in UNIVERSE.items():
        for ticker in tickers:
            attempted += 1
            try:
                row, news = fetch_stock_row(ticker, bucket)
                rows.append(row)
                all_news[ticker] = news
            except Exception:
                continue

    if not rows:
        raise HTTPException(status_code=500, detail="No stock data fetched. Check internet connection.")

    fetched_df = pd.DataFrame(rows)
    complete_df = _ensure_complete_records(fetched_df)

    if complete_df.empty:
        raise HTTPException(status_code=500, detail="No stocks had all crucial data points required for AlphaScore.")

    scored = compute_scores(complete_df, DEFAULT_WEIGHTS).sort_values("alpha_score", ascending=False)
    scored.to_csv(DATA_FILE, index=False)
    NEWS_FILE.write_text(json.dumps(all_news, indent=2))

    coverage = {
        "attempted": attempted,
        "fetched": int(len(fetched_df)),
        "eligible_complete_records": int(len(complete_df)),
    }
    META_FILE.write_text(
        json.dumps(
            {
                "last_synced": datetime.now(timezone.utc).isoformat(),
                "coverage": coverage,
            },
            indent=2,
        )
    )

    return {
        "rows": len(scored),
        "last_synced": load_meta().get("last_synced"),
        "coverage": coverage,
    }


@app.get("/metadata")
def metadata() -> dict[str, Any]:
    return load_meta()


@app.get("/rankings")
def rankings() -> dict[str, Any]:
    df = load_dataset()
    by_seg = {}
    for seg in ["large", "mid", "small"]:
        seg_df = df[df["market_cap_segment"] == seg].sort_values("alpha_score", ascending=False).head(10)
        by_seg[seg] = seg_df.to_dict(orient="records")
    meta = load_meta()
    return {"rankings": by_seg, "last_synced": meta.get("last_synced"), "coverage": meta.get("coverage", {})}


@app.post("/recalculate")
def recalculate(weights: WeightConfig) -> dict[str, Any]:
    df = load_dataset()
    scored = compute_scores(df, weights.model_dump()).sort_values("alpha_score", ascending=False)
    scored.to_csv(DATA_FILE, index=False)
    return {"ok": True, "weights": weights.model_dump()}


@app.get("/search")
def search(q: str = "") -> dict[str, Any]:
    df = load_dataset()
    s = q.lower().strip()
    if not s:
        filtered = df.head(25)
    else:
        filtered = df[df["ticker"].str.lower().str.contains(s) | df["name"].str.lower().str.contains(s)]
    return {"results": filtered.sort_values("alpha_score", ascending=False).head(25).to_dict(orient="records")}


@app.get("/stock/{ticker}")
def stock_detail(ticker: str) -> dict[str, Any]:
    df = load_dataset()
    row = df[df["ticker"].str.lower() == ticker.lower()]
    if row.empty:
        raise HTTPException(status_code=404, detail="Ticker not found in India universe")

    news_map = json.loads(NEWS_FILE.read_text()) if NEWS_FILE.exists() else {}
    data = row.iloc[0].to_dict()
    data["news"] = news_map.get(data["ticker"], [])
    data["last_synced"] = load_meta().get("last_synced")
    data["score_breakdown"] = _scoring_breakdown(row.iloc[0])
    data["source_references"] = {
        "nse": f"https://www.nseindia.com/get-quotes/equity?symbol={data['ticker'].split('.')[0]}",
        "bse": f"https://www.bseindia.com/stock-share-price/stockreach_financials.aspx?scripcode={data['ticker'].split('.')[0]}",
        "yahoo": f"https://finance.yahoo.com/quote/{data['ticker']}",
    }
    return data


@app.get("/evaluate-live")
def evaluate_live(query: str) -> dict[str, Any]:
    symbols = _candidate_symbols(query)
    if not symbols:
        raise HTTPException(status_code=400, detail="Provide stock symbol, e.g., TCS or TCS.NS")

    errors: list[str] = []
    live_row = None
    live_news: list[dict[str, str]] = []

    for symbol in symbols:
        try:
            row, news = fetch_stock_row(symbol, "searched")
            if not row["has_complete_data"]:
                raise ValueError(f"Missing crucial fields: {row['missing_crucial_fields']}")
            live_row = row
            live_news = news
            break
        except Exception as exc:
            errors.append(f"{symbol}: {str(exc)}")

    if live_row is None:
        raise HTTPException(status_code=404, detail="Could not evaluate stock with complete data. " + " | ".join(errors))

    try:
        base_df = load_dataset()
    except HTTPException:
        base_df = pd.DataFrame()

    combined = pd.concat([base_df, pd.DataFrame([live_row])], ignore_index=True)
    scored = compute_scores(combined, DEFAULT_WEIGHTS)
    scored_row = scored[scored["ticker"] == live_row["ticker"]].iloc[-1]

    result = scored_row.to_dict()
    result["news"] = live_news
    result["last_synced"] = datetime.now(timezone.utc).isoformat()
    result["score_breakdown"] = _scoring_breakdown(scored_row)
    symbol = result["ticker"].split(".")[0]
    result["source_references"] = {
        "nse": f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
        "bse": f"https://www.bseindia.com/stock-share-price/stockreach_financials.aspx?scripcode={symbol}",
        "yahoo": f"https://finance.yahoo.com/quote/{result['ticker']}",
    }
    return {"stock": result}


def read_wishlist() -> list[dict[str, str]]:
    if not WISHLIST_FILE.exists():
        return []
    return json.loads(WISHLIST_FILE.read_text())


@app.get("/wishlist")
def get_wishlist() -> dict[str, Any]:
    return {"items": read_wishlist()}


@app.post("/wishlist")
def add_or_update_wishlist(item: WishlistItem) -> dict[str, Any]:
    items = read_wishlist()
    items = [i for i in items if i["ticker"].lower() != item.ticker.lower()]
    items.append(item.model_dump())
    WISHLIST_FILE.write_text(json.dumps(items, indent=2))
    return {"items": items}


@app.delete("/wishlist/{ticker}")
def delete_wishlist_item(ticker: str) -> dict[str, Any]:
    items = [i for i in read_wishlist() if i["ticker"].lower() != ticker.lower()]
    WISHLIST_FILE.write_text(json.dumps(items, indent=2))
    return {"items": items}
