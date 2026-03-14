LARGE_CAP = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "SUNPHARMA.NS"
]

MID_CAP = [
    "LODHA.NS", "VOLTAS.NS", "BSE.NS", "AUBANK.NS", "MPHASIS.NS",
    "MUTHOOTFIN.NS", "POLYCAB.NS", "TORNTPHARM.NS", "PERSISTENT.NS", "COFORGE.NS",
    "PAGEIND.NS", "DIXON.NS", "GODREJPROP.NS", "HAVELLS.NS", "ABFRL.NS"
]

SMALL_CAP = [
    "IDEA.NS", "IRFC.NS", "RAILTEL.NS", "SWSOLAR.NS", "JWL.NS",
    "HFCL.NS", "EASEMYTRIP.NS", "RITES.NS", "TANLA.NS", "SOBHA.NS",
    "KNRCON.NS", "AETHER.NS", "KAYNES.NS", "LATENTVIEW.NS", "CYIENTDLM.NS"
]

UNIVERSE = {
    "large": LARGE_CAP,
    "mid": MID_CAP,
    "small": SMALL_CAP,
}

DEFAULT_WEIGHTS = {
    "valuation": 0.10,
    "leverage": 0.12,
    "profitability": 0.18,
    "liquidity": 0.08,
    "cashflow": 0.10,
    "growth": 0.20,
    "ownership": 0.10,
    "qualitative": 0.12,
}
