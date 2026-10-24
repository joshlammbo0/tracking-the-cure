"""SEC EDGAR: map tickers to CIKs and list recent material filings."""
from .http import get

FORMS = {"10-K", "10-Q", "8-K", "20-F", "6-K", "S-1", "424B4", "424B5", "S-4"}
_tickers = None


def cik_for(ticker):
    global _tickers
    if _tickers is None:
        data = get("https://www.sec.gov/files/company_tickers.json", min_interval=0.15, key="sec").json()
        _tickers = {v["ticker"].upper(): str(v["cik_str"]).zfill(10) for v in data.values()}
    return _tickers.get(ticker.upper())


def recent_filings(ticker, n=4):
    cik = cik_for(ticker)
    if not cik:
        return None, []
    d = get("https://data.sec.gov/submissions/CIK{}.json".format(cik), min_interval=0.15, key="sec").json()
    rec = d["filings"]["recent"]
    out = []
    for form, date, acc, doc, desc in zip(rec["form"], rec["filingDate"], rec["accessionNumber"],
                                          rec["primaryDocument"], rec["primaryDocDescription"]):
        if form not in FORMS:
            continue
        out.append({
            "form": form, "date": date, "description": desc or form,
            "url": "https://www.sec.gov/Archives/edgar/data/{}/{}/{}".format(int(cik), acc.replace("-", ""), doc),
        })
        if len(out) >= n:
            break
    return cik, out
