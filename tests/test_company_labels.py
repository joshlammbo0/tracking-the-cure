"""Company metric labels: price/sales naming and date-aware earnings."""
import datetime as dt
import pathlib

from pipeline import render

TODAY = dt.date(2026, 11, 15)


def test_future_earnings_date_is_next():
    e = render.earnings_status({"next_earnings": "2026-11-24"}, [], TODAY)
    assert e["next"] == "2026-11-24" and e["last"] is None


def test_past_date_with_filing_is_last_reported_not_next():
    filings = [{"form": "10-Q", "date": "2026-10-29"}, {"form": "8-K", "date": "2026-09-14"}]
    e = render.earnings_status({"next_earnings": "2026-10-29"}, filings, TODAY)
    assert e["next"] is None and e["last"] == "2026-10-29" and e["last_form"] == "10-Q"


def test_past_date_without_filing_is_neither():
    e = render.earnings_status({"next_earnings": "2026-10-29"}, [{"form": "8-K", "date": "2026-09-01"}], TODAY)
    assert e == {"next": None, "last": None, "last_form": None}


def test_missing_date():
    assert render.earnings_status({}, [], TODAY)["next"] is None


def test_no_ev_sales_label_left():
    tpl = (pathlib.Path(__file__).resolve().parent.parent / "templates").rglob("*.html")
    assert not any("EV / sales" in p.read_text() for p in tpl)
