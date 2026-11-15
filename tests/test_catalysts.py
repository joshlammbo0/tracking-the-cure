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


def test_month_only_registry_dates_are_never_shown_as_a_day():
    import re
    D = render.load_all()
    checked = 0
    for r in rows():
        if r.get("origin") != "registry":
            continue
        raw = render.registry_date(r, D["trials"])
        if raw and len(raw) == 7:
            checked += 1
            assert r["month_only"] and r["when"] == r["short"] == render.fdate(raw, "month"), r["title"]
            assert not re.search(r"\b\d{1,2}\b ’|\d{1,2}, \d{4}", r["when"]), r["when"]
    assert checked  # the current data has month-only registry dates (e.g. SURPASS-T1D)


def test_month_only_ics_event_spans_the_month():
    text = render.ics(rows()).replace("\r\n ", "")
    ev = next(e for e in text.split("BEGIN:VEVENT")[1:] if "NCT06914895" in e)
    assert "DTSTART;VALUE=DATE:20261101" in ev and "DTEND;VALUE=DATE:20261201" in ev
    assert "month only" in ev


def test_program_next_catalyst_uses_registry_precision():
    D = render.load_all()
    render.enrich_programs(D)
    p = next(p for p in D["programs"] if p["id"] == "lilly-tirzepatide-t1d")
    assert p["next_label"] == "Nov 2026"
