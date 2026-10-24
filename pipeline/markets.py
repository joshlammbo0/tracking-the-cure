"""Stock data via yfinance (free, unofficial). Converts market caps to USD."""
import datetime as dt
import logging

import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.CRITICAL)
_fx = {}


def usd_rate(ccy):
    if not ccy or ccy == "USD":
        return 1.0
    if ccy not in _fx:
        try:
            _fx[ccy] = float(yf.Ticker("{}USD=X".format(ccy)).fast_info["lastPrice"])
        except Exception:
            _fx[ccy] = None
    return _fx[ccy]


def _ret(closes, days):
    if closes is None or len(closes) < 2:
        return None
    cutoff = closes.index[-1] - dt.timedelta(days=days)
    past = closes[closes.index <= cutoff]
    if past.empty:
        return None
    return float(closes.iloc[-1] / past.iloc[-1] - 1)


def _rev_usd(info, price_ccy):
    """Revenue is reported in the filer's currency (e.g. DKK for the Novo ADR), not the quote currency."""
    rev = info.get("totalRevenue")
    rate = usd_rate(info.get("financialCurrency") or price_ccy)
    return float(rev) * rate if rev and rate else None


def quote(ticker):
    t = yf.Ticker(ticker)
    fi = t.fast_info
    hist = t.history(period="2y", interval="1d", auto_adjust=True)
    closes = hist["Close"].dropna() if not hist.empty else None
    ccy = fi.get("currency")
    fx = usd_rate(ccy)
    mcap = fi.get("marketCap")
    ytd = None
    if closes is not None and len(closes):
        jan1 = closes[closes.index.year < closes.index[-1].year]
        if not jan1.empty:
            ytd = float(closes.iloc[-1] / jan1.iloc[-1] - 1)
    info = {}
    try:
        info = t.info or {}
    except Exception:
        pass
    earnings = None
    try:
        cal = t.calendar or {}
        ed = cal.get("Earnings Date")
        if ed:
            earnings = str(ed[0])
    except Exception:
        pass
    spark, history = [], []
    if closes is not None and len(closes):
        weekly = closes.iloc[::-5].iloc[::-1]  # every 5th session, anchored on the latest close
        history = [[str(i.date()), round(float(v), 4)] for i, v in weekly.items()]
        last_year = closes[closes.index >= closes.index[-1] - dt.timedelta(days=365)]
        spark = [round(float(v), 4) for v in last_year.iloc[::5]]
    return {
        "ticker": ticker,
        "currency": ccy,
        "price": float(fi.get("lastPrice")) if fi.get("lastPrice") else None,
        "market_cap_usd": float(mcap) * fx if mcap and fx else None,
        "ret_1m": _ret(closes, 30), "ret_ytd": ytd, "ret_1y": _ret(closes, 365),
        "revenue_ttm_usd": _rev_usd(info, ccy),
        "next_earnings": earnings,
        "spark": spark,
        "history": history,
        "as_of": str(closes.index[-1].date()) if closes is not None and len(closes) else None,
    }
