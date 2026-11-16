"""Approved therapies must carry an outcome label, so an approval is never presented as a cure."""
from pipeline import build, render


def test_approved_programs_need_outcome_label():
    p = {"id": "x", "section": "cure", "approach": "immune", "name": "X", "company": "C", "stage": "approved",
         "evidence": "approved", "status": "active", "summary": "s", "reality_check": "r",
         "sources": [{"label": "l", "url": "https://e.org"}], "verified_on": "2026-10-01"}
    assert any("outcome_label" in e for e in build.validate([p], [], {}))
    assert not any("outcome_label" in e for e in build.validate([dict(p, outcome_label="Delays onset")], [], {}))


def test_homepage_shows_outcome_for_each_approved_therapy(tmp_path):
    out = tmp_path / "site"
    render.render(out)
    html = (out / "index.html").read_text()
    D = render.load_all()
    approved = [p for p in D["programs"] if p["section"] == "cure" and p["status"] == "active" and p["stage"] == "approved"]
    assert approved
    for p in approved:
        assert p["outcome_label"] in html.replace("&#39;", "'"), p["id"]
