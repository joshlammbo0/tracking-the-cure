"""Catalyst terminology: registry completion dates are never labelled readouts, every event carries a date
provenance, and guidance windows are shown as the source words them."""
import yaml

from pipeline import build, render
from conftest import ROOT


def rows():
    D = render.load_all()
    render.enrich_programs(D)
    return render.catalyst_rows(D)


def test_curated_catalysts_validate():
    cats = yaml.safe_load(open(ROOT / "data/catalysts.yaml"))["catalysts"]
    assert build.validate_catalysts(cats) == []
    bad = [{"title": "x", "type": "readout", "provenance": "Rumour"}]
    assert len(build.validate_catalysts(bad)) == 2  # unknown provenance + readout without a source


def test_registry_dates_are_trial_completions_not_readouts():
    for r in rows():
        if r.get("origin") == "registry":
            assert r["type"] == "trial_completion" and r["type_label"] == "Trial completion", r["title"]
            assert r["provenance"] in ("Registry estimate", "Confirmed")


def test_every_event_has_a_provenance_label():
    allowed = build.PROVENANCE | {render.UNCLASSIFIED}
    for r in rows():
        assert r["prov_label"] in allowed, r["title"]


def test_guidance_windows_not_collapsed_to_a_date():
    for r in rows():
        if r.get("window"):
            assert r["when"] == r["window"] and r["short"] == r["window"], r["title"]
        if r.get("precision") == "guided":
            assert not r["when"].startswith("by "), r["title"]


def test_ics_titles_carry_type_and_provenance():
    text = render.ics(rows())
    summaries = [l for l in text.replace("\r\n ", "").split("\r\n") if l.startswith("SUMMARY:")]
    assert summaries and all(s.startswith("SUMMARY:[") and " · " in s.split("]")[0] for s in summaries)
    assert "[Readout" not in text
