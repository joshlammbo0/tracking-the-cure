"""Cure Impact Model: how much T1D-driven CGM, pump and insulin revenue would a functional
cure displace, and how large could the cure itself be?

This module is the single source of truth for every model number printed in the HTML
(homepage, model page, sensitivity tables, company read-across, research notes, CSV).
site/assets/model.js re-implements `run()` line for line so the sliders can recompute in
the browser; tests/test_model.py pins the formula and the QA pass checks the two agree.

Mechanics (also written out on the model page):
  baseline_m(y)  = size_m(2025) x (1 + CAGR_m)^(y - 2025)
  target(y)      = 0 before approval, else peak x S((y - approval + 1) / ramp) x T1D population
                   where S(t) = 3t^2 - 2t^3 clamped to [0, 1] (a smooth S-curve)
  cured(y)       = min(target(y), cured(y-1) + capacity)     (capacity caps patients/year)
  penetration(y) = cured(y) / T1D population
  displaced CGM  = baseline x T1D share x penetration x (1 - residual CGM use)
  displaced pump / insulin = baseline x T1D share x penetration
  cure sales(y)  = newly treated(y) x one-time price
"""
import csv
import io

START, END = 2025, 2040
MARKETS = ("insulin", "cgm", "pump")
SCENARIO_ORDER = ("bear", "base", "bull", "immuno")

# Sensitivity axes (approval year x peak share; price x capacity).
SENS_APPROVAL = [2028, 2030, 2031, 2032, 2034, 2036]
SENS_PEAK = [0.05, 0.10, 0.15, 0.25, 0.35]
SENS_PRICE = [250000, 500000, 750000, 1000000, 1500000]
SENS_CAP = [10000, 25000, 40000, 75000, 150000]


def default_inputs(market, scenario="base"):
    """Scenario levers from market.yaml plus the sourced/assumed market parameters."""
    sc = market["scenarios"][scenario]
    a, mk = market["assumptions"], market["markets"]
    return {
        "approval": int(sc["approval"]), "peak": float(sc["peak"]), "ramp": int(sc["ramp"]),
        "cap": float(sc["cap"]), "price": float(sc["price"]), "residual": float(sc["residual"]),
        "sh_cgm": float(a["t1d_share_cgm"]["value"]), "sh_pump": float(a["t1d_share_pump"]["value"]),
        "sh_ins": float(a["t1d_share_insulin"]["value"]),
        "g_cgm": float(mk["cgm"]["cagr"]), "g_pump": float(mk["pump"]["cagr"]), "g_ins": float(mk["insulin"]["cagr"]),
        "size": "value",
    }


def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def run(market, v):
    """Run the model for inputs `v`. Returns per-year rows plus headline outputs."""
    mk = market["markets"]
    base_year = int(market["base_year"])
    pop = float(market["population"]["t1d_global_m"]) * 1e6
    size = v.get("size", "value")
    rows, prev = [], 0.0
    for y in range(START, END + 1):
        t = y - base_year
        b = {
            "cgm": mk["cgm"][size] * 1e9 * (1 + v["g_cgm"]) ** t,
            "pump": mk["pump"][size] * 1e9 * (1 + v["g_pump"]) ** t,
            "insulin": mk["insulin"][size] * 1e9 * (1 + v["g_ins"]) ** t,
        }
        target = 0.0 if y < v["approval"] else v["peak"] * _smooth((y - v["approval"] + 1) / v["ramp"]) * pop
        cured = min(target, prev + v["cap"])
        p = cured / pop
        t1d = {"cgm": b["cgm"] * v["sh_cgm"], "pump": b["pump"] * v["sh_pump"], "insulin": b["insulin"] * v["sh_ins"]}
        disp = {"cgm": t1d["cgm"] * p * (1 - v["residual"]), "pump": t1d["pump"] * p, "insulin": t1d["insulin"] * p}
        new = max(0.0, cured - prev)
        rows.append({
            "year": y, "penetration": p, "cured": cured, "new_patients": new,
            "baseline": b, "t1d_baseline": t1d, "displaced": disp,
            "displaced_total": disp["cgm"] + disp["pump"] + disp["insulin"],
            "t1d_baseline_total": t1d["cgm"] + t1d["pump"] + t1d["insulin"],
            "cure_sales": new * v["price"],
        })
        prev = cured
    return {"inputs": dict(v), "rows": rows, "summary": summarize(rows)}


def summarize(rows):
    by = {r["year"]: r for r in rows}
    peak = max(rows, key=lambda r: r["cure_sales"])
    out = {}
    for y in (2030, 2035, 2040):
        r = by[y]
        out[str(y)] = {
            "displaced": dict(r["displaced"]), "displaced_total": r["displaced_total"],
            "share_of_t1d": r["displaced_total"] / r["t1d_baseline_total"] if r["t1d_baseline_total"] else 0.0,
            "penetration": r["penetration"], "cured": r["cured"], "cure_sales": r["cure_sales"],
        }
    out["peak_cure_sales"] = peak["cure_sales"]
    out["peak_cure_year"] = peak["year"] if peak["cure_sales"] > 0 else None
    out["cum_cure_sales"] = sum(r["cure_sales"] for r in rows)
    out["cum_displaced"] = sum(r["displaced_total"] for r in rows)
    first = next((r for r in rows if r["displaced_total"] > 0), None)
    out["first_displacement_year"] = first["year"] if first else None
    return out


