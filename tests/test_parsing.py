"""Parsers for live sources, exercised on fixed fixtures (no network)."""
import datetime as dt

from pipeline import build, ctgov, openfda, sec


def test_parse_date_precisions():
    assert build.parse_date("2026-11") == dt.date(2026, 11, 30)
    assert build.parse_date("2026-12") == dt.date(2026, 12, 31)
    assert build.parse_date("2027") == dt.date(2027, 12, 31)
    assert build.parse_date("2026-09-17") == dt.date(2026, 9, 17)
    assert build.parse_date(None) is None
    assert build.parse_date("not a date") is None


STUDY = {
    "hasResults": False,
    "protocolSection": {
        "identificationModule": {"nctId": "NCT06914895", "briefTitle": "A Study of Tirzepatide in T1D", "acronym": "SURPASS-T1D-1"},
        "statusModule": {"overallStatus": "ACTIVE_NOT_RECRUITING",
                         "primaryCompletionDateStruct": {"date": "2026-11", "type": "ESTIMATED"},
                         "completionDateStruct": {"date": "2027-01", "type": "ESTIMATED"},
                         "startDateStruct": {"date": "2025-05"},
                         "lastUpdatePostDateStruct": {"date": "2026-09-01"}},
        "designModule": {"phases": ["PHASE1", "PHASE2"], "enrollmentInfo": {"count": 905, "type": "ESTIMATED"}},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Eli Lilly and Company", "class": "INDUSTRY"}},
        "conditionsModule": {"conditions": ["Type 1 Diabetes"]},
    },
}


def test_ctgov_parse_fields():
    t = ctgov.parse(STUDY)
    assert t["nct_id"] == "NCT06914895"
    assert t["acronym"] == "SURPASS-T1D-1"
    assert t["status"] == "ACTIVE_NOT_RECRUITING"
    assert t["primary_completion"] == "2026-11" and t["primary_completion_type"] == "ESTIMATED"
    assert t["enrollment"] == 905
    assert t["phases"] == ["Phase 1", "Phase 2"]
    assert t["url"] == "https://clinicaltrials.gov/study/NCT06914895"


def test_ctgov_combined_phase_grades_conservatively():
    assert ctgov.parse(STUDY)["phase_grade"] == "phase1"


def test_ctgov_missing_modules_do_not_crash():
    bare = {"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}, "statusModule": {}}}
    t = ctgov.parse(bare)
    assert t["phase_grade"] is None and t["primary_completion"] is None and t["enrollment"] is None


def test_openfda_iso():
    assert openfda._iso("20260825") == "2026-08-25"
    assert openfda._iso("2026-08-25") == "2026-08-25"
    assert openfda._iso(None) is None


def test_sec_recent_filings_filters_forms(monkeypatch):
    class R:
        def __init__(self, data):
            self._d = data

        def json(self):
            return self._d
    sec._tickers = None
    tickers = {"0": {"ticker": "DXCM", "cik_str": 1093557}}
    subs = {"filings": {"recent": {
        "form": ["4", "8-K", "10-Q", "SC 13G", "10-K"],
        "filingDate": ["2026-10-01", "2026-09-14", "2026-08-01", "2026-07-01", "2026-02-01"],
        "accessionNumber": ["a-1", "0001093557-26-000175", "0001093557-26-000100", "x-1", "0001093557-26-000010"],
        "primaryDocument": ["f4.xml", "dxcm-8k.htm", "dxcm-10q.htm", "13g.htm", "dxcm-10k.htm"],
        "primaryDocDescription": ["", "8-K", "", "", "10-K"]}}}

    def fake_get(url, **kw):
        return R(tickers if "company_tickers" in url else subs)
    monkeypatch.setattr(sec, "get", fake_get)
    cik, out = sec.recent_filings("DXCM", n=3)
    assert cik == "0001093557"
    assert [f["form"] for f in out] == ["8-K", "10-Q", "10-K"]
    assert out[0]["url"] == "https://www.sec.gov/Archives/edgar/data/1093557/000109355726000175/dxcm-8k.htm"
    assert out[1]["description"] == "10-Q"
