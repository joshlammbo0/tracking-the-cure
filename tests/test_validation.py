"""Curated-data validation: the rules build.validate() enforces, and the real YAML passing them."""
import copy

import yaml

from pipeline import build
from conftest import ROOT


def good_program(**kw):
    p = {"id": "x-1", "section": "cure", "approach": "immune", "name": "X", "company": "Co", "stage": "phase2",
         "evidence": "phase1", "status": "active", "summary": "s", "reality_check": "r",
         "sources": [{"label": "l", "url": "https://example.org"}], "verified_on": "2026-10-01", "nct_ids": ["NCT01234567"]}
    p.update(kw)
    return p


def test_valid_record_passes():
    assert build.validate([good_program()], [], {}) == []


def test_missing_field_reported():
    p = good_program()
    del p["reality_check"]
    assert any("missing 'reality_check'" in e for e in build.validate([p], [], {}))


def test_unknown_grade_rejected():
    assert any("not in" in e for e in build.validate([good_program(stage="phase4")], [], {}))


def test_evidence_cannot_lead_stage():
    errs = build.validate([good_program(stage="phase1", evidence="phase3")], [], {})
    assert any("evidence cannot be ahead of stage" in e for e in errs)


def test_bad_nct_id_and_duplicate_id():
    errs = build.validate([good_program(nct_ids=["NCT123"]), good_program(nct_ids=[])], [], {})
    assert any("bad NCT id" in e for e in errs)
    assert any("duplicate id" in e for e in errs)


def test_cure_program_needs_known_approach():
    assert any("approach must be" in e for e in build.validate([good_program(approach="magic")], [], {}))


def test_note_keys_must_exist():
    notes = {"programs": {"nope": {"commentary": "x"}}, "devices": {"ghost": {"user_take": "y"}}}
    errs = build.validate([good_program()], [{"id": "dev"}], notes)
    assert any("program 'nope'" in e for e in errs)
    assert any("device 'ghost'" in e for e in errs)


def test_committed_yaml_is_valid():
    progs = yaml.safe_load(open(ROOT / "data/programs.yaml"))["programs"]
    devs = yaml.safe_load(open(ROOT / "data/devices.yaml"))["devices"]
    notes = yaml.safe_load(open(ROOT / "data/my_notes.yaml")) or {}
    assert build.validate(progs, devs, notes) == []


def test_every_record_cites_a_source():
    progs = yaml.safe_load(open(ROOT / "data/programs.yaml"))["programs"]
    devs = yaml.safe_load(open(ROOT / "data/devices.yaml"))["devices"]
    for rec in progs + devs:
        assert rec.get("sources"), rec["id"]
        for s in rec["sources"]:
            assert s["url"].startswith("http"), (rec["id"], s)


def test_company_exposure_is_sourced_or_labelled():
    comps = yaml.safe_load(open(ROOT / "data/companies.yaml"))["companies"]
    for c in comps:
        if "exposure" in c:
            assert c.get("exposure_basis") in {"disclosed", "derived", "assumption"}, c["ticker"]
            assert c.get("exposure_note"), c["ticker"]
            assert all(0 < v <= 1 for v in c["exposure"].values()), c["ticker"]
            if c["exposure_basis"] in {"disclosed", "derived"} and not c.get("exposure_derived_from"):
                assert c.get("exposure_source", "").startswith("http"), c["ticker"]


def test_market_scenarios_complete():
    m = yaml.safe_load(open(ROOT / "data/market.yaml"))
    for k in ("bear", "base", "bull", "immuno"):
        sc = m["scenarios"][k]
        for f in ("label", "approval", "peak", "ramp", "price", "cap", "residual"):
            assert f in sc, (k, f)