def sensitivity(market, v):
    """Two grids around inputs v: 2040 displaced revenue, and cumulative cure sales."""
    g1 = []
    for ap in SENS_APPROVAL:
        g1.append([run(market, dict(v, approval=ap, peak=pk))["summary"]["2040"]["displaced_total"] for pk in SENS_PEAK])
    g2 = []
    for pr in SENS_PRICE:
        g2.append([run(market, dict(v, price=pr, cap=cp))["summary"]["cum_cure_sales"] for cp in SENS_CAP])
    return {
        "approval_peak": {"rows": SENS_APPROVAL, "cols": SENS_PEAK, "values": g1,
                          "metric": "Total displaced revenue in 2040"},
        "price_capacity": {"rows": SENS_PRICE, "cols": SENS_CAP, "values": g2,
                           "metric": "Cumulative cure sales, 2025-2040"},
    }


# ------------------------------------------------------------------ company read-across
def company_exposure(companies):
    """Resolve each company's revenue split by modelled market. Returns {ticker: info}."""
    by = {c["ticker"]: c for c in companies}
    out = {}
    for c in companies:
        basis = c.get("exposure_basis")
        if not basis:
            continue
        exp = dict(c.get("exposure") or {})
        rev = ((c.get("quote") or {}).get("revenue_ttm_usd"))
        note = c.get("exposure_note")
        src = c.get("exposure_derived_from")
        if src:
            sub = by.get(src) or {}
            sub_rev = (sub.get("quote") or {}).get("revenue_ttm_usd")
            sub_exp = sub.get("exposure") or {}
            if sub_rev and rev:
                share = sub_rev / rev
                exp = {m: share * f for m, f in sub_exp.items()}
            else:
                exp = {}
        out[c["ticker"]] = {"exposure": exp, "basis": basis if exp else "unknown", "note": note,
                            "source": c.get("exposure_source"), "revenue": rev}
    return out


def read_across(companies, market, v, years=(2030, 2035, 2040)):
    """Displaced revenue per company, assuming each company holds its share of each market.

    displaced_c(y) = sum_m [ current revenue x exposure_m x (1+CAGR_m)^(y-base) x T1D share_m
                             x penetration(y) x (1 - residual if CGM) ]
    expressed in dollars and as % of the company's CURRENT (TTM) revenue.
    """
    res = run(market, v)
    by = {r["year"]: r for r in res["rows"]}
    base_year = int(market["base_year"])
    share = {"cgm": v["sh_cgm"], "pump": v["sh_pump"], "insulin": v["sh_ins"]}
    growth = {"cgm": v["g_cgm"], "pump": v["g_pump"], "insulin": v["g_ins"]}
    exposures = company_exposure(companies)
    out = []
    for c in companies:
        info = exposures.get(c["ticker"])
        if not info:
            continue
        rev, exp = info["revenue"], info["exposure"]
        row = {"ticker": c["ticker"], "name": c["name"], "group": c.get("group"), "revenue": rev,
               "exposure": exp, "basis": info["basis"], "note": info["note"], "source": info["source"],
               "t1d_share_of_rev": sum(exp.get(m, 0) * share[m] for m in MARKETS) if exp else None,
               "years": {}}
        for y in years:
            r = by[y]
            if not rev or not exp:
                row["years"][str(y)] = None
                continue
            d = 0.0
            for m, f in exp.items():
                keep = (1 - v["residual"]) if m == "cgm" else 1.0
                d += rev * f * (1 + growth[m]) ** (y - base_year) * share[m] * r["penetration"] * keep
            row["years"][str(y)] = {"displaced": d, "pct_current_rev": d / rev}
        out.append(row)
    return out


def classify(row):
    exp = row["exposure"] or {}
    tot = sum(exp.values())
    if not exp:
        return "Not modelled"
    if tot >= 0.95:
        return "Pure-play"
    return "Diversified"


# ------------------------------------------------------------------ exports
def to_csv(market, results):
    """Year-by-year outputs for every scenario, one CSV."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["scenario", "year", "t1d_patients_cured", "share_of_t1d_cured", "new_patients_treated",
                "insulin_displaced_usd", "cgm_displaced_usd", "pump_displaced_usd", "total_displaced_usd",
                "t1d_attributable_baseline_usd", "cure_sales_usd"])
    for key, res in results.items():
        for r in res["rows"]:
            w.writerow([key, r["year"], round(r["cured"]), round(r["penetration"], 6), round(r["new_patients"]),
                        round(r["displaced"]["insulin"]), round(r["displaced"]["cgm"]), round(r["displaced"]["pump"]),
                        round(r["displaced_total"]), round(r["t1d_baseline_total"]), round(r["cure_sales"])])
    return buf.getvalue()


def to_json(market, companies):
    """Everything the model page needs: inputs, scenario outputs, sensitivity, read-across."""
    results = {k: run(market, default_inputs(market, k)) for k in SCENARIO_ORDER}
    base = default_inputs(market, "base")
    return {
        "start": START, "end": END,
        "scenarios": {k: {"label": market["scenarios"][k]["label"], "thesis": market["scenarios"][k].get("thesis"),
                          "inputs": results[k]["inputs"], "summary": results[k]["summary"]} for k in SCENARIO_ORDER},
        "base_rows": results["base"]["rows"],
        "sensitivity": sensitivity(market, base),
        "read_across": {k: read_across(companies, market, default_inputs(market, k)) for k in SCENARIO_ORDER},
    }, results
