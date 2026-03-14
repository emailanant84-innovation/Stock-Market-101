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


class NewsSummary(BaseModel):
    title: str
    publisher: str | None = None
    link: str | None = None


def _safe(v: Any, default: float = np.nan) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


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


def fetch_stock_row(ticker: str, bucket: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    tk = yf.Ticker(ticker)
    info = tk.info or {}
    fast = tk.fast_info or {}

    hist = tk.history(period="1y", interval="1d")
    revenue_growth = _safe(info.get("revenueGrowth"), 0.0)
    earnings_growth = _safe(info.get("earningsGrowth"), 0.0)
    cfo = _safe(info.get("operatingCashflow"))

    news = []
    for n in (tk.news or [])[:6]:
        content = n.get("content", {})
        news.append(
            {
                "title": content.get("title") or n.get("title", ""),
                "publisher": content.get("provider", {}).get("displayName") or n.get("publisher"),
                "link": content.get("canonicalUrl", {}).get("url") or n.get("link"),
            }
        )

    close_now = _safe(fast.get("last_price"), _safe(info.get("currentPrice"), 0.0))
    close_prev = _safe(info.get("previousClose"), close_now)
    one_year_change = 0.0
    if not hist.empty:
        one_year_change = (hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1) * 100

    row = {
        "ticker": ticker,
        "name": info.get("longName") or info.get("shortName") or ticker,
        "exchange": "NSE/BSE",
        "market_cap_segment": bucket,
        "sector": info.get("sector", "Unknown"),
        "industry": info.get("industry", "Unknown"),
        "price": close_now,
        "prev_close": close_prev,
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
        "operating_cashflow": cfo,
        "free_cashflow": _safe(info.get("freeCashflow")),
        "revenue_growth": revenue_growth,
        "earnings_growth": earnings_growth,
        "one_year_change_pct": one_year_change,
        "promoter_holding": _safe(info.get("heldPercentInsiders")),
        "institutional_holding": _safe(info.get("heldPercentInstitutions")),
        "market_cap": _safe(info.get("marketCap")),
    }
    return row, news


def compute_scores(df: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    w_total = sum(weights.values()) or 1
    w = {k: v / w_total for k, v in weights.items()}

    out = df.copy()
    out["valuation_score"] = (1 / (out["pe_ratio"].replace(0, np.nan))).rank(pct=True).fillna(0.5) * 100
    out["leverage_score"] = (1 / (out["debt_to_equity"].replace(0, np.nan))).rank(pct=True).fillna(0.5) * 100
    out["profitability_score"] = out[["roe", "roa", "operating_margin", "net_margin"]].mean(axis=1).rank(pct=True).fillna(0.5) * 100
    out["liquidity_score"] = out[["current_ratio", "quick_ratio"]].mean(axis=1).rank(pct=True).fillna(0.5) * 100
    out["cashflow_score"] = out[["operating_cashflow", "free_cashflow"]].mean(axis=1).rank(pct=True).fillna(0.5) * 100
    out["growth_score"] = out[["revenue_growth", "earnings_growth", "one_year_change_pct"]].mean(axis=1).rank(pct=True).fillna(0.5) * 100
    out["ownership_score"] = out[["promoter_holding", "institutional_holding"]].mean(axis=1).rank(pct=True).fillna(0.5) * 100
    if "qualitative_score" not in out.columns:
        out["qualitative_score"] = 50.0

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
    return {"last_synced": None}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/sync")
def sync_data() -> dict[str, Any]:
    all_rows: list[dict[str, Any]] = []
    all_news: dict[str, list[dict[str, str]]] = {}

    for bucket, tickers in UNIVERSE.items():
        for ticker in tickers:
            try:
                row, news = fetch_stock_row(ticker, bucket)
                row["qualitative_score"] = _qualitative_score([n.get("title", "") for n in news])
                all_rows.append(row)
                all_news[ticker] = news
            except Exception:
                continue

    if not all_rows:
        raise HTTPException(status_code=500, detail="No stock data fetched. Check internet connection.")

    df = pd.DataFrame(all_rows)
    scored = compute_scores(df, DEFAULT_WEIGHTS).sort_values("alpha_score", ascending=False)
    scored.to_csv(DATA_FILE, index=False)
    NEWS_FILE.write_text(json.dumps(all_news, indent=2))
    META_FILE.write_text(json.dumps({"last_synced": datetime.now(timezone.utc).isoformat()}, indent=2))

    return {
        "rows": len(scored),
        "last_synced": load_meta()["last_synced"],
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
    return {"rankings": by_seg, "last_synced": load_meta().get("last_synced")}


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
    return data


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
