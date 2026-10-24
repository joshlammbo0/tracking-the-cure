"""Cure Impact Model: pinned outputs and invariants. Every model number on the site comes from here."""
import math

import pytest
import yaml

from pipeline import model
from conftest import ROOT

MARKET = yaml.safe_load(open(ROOT / "data/market.yaml"))


def run(scenario="base", **over):
    v = model.default_inputs(MARKET, scenario)
    v.update(over)
    return model.run(MARKET, v)


def test_nothing_displaced_before_approval():
    res = run()
    approval = res["inputs"]["approval"]
    for r in res["rows"]:
        if r["year"] < approval:
            assert r["displaced_total"] == 0 and r["cure_sales"] == 0


def test_capacity_caps_new_patients():
    res = run()
    cap = res["inputs"]["cap"]
    assert all(r["new_patients"] <= cap + 1e-6 for r in res["rows"])


def test_penetration_never_exceeds_peak():
    res = run("bull")
    assert max(r["penetration"] for r in res["rows"]) <= res["inputs"]["peak"] + 1e-12


def test_residual_cgm_use_reduces_only_cgm():
    a, b = run(residual=0.0), run(residual=0.5)
    ra, rb = a["rows"][-1], b["rows"][-1]
    assert math.isclose(rb["displaced"]["cgm"], ra["displaced"]["cgm"] * 0.5)
    assert ra["displaced"]["pump"] == rb["displaced"]["pump"]


def test_cure_sales_equal_new_patients_times_price():
    res = run()
    p = res["inputs"]["price"]
    for r in res["rows"]:
        assert math.isclose(r["cure_sales"], r["new_patients"] * p)


@pytest.mark.parametrize("scenario,d2035,d2040,peak", [
    ("base", 0.864, 3.16, 20.0),
    ("bull", 5.01, 15.63, 60.0),
    ("bear", 0.09, 0.69, 11.2),
    ("immuno", 0.16, 0.43, 5.0),
])
def test_pinned_scenario_outputs(scenario, d2035, d2040, peak):
    """Guards against accidental formula changes. Update deliberately if market.yaml changes."""
    s = run(scenario)["summary"]
    assert round(s["2035"]["displaced_total"] / 1e9, 2 if d2035 >= 0.1 else 2) == pytest.approx(d2035, abs=0.01)
    assert round(s["2040"]["displaced_total"] / 1e9, 2) == pytest.approx(d2040, abs=0.01)
    assert round(s["peak_cure_sales"] / 1e9, 1) == pytest.approx(peak, abs=0.1)


def test_sensitivity_monotone_in_peak_share():
    g = model.sensitivity(MARKET, model.default_inputs(MARKET))["approval_peak"]
    for row in g["values"]:
        assert row == sorted(row)


def test_read_across_scales_with_exposure():
    comps = [
        {"ticker": "A", "name": "A", "exposure": {"pump": 1.0}, "exposure_basis": "assumption", "exposure_note": "n", "quote": {"revenue_ttm_usd": 1e9}},
        {"ticker": "B", "name": "B", "exposure": {"pump": 0.5}, "exposure_basis": "assumption", "exposure_note": "n", "quote": {"revenue_ttm_usd": 1e9}},
        {"ticker": "C", "name": "C", "exposure_basis": "unknown", "exposure_note": "n", "quote": {"revenue_ttm_usd": 1e9}},
    ]
    rows = {r["ticker"]: r for r in model.read_across(comps, MARKET, model.default_inputs(MARKET))}
    a, b = rows["A"]["years"]["2040"]["pct_current_rev"], rows["B"]["years"]["2040"]["pct_current_rev"]
    assert math.isclose(a, 2 * b)
    assert rows["C"]["years"]["2040"] is None


def test_derived_exposure_uses_subsidiary_revenue():
    comps = [
        {"ticker": "SUB", "name": "Sub", "exposure": {"pump": 1.0}, "exposure_basis": "assumption", "quote": {"revenue_ttm_usd": 2e9}},
        {"ticker": "PAR", "name": "Parent", "exposure_derived_from": "SUB", "exposure_basis": "derived", "quote": {"revenue_ttm_usd": 8e9}},
    ]
    ex = model.company_exposure(comps)
    assert math.isclose(ex["PAR"]["exposure"]["pump"], 0.25)


def test_csv_has_every_scenario_year():
    results = {k: run(k) for k in model.SCENARIO_ORDER}
    lines = model.to_csv(MARKET, results).strip().splitlines()
    assert len(lines) == 1 + len(model.SCENARIO_ORDER) * (model.END - model.START + 1)
