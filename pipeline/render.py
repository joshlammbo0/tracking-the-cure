"""Static site generator: curated YAML + site/data/*.json -> real HTML pages in _site/.

Run after the data step:
    python -m pipeline.build [--offline]
    python -m pipeline.render
    python -m http.server 8765 -d _site

Every number printed in the HTML comes from the data files or from pipeline/model.py.
Nothing here fetches from the network, so the render is identical online and offline.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup

from . import charts, model, og
from .build import GRADES, ACTIVE, parse_date

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SRC = ROOT / "site"
TPL = ROOT / "templates"
OUT = ROOT / "_site"

SITE_URL = os.environ.get("SITE_URL", "https://joshlammbo0.github.io/tracking-the-cure/")
SITE_NAME = "Tracking the Cure"

GRADE_LABEL = {"preclinical": "Preclinical", "phase1": "Phase 1", "phase2": "Phase 2", "phase3": "Phase 3",
               "filed": "Filed", "approved": "Approved"}
GRADE_SHORT = {"preclinical": "Preclin.", "phase1": "Ph 1", "phase2": "Ph 2", "phase3": "Ph 3", "filed": "Filed", "approved": "Appr."}
APPROACH = {
    "cell_replacement": ("Cell replacement",
                         "Replace lost beta cells with donor or stem-cell-derived islets. Works today, but needs chronic immunosuppression."),
    "gene_edited": ("Gene-edited / immune-evasive cells",
                    "Engineer cells to hide from the immune system so no immunosuppression is needed. This is the 'real cure' thesis, and the earliest stage."),
    "encapsulation": ("Encapsulation & devices",
                      "Physically shield cells inside a device. Historically hard: cells starve for oxygen, or the body walls the device off."),
    "immune": ("Immune / disease-modifying",
               "Stop or slow the autoimmune attack. Today these delay or preserve function; none is a cure."),
}
GLP_TOPIC = {"adjunct": "Add-on therapy trials", "beta_cell": "Beta-cell preservation", "safety": "Safety & history"}
CAT_TYPE = {"conference": "Conference", "fda": "FDA", "readout": "Readout", "company": "Company",
            "launch": "Launch", "earnings": "Earnings"}
STATUS_LABEL = {
    "RECRUITING": "Recruiting", "NOT_YET_RECRUITING": "Not yet recruiting", "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
    "ENROLLING_BY_INVITATION": "Enrolling by invitation", "COMPLETED": "Completed", "TERMINATED": "Terminated",
    "WITHDRAWN": "Withdrawn", "SUSPENDED": "Suspended", "UNKNOWN": "Unknown",
}
DEVICE_STATUS = {"marketed": "Marketed", "cleared_not_launched": "Cleared, not launched", "pipeline": "Pipeline",
                 "discontinued": "Discontinued"}
GROUP_LABEL = {"cgm_pump": "Diabetes devices", "pharma": "Pharma (insulin & GLP-1)", "cell_gene": "Cell & gene therapy",
               "immune": "Immunology"}
DEVICE_CATS = [
    {"slug": "cgm", "key": "cgm", "title": "Continuous glucose monitors",
     "lede": "Sensors that read glucose every few minutes. The category a functional cure would shrink least, because cured patients may keep monitoring.",
     "codes": ["QBJ", "SAF", "SBH", "SJD", "MDS", "QHJ", "QCD", "SFI"]},
    {"slug": "pumps", "key": "pump", "title": "Insulin pumps & automated insulin delivery",
     "lede": "Pumps and the algorithms that steer them. Almost entirely a T1D market, so the most exposed to a cure.",
     "codes": ["QFG", "QJI", "OZP"]},
    {"slug": "software", "key": "other", "title": "Dosing software & other",
     "lede": "Insulin-dosing software and other regulated diabetes tools.",
     "codes": ["QRX"]},
]
MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()

NAV = [("", "Overview"), ("model/", "Cure Impact Model"), ("pipeline/", "Cure pipeline"), ("glp1/", "GLP-1s"),
       ("medtech/", "Medtech"), ("companies/", "Companies"), ("catalysts/", "Catalysts"), ("research/", "Research"),
       ("about/", "About")]
# Desktop/tablet masthead: five primary destinations plus a "More" menu (short labels to fit from 720px up).
NAV_PRIMARY = [("model/", "Model"), ("pipeline/", "Pipeline"), ("companies/", "Companies"), ("catalysts/", "Catalysts"),
               ("research/", "Research")]
NAV_MORE = [("glp1/", "GLP-1s in T1D"), ("medtech/", "Medtech"), ("methodology/", "Methodology"), ("about/", "About")]

NOTES = [
    {"slug": "glp1s-and-the-t1d-label", "template": "research/glp1_label.html",
     "title": "Why GLP-1s don't have a type 1 diabetes label yet", "kicker": "GLP-1s",
     "dek": "A decade after liraglutide's T1D program, no GLP-1 label covers type 1. The data explain why, and what tirzepatide's Phase 3 has to show.",
     "published": "2026-10-24"},
    {"slug": "the-cure-race-in-one-chart", "template": "research/cure_race.html",
     "title": "The cure race in one chart", "kicker": "Cure pipeline",
     "dek": "Plotting every tracked program by how far it has advanced against how far its evidence has actually read out.",
     "published": "2026-10-24"},
    {"slug": "what-a-cure-means-for-pump-makers", "template": "research/pump_makers.html",
     "title": "What a functional cure means for pump makers", "kicker": "Model read-across",
     "dek": "Running the Cure Impact Model through the income statements of the companies most exposed to type 1 diabetes.",
     "published": "2026-10-24"},
]


# ------------------------------------------------------------------ formatting helpers
def money(n, dp=1):
    return charts.money(n, dp)


def pct(x, dp=0, signed=False):
    if x is None:
        return "—"
    s = "{:,.{}f}%".format(x * 100, dp)
    if signed:
        if x > 0:
            s = "+" + s
        elif x < 0:
            s = "−" + s.lstrip("-")
    return s


def num(n, dp=0):
    if n is None:
        return "—"
    return "{:,.{}f}".format(n, dp)


def fdate(s, precision=None, short=False):
    """Human date honouring the precision of the source (never adds false precision)."""
    if not s:
        return "Date not disclosed"
    s = str(s)
    p = (precision or "exact").lower()
    try:
        y = int(s[:4])
        m = int(s[5:7]) if len(s) >= 7 else None
        d = int(s[8:10]) if len(s) >= 10 else None
    except ValueError:
        return s
    if p == "year" or m is None:
        return str(y)
    if p == "quarter":
        return "Q{} {}".format((m - 1) // 3 + 1, y)
    if p == "half":
        return "H{} {}".format(1 if m <= 6 else 2, y)
    if p in ("month", "guided") or d is None:
        base = "{} {}".format(MONTHS[m - 1], y)
        return "by " + base if p == "guided" else base
    if short:
        return "{} {}".format(MONTHS[m - 1], d)
    return "{} {}, {}".format(MONTHS[m - 1], d, y)


def precision_note(p):
    p = (p or "").lower()
    return {
        "guided": "company guidance, not a fixed date",
        "quarter": "quarter only", "half": "half-year only", "month": "month only", "year": "year only",
        "registry-estimated": "registry estimate", "registry-anticipated": "registry estimate",
        "registry-actual": "registry actual", "registry": "registry estimate",
    }.get(p, "")


def days_until(s):
    d = parse_date(s)
    return (d - TODAY).days if d else None


def slug_ticker(t):
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def quarter_of(s):
    d = parse_date(s)
    return (d.year, (d.month - 1) // 3 + 1) if d else None


# ------------------------------------------------------------------ data loading
DATA_JSON = SRC / "data"  # overridable with --data-dir (frozen snapshots for regression checks)


def load_json(name, default=None):
    p = DATA_JSON / name
    if not p.exists():
        return default
    return json.loads(p.read_text())


def load_yaml(name):
    with open(DATA / name) as f:
        return yaml.safe_load(f)


TODAY = dt.date.today()


def load_all():
    progs = load_json("programs.json", {"programs": [], "papers": {}, "news": {}})
    comps = load_json("companies.json", {"companies": []})["companies"]
    curated_c = {c["ticker"]: c for c in load_yaml("companies.yaml")["companies"]}
    # Curated fields always win (the JSON may predate a YAML edit).
    merged = []
    for c in comps:
        cc = dict(c)
        cc.update(curated_c.get(c["ticker"], {}))
        merged.append(cc)
    for t, c in curated_c.items():
        if t not in {x["ticker"] for x in comps}:
            merged.append(dict(c, quote=None, filings=[]))
    return {
        "programs": progs["programs"], "papers": progs.get("papers") or {},
        "trials": load_json("trials.json", {"trials": {}})["trials"],
        "devices": load_json("devices.json", {"devices": [], "fda_feed": [], "code_labels": {}}),
        "companies": merged,
        "catalysts": load_json("catalysts.json", {"catalysts": []})["catalysts"],
        "changes": load_json("changes.json", {"changes": []})["changes"],
        "glp1": load_json("glp1.json", {"registry_scan": [], "papers": {}, "labels": [], "any_t1d_label": False}),
        "meta": load_json("meta.json", {}),
        "market": load_yaml("market.yaml"),
        "notes": load_yaml("my_notes.yaml") or {},
    }


# ------------------------------------------------------------------ enrichment
def enrich_programs(D):
    for p in D["programs"]:
        p["stage_i"] = GRADES.index(p["stage"])
        p["evidence_i"] = GRADES.index(p["evidence"])
        p["gap"] = p["stage_i"] - p["evidence_i"]
        p["url"] = "programs/{}/".format(p["id"])
        p["short"] = re.split(r"\s[(—]", p["name"])[0].strip()
        p["approach_label"] = APPROACH.get(p.get("approach"), (GLP_TOPIC.get(p.get("glp1_topic"), "GLP-1"), ""))[0]
        p["company_slug"] = slug_ticker(p["ticker"]) if p.get("ticker") else None
        p["timeline"] = program_timeline(p, D["changes"])
        nc = p.get("next_catalyst")
        p["next_label"] = None
        if nc:
            p["next_label"] = fdate(nc.get("date"), "registry" if nc.get("date_precision") == "registry" else nc.get("date_precision"))
    tracked = {c["ticker"] for c in D["companies"]}
    for p in D["programs"]:
        if p.get("ticker") not in tracked:
            p["company_slug"] = None


def program_timeline(p, changes):
    ev = []
    for t in p.get("trials") or []:
        tag = t.get("acronym") or t["nct_id"]
        if t.get("start_date"):
            ev.append({"date": t["start_date"], "label": "{} started".format(tag), "sub": t["nct_id"] + " · " + ", ".join(t.get("phases") or []),
                       "url": t["url"], "kind": "past" if parse_date(t["start_date"]) and parse_date(t["start_date"]) <= TODAY else "future"})
        pc = t.get("primary_completion")
        if pc:
            actual = (t.get("primary_completion_type") or "").upper() == "ACTUAL"
            ev.append({"date": pc, "label": "{} primary completion".format(tag),
                       "sub": t["nct_id"] + (" · actual" if actual else " · registry estimate, not a results date"),
                       "url": t["url"], "kind": "past" if actual else "future", "estimate": not actual})
        if t.get("status") in ("TERMINATED", "WITHDRAWN", "SUSPENDED"):
            ev.append({"date": t.get("last_update"), "label": "{} {} (registry)".format(tag, STATUS_LABEL.get(t["status"], t["status"]).lower()),
                       "sub": (t.get("why_stopped") or "Reason not given in registry")[:160], "url": t["url"], "kind": "past"})
    ncts = set(p.get("nct_ids") or [])
    for c in changes:
        if c.get("nct_id") in ncts:
            lab = "Registry status changed: {} → {}".format(c.get("from"), c.get("to")) if c["kind"] == "status" else \
                "Registry primary completion moved {} → {}".format(c.get("from"), c.get("to"))
            ev.append({"date": c["date"], "label": lab, "sub": c["nct_id"], "url": "https://clinicaltrials.gov/study/" + c["nct_id"], "kind": "past"})
    nc = p.get("next_catalyst")
    if nc and nc.get("date"):
        prec = "registry" if nc.get("date_precision") == "registry" else nc.get("date_precision")
        ev.append({"date": nc["date"], "label": "Next catalyst: " + nc["label"], "sub": precision_note(prec) or None,
                   "kind": "future", "precision": prec})
    ev = [e for e in ev if e.get("date")]
    seen, out = set(), []
    for e in sorted(ev, key=lambda e: (str(e["date"]), e["label"])):
        k = (str(e["date"]), e["label"])
        if k not in seen:
            seen.add(k)
            out.append(e)
    return out


def enrich_companies(D, market):
    base_ra = {r["ticker"]: r for r in model.read_across(D["companies"], market, model.default_inputs(market, "base"))}
    for c in D["companies"]:
        c["slug"] = slug_ticker(c["ticker"])
        c["url"] = "companies/{}/".format(c["slug"])
        q = c.get("quote") or {}
        c["q"] = q
        c["programs"] = [p for p in D["programs"] if p.get("ticker") == c["ticker"]]
        c["devices"] = [d for d in D["devices"]["devices"] if d.get("ticker") == c["ticker"]]
        c["ra"] = base_ra.get(c["ticker"])
        c["group_label"] = GROUP_LABEL.get(c.get("group"), c.get("group"))


def catalyst_rows(D):
    progs = {p["id"]: p for p in D["programs"]}
    devs = {d["id"]: d for d in D["devices"]["devices"]}
    rows = []
    for c in D["catalysts"]:
        r = dict(c)
        # Stable across runs (no list position), so calendar apps update events instead of duplicating them.
        key = "{}|{}|{}".format(c["type"], c["title"], c.get("related") or c.get("source") or "")
        r["uid"] = "ttc-" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
        r["days"] = days_until(c["date"])
        prec = c.get("precision") or "exact"
        r["when"] = fdate(c["date"], "exact" if prec.startswith("registry") else prec)
        if prec == "exact" or prec.startswith("registry"):
            r["short"] = "{} ’{}".format(fdate(c["date"], "exact", short=True), c["date"][2:4])
        else:
            r["short"] = r["when"]
        r["prec_note"] = precision_note(prec)
        r["type_label"] = CAT_TYPE.get(c["type"], c["type"].title())
        rel = c.get("related")
        r["related_url"] = progs[rel]["url"] if rel in progs else None
        if rel in devs:
            cat = next((x for x in DEVICE_CATS if x["key"] == devs[rel]["category"]), None)
            r["related_url"] = "medtech/{}/".format(cat["slug"]) if cat else None
        rows.append(r)
    return rows


# ------------------------------------------------------------------ model page data
def model_page_data(D, market):
    mj, results = model.to_json(market, D["companies"])
    base = results["base"]
    x = [r["year"] for r in base["rows"]]

    def series(res):
        return [
            {"name": "Insulin", "key": "insulin", "cls": "s1", "values": [r["displaced"]["insulin"] for r in res["rows"]]},
            {"name": "CGM", "key": "cgm", "cls": "s2", "values": [r["displaced"]["cgm"] for r in res["rows"]]},
            {"name": "Pumps / AID", "key": "pump", "cls": "s3", "values": [r["displaced"]["pump"] for r in res["rows"]]},
        ]
    chart = Markup(charts.stacked_area(x, series(base), "Projected T1D-attributable revenue displaced by a functional cure, base case, 2025 to 2040",
                                       marks=(2035, 2040), chart_id="model-chart"))
    # Homepage hero: displaced revenue inside the T1D-attributable baseline it is a share of. Both series are existing
    # model.run() outputs (t1d_baseline_total, displaced_total) for the base case; nothing is recalculated here.
    rows = base["rows"]
    hero_args = ([r["year"] for r in rows], [r["t1d_baseline_total"] for r in rows], [r["displaced_total"] for r in rows],
                 "T1D-attributable revenue in the no-cure baseline and the part a cure displaces, base case, 2025 to 2040")
    approval = base["inputs"]["approval"]
    hero = {"wide": Markup(charts.context_area(*hero_args, marker=(approval, "Approval {} · assumption".format(approval)))),
            "narrow": Markup(charts.context_area(*hero_args, marker=(approval, "Approval {} · assumption".format(approval)),
                                                 w=360, h=300, compact=True)),
            "baseline_2025": rows[0]["t1d_baseline_total"], "baseline_2040": rows[-1]["t1d_baseline_total"]}
    exposures = model.company_exposure(D["companies"])
    js = {
        "market": {"base_year": market["base_year"], "markets": market["markets"], "population": market["population"]},
        "scenarios": {k: dict(market["scenarios"][k]) for k in model.SCENARIO_ORDER},
        "defaults": {k: model.default_inputs(market, k) for k in model.SCENARIO_ORDER},
        "sens": {"approval": model.SENS_APPROVAL, "peak": model.SENS_PEAK, "price": model.SENS_PRICE, "cap": model.SENS_CAP},
        "companies": [{"ticker": c["ticker"], "name": c["name"], "slug": slug_ticker(c["ticker"]),
                       "revenue": exposures[c["ticker"]]["revenue"], "exposure": exposures[c["ticker"]]["exposure"],
                       "basis": exposures[c["ticker"]]["basis"]}
                      for c in D["companies"] if c["ticker"] in exposures],
        "check": {k: {"d2035": v["summary"]["2035"]["displaced_total"], "d2040": v["summary"]["2040"]["displaced_total"],
                      "cum": v["summary"]["cum_cure_sales"]} for k, v in results.items()},
    }
    ra_rows = sorted(mj["read_across"]["base"], key=lambda r: -((r["years"]["2040"] or {}).get("pct_current_rev") or -1))
    for r in ra_rows:
        r["kind"] = model.classify(r)
        r["slug"] = slug_ticker(r["ticker"])
    # Read-across chart categories. Pure-plays whose modelled revenue mix is identical get identical results by
    # construction, so they are drawn once with their names listed (not as several identical bars).
    PURE = {"pump": "Pump pure-plays", "cgm": "CGM pure-plays", "insulin": "Insulin-delivery pure-plays"}
    cats, groups = [], {}
    for r in ra_rows:
        if not r["exposure"] or not (r["years"].get("2040") or {}):
            continue
        key = tuple(sorted(r["exposure"].items()))
        if len(key) == 1 and key[0][1] >= 0.95:
            groups.setdefault(key, []).append(r)
        else:
            cats.append({"label": r["name"], "members": None, "tickers": [r["ticker"]],
                         "value": r["years"]["2040"]["pct_current_rev"]})
    for key, members in groups.items():
        vals = {round(m["years"]["2040"]["pct_current_rev"], 12) for m in members}
        assert len(vals) == 1, "pure-play group with differing results: " + str([m["ticker"] for m in members])
        label = PURE[key[0][0]] if len(members) > 1 else members[0]["name"]
        cats.append({"label": label, "members": ", ".join(m["name"] for m in members) if len(members) > 1 else None,
                     "tickers": [m["ticker"] for m in members], "value": members[0]["years"]["2040"]["pct_current_rev"]})
    cats.sort(key=lambda c: -c["value"])
    js["categories"] = [{k: c[k] for k in ("label", "members", "tickers")} for c in cats]
    not_modelled = [r["name"] for r in ra_rows if not r["exposure"] or not r["years"].get("2040")]
    sens = mj["sensitivity"]
    for g in sens.values():
        g["bins"] = heat_bins(g["values"])
    return {"json": mj, "results": results, "chart": chart, "hero": hero, "js": js, "ra_cats": cats, "ra_not_modelled": not_modelled, "ra": ra_rows, "series": series, "sens": sens,
            "csv": model.to_csv(market, results)}


def heat_bins(grid):
    """Rank-based 6-step bins for the sensitivity heatmaps (same rule as app.js heatBins)."""
    flat = sorted(v for row in grid for v in row)
    n = len(flat)
    return [[min(5, int(6 * flat.index(v) / n)) for v in row] for row in grid]


def implications(md, market):
    """Three research-note style takeaways, every number pulled from model output."""
    b = md["results"]["base"]["summary"]
    v = md["results"]["base"]["inputs"]
    ra = {r["ticker"]: r for r in md["ra"]}

    def p40(t):
        r = ra.get(t)
        y = r and r["years"].get("2040")
        return y["pct_current_rev"] if y else None
    pump_t = [t for t in ("PODD", "TNDM", "BBNX", "MMED") if p40(t) is not None]
    pump_pct = p40(pump_t[0]) if pump_t else None
    dx = p40("DXCM")
    nvo = p40("NVO")
    d40 = b["2040"]["displaced"]
    out = []
    if pump_pct is not None and dx is not None:
        rel = "more than" if pump_pct > dx else "less than"
        out.append({
            "title": "Pump pure-plays carry the most concentrated risk.",
            "body": "In the base case, displaced pump revenue reaches {} a year by 2040. Held at today's market shares, that equals "
                    "{} of current revenue at each pump pure-play (Insulet, Tandem, Beta Bionics, MiniMed), {} the {} at Dexcom. "
                    "The gap comes from exposure: pumps are assumed {} T1D-driven and are fully displaced, while CGM is {} T1D and "
                    "{} of cured patients are assumed to keep a sensor.".format(
                        money(d40["pump"]), pct(pump_pct, 1), rel, pct(dx, 1), pct(v["sh_pump"]), pct(v["sh_cgm"]), pct(v["residual"]))})
    rank = sorted(d40, key=d40.get, reverse=True).index("insulin")
    diluted = nvo is not None and pump_pct is not None and nvo < pump_pct
    out.append({
        "title": "Insulin is the {} market today{}.".format(
            "largest" if max(market["markets"], key=lambda k: market["markets"][k]["value"]) == "insulin" else "a large",
            ", but the {} displaced pool{}".format(["largest", "second-largest", "smallest"][rank], " and the most diluted" if diluted else "")
            if rank > 0 else (", and the most diluted" if diluted else "")),
        "body": "Displaced insulin revenue is {} in 2040, versus {} for CGM and {} for pumps. Spread across diversified "
                "pharma, it is a rounding error: for Novo Nordisk, where insulin is {} of sales, the base case implies {} of current revenue."
                .format(money(d40["insulin"]), money(d40["cgm"]), money(d40["pump"]),
                        pct(ra["NVO"]["exposure"].get("insulin"), 1) if "NVO" in ra else "—", pct(nvo, 1))})
    out.append({
        "title": "It is a terminal-value story before it is a revenue story.",
        "body": "Displacement does not start until {} and is only {} of T1D-attributable revenue by 2035, rising to {} by 2040. "
                "Peak cure sales of {} arrive in {}. For long-duration device equities, the risk should surface in multiples "
                "well before it shows up in reported revenue.".format(
                    b["first_displacement_year"] or "after 2040", pct(b["2035"]["share_of_t1d"], 1), pct(b["2040"]["share_of_t1d"], 1),
                    money(b["peak_cure_sales"]), b["peak_cure_year"] or "—")})
    return out


# ------------------------------------------------------------------ ICS
def ics(rows):
    def esc_ics(s):
        return str(s).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    def fold(line):
        out, b = [], line.encode("utf-8")
        while len(b) > 74:
            cut = 74
            while (b[cut] & 0xC0) == 0x80:
                cut -= 1
            out.append(b[:cut].decode("utf-8"))
            b = b" " + b[cut:]
        out.append(b.decode("utf-8"))
        return "\r\n".join(out)
    stamp = dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Tracking the Cure//Catalyst calendar//EN", "CALSCALE:GREGORIAN",
             "METHOD:PUBLISH", "X-WR-CALNAME:Tracking the Cure — T1D catalysts",
             "X-WR-CALDESC:Readouts\\, launches\\, conferences and earnings tracked by Tracking the Cure. Not investment advice.",
             "REFRESH-INTERVAL;VALUE=DURATION:P1D", "X-PUBLISHED-TTL:P1D"]
    for r in rows:
        d = parse_date(r["date"])
        if not d or d < TODAY - dt.timedelta(days=90):
            continue
        end = parse_date(r.get("end")) or d
        desc = "Date precision: {}. ".format(r["prec_note"] or "exact") if r.get("prec_note") else ""
        desc += (r.get("note") or "") + (" Source: " + r["source"] if r.get("source") else "")
        lines += ["BEGIN:VEVENT", "UID:{}@tracking-the-cure".format(r["uid"]), "DTSTAMP:" + stamp,
                  "DTSTART;VALUE=DATE:" + d.strftime("%Y%m%d"),
                  "DTEND;VALUE=DATE:" + (end + dt.timedelta(days=1)).strftime("%Y%m%d"),
                  "SUMMARY:" + esc_ics("[{}] {}".format(r["type_label"], r["title"]) + (" (≈)" if r.get("prec_note") else "")),
                  "DESCRIPTION:" + esc_ics(desc.strip())]
        if r.get("source"):
            lines.append("URL:" + r["source"])
        lines.append("TRANSP:TRANSPARENT")
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(fold(l) for l in lines) + "\r\n"


# ------------------------------------------------------------------ render
class Site:
    def __init__(self, out):
        self.out = out
        self.pages = []
        self.env = Environment(loader=FileSystemLoader(str(TPL)), autoescape=True,
                               trim_blocks=True, lstrip_blocks=True)
        f = self.env.filters
        f["money"] = money
        f["pct"] = pct
        f["num"] = num
        f["fdate"] = fdate
        f["grade"] = lambda g: GRADE_LABEL.get(g, g or "—")
        f["status"] = lambda s: STATUS_LABEL.get(s, (s or "Unknown").replace("_", " ").title())
        f["prec_note"] = precision_note
        f["spark"] = lambda v: Markup(charts.spark(v))
        f["slug"] = slug_ticker
        f["json"] = lambda o: Markup(json.dumps(o, separators=(",", ":"), default=str).replace("</", "<\\/"))
        f["regex_ticker"] = lambda t: (re.search(r"\(([^)]+)\)\s*$", t) or [None, t])[1]
        self.env.tests["startingwith"] = lambda v, prefix: str(v).startswith(prefix)
        self.env.globals.update(GRADES=GRADES, GRADE_LABEL=GRADE_LABEL, GRADE_SHORT=GRADE_SHORT, APPROACH=APPROACH,
                                CAT_TYPE=CAT_TYPE, SITE_NAME=SITE_NAME, SITE_URL=SITE_URL,
                                NAV=NAV, NAV_PRIMARY=NAV_PRIMARY, NAV_MORE=NAV_MORE, today=TODAY, days_until=days_until, DEVICE_STATUS=DEVICE_STATUS)

    def page(self, path, template, title, description, og_key=None, og_kicker="", og_track=None, **ctx):
        """path is the directory URL relative to the site root ('' for home, 'model/' ...)."""
        depth = path.count("/") if path and not path.endswith(".html") else 0
        root = "../" * depth
        if path == "404.html":  # served for any missing URL, at any depth: use the absolute site path
            from urllib.parse import urlparse
            root = urlparse(SITE_URL).path
        og_name = (og_key or (path.strip("/").replace("/", "-") or "home")) + ".png"
        og.ensure(og_name, title if path else SITE_NAME, og_kicker or "Independent research · Type 1 diabetes", og_track)
        full_title = title if not path else "{} · {}".format(title, SITE_NAME)
        html = self.env.get_template(template).render(
            root=root, path=path, title=title, full_title=full_title, description=description,
            canonical=SITE_URL + path, og_image=SITE_URL + "og/" + og_name, **ctx)
        target = self.out / (path if path.endswith(".html") else path + "index.html")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html)
        if not path.endswith("404.html"):
            self.pages.append(path)


def render(out=OUT, styleguide=False):
    D = load_all()
    market = D["market"]
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(SRC / "assets", out / "assets", ignore=shutil.ignore_patterns("og"))
    shutil.copytree(DATA_JSON, out / "data")
    enrich_programs(D)
    enrich_companies(D, market)
    md = model_page_data(D, market)
    cats = catalyst_rows(D)
    meta = D["meta"]
    built = meta.get("built_at", "")
    built_date = built[:10] if built else TODAY.isoformat()

    S = Site(out)
    # Content hashes as ?v= cache-busters, so a deploy never serves a stale stylesheet or script.
    S.env.globals["v"] = {n: hashlib.sha1((SRC / "assets" / n).read_bytes()).hexdigest()[:10]
                          for n in ("style.css", "app.js", "model.js", "model-view.js")}
    S.env.globals.update(built_at=built, built_date=built_date, built_human=fdate(built_date), meta=meta)
    cure = [p for p in D["programs"] if p["section"] == "cure"]
    glp = [p for p in D["programs"] if p["section"] == "glp1"]
    active_cure = [p for p in cure if p["status"] == "active"]
    upcoming = [c for c in cats if c["days"] is not None and c["days"] >= 0]
    sizes = market["markets"]
    tam = sum(sizes[k]["value"] for k in ("cgm", "pump", "insulin")) * 1e9
    headline = {
        "active": len(active_cure),
        "late": len([p for p in active_cure if p["stage_i"] >= GRADES.index("phase3")]),
        "late_ev": len([p for p in active_cure if p["evidence_i"] >= GRADES.index("phase3")]),
        "approved": [p for p in active_cure if p["stage"] == "approved"],
        "glp_label": D["glp1"].get("any_t1d_label"),
        "tam": tam, "flags": sum(1 for p in D["programs"] for f in p["flags"] if f["level"] != "info"),
        "trials": len(D["trials"]),
    }
    hype_order = sorted(cure, key=lambda p: (p["status"] == "discontinued", -p["stage_i"], -p["evidence_i"], p["name"]))
    common = dict(D=D, md=md, market=market, headline=headline, cats=cats, upcoming=upcoming, cure=cure, glp=glp,
                  hype_order=hype_order, notes_meta=NOTES, DEVICE_CATS=DEVICE_CATS, GLP_TOPIC=GLP_TOPIC,
                  GROUP_LABEL=GROUP_LABEL, implications=implications(md, market))

    # Home
    S.page("", "index.html", SITE_NAME,
           "Independent, source-cited investment research on the race to cure type 1 diabetes: a live pipeline tracker, "
           "a Cure Impact Model for CGM, pump and insulin makers, and a catalyst calendar.", og_key="home", **common)
    # Model
    (out / "model").mkdir(exist_ok=True)
    (out / "model" / "cure-impact-model.csv").write_text(md["csv"])
    (out / "data" / "model.json").write_text(json.dumps(md["json"], default=str))
    S.page("model/", "model.html", "Cure Impact Model",
           "How much CGM, insulin-pump and insulin revenue would a functional cure for type 1 diabetes displace? Scenarios, "
           "sensitivities and company read-across, with every assumption labelled.", og_kicker="Flagship model", **common)
    # Pipeline + programs
    S.page("pipeline/", "pipeline.html", "Cure pipeline",
           "Every tracked type 1 diabetes cure program, graded on stage reached and evidence read out, with live registry data.",
           og_kicker="Cure pipeline", **common)
    for p in D["programs"]:
        related = [q for q in D["programs"] if q is not p and q.get("ticker") and q.get("ticker") == p.get("ticker")]
        S.page(p["url"], "program.html", p["name"],
               "{} ({}): stage {}, evidence {}. {}".format(p["name"], p["company"], GRADE_LABEL[p["stage"]], GRADE_LABEL[p["evidence"]],
                                                          re.sub(r"\s+", " ", p["reality_check"])[:140]),
               og_key="program-" + p["id"], og_kicker=p["company"], og_track=(p["evidence_i"], p["stage_i"]), p=p, related=related,
               papers=(D["papers"] or {}).get(p.get("approach")) or (D["glp1"]["papers"] or {}).get(p.get("glp1_topic")) or [],
               **common)
    # GLP-1
    S.page("glp1/", "glp1.html", "GLP-1s in type 1 diabetes",
           "GLP-1 and GIP/GLP-1 drugs in type 1 diabetes: label status checked against FDA labels daily, every registered trial, and the evidence so far.",
           og_kicker="GLP-1s in T1D", **common)
    # Medtech
    S.page("medtech/", "medtech.html", "T1D medtech",
           "CGMs, insulin pumps and automated insulin delivery: what is marketed, cleared and in the pipeline, plus every new FDA decision.",
           og_kicker="Medtech", **common)
    for cat in DEVICE_CATS:
        devs = [d for d in D["devices"]["devices"] if d["category"] == cat["key"]]
        feed = [f for f in D["devices"]["fda_feed"] if f.get("product_code") in cat["codes"]]
        S.page("medtech/{}/".format(cat["slug"]), "device_category.html", cat["title"],
               cat["lede"] + " Live FDA decision feed from openFDA.", og_key="medtech-" + cat["slug"], og_kicker="Medtech",
               cat=cat, devs=devs, feed=feed, **common)
    # Companies
    S.page("companies/", "companies.html", "Companies",
           "Public companies exposed to type 1 diabetes: live prices, returns, revenue, diabetes share of revenue, and cure-scenario exposure.",
           og_kicker="Companies", **common)
    for c in D["companies"]:
        q = c["q"]
        S.page(c["url"], "company.html", "{} ({})".format(c["name"], c["ticker"]),
               "{} ({}): price, key metrics, type 1 diabetes exposure, linked programs and devices, and recent SEC filings."
               .format(c["name"], c["ticker"]), og_key="company-" + c["slug"], og_kicker=c["ticker"],
               c=c, price_chart=Markup(price_chart(c)) if q.get("spark") or q.get("history") else None, **common)
    # Catalysts
    (out / "catalysts.ics").write_text(ics(cats))
    S.page("catalysts/", "catalysts.html", "Catalyst calendar",
           "Upcoming type 1 diabetes catalysts by quarter: trial readouts, launches, FDA decisions, conferences and earnings. Subscribe via .ics.",
           og_kicker="Catalysts", quarters=quarters(upcoming), **common)
    # Research
    S.page("research/", "research.html", "Research notes",
           "Short, sourced analytical notes on type 1 diabetes cures, GLP-1s and medtech, built from the tracked data. Analysis, not advice.",
           og_kicker="Research", **common)
    for n in NOTES:
        S.page("research/{}/".format(n["slug"]), n["template"], n["title"], n["dek"], og_key="note-" + n["slug"],
               og_kicker="Research note", note=n, **common)
    # Methodology, About, 404
    S.page("methodology/", "methodology.html", "Methodology",
           "How programs are graded, how flags are raised, where the data comes from, and how fresh each source is.",
           og_kicker="Methodology", **common)
    S.page("about/", "about.html", "About",
           "Who built Tracking the Cure and why: an independent research project by someone living with type 1 diabetes.",
           og_kicker="About", **common)
    S.page("404.html", "404.html", "Page not found", "This page does not exist.", og_key="home", **common)
    if styleguide:  # development reference page: noindex, not linked, not in the sitemap, never built by the Action
        S.page("styleguide/", "styleguide.html", "Design system reference", "Development-only component reference.",
               og_key="home", **common)
        S.pages.remove("styleguide/")

    # og images, sitemap, robots
    shutil.copytree(SRC / "assets" / "og", out / "og")
    urls = "".join("<url><loc>{}{}</loc><lastmod>{}</lastmod></url>".format(SITE_URL, p, built_date) for p in S.pages)
    (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + urls + "</urlset>\n")
    (out / "robots.txt").write_text("User-agent: *\nAllow: /\nSitemap: {}sitemap.xml\n".format(SITE_URL))
    (out / ".nojekyll").write_text("")
    og.favicon(out / "favicon.ico")
    print("Rendered {} pages into {}".format(len(S.pages) + 1, os.path.relpath(out, ROOT)))
    return S.pages


def price_chart(c):
    q = c["q"]
    hist = q.get("history")
    if hist:
        x = [h[0] for h in hist]
        vals = [h[1] for h in hist]
        sub = "weekly closes"
    else:
        vals = q["spark"]
        end = parse_date(q.get("as_of")) or TODAY
        x = [(end - dt.timedelta(days=7 * (len(vals) - 1 - i))).isoformat() for i in range(len(vals))]
        sub = "approx. weekly closes"
    return charts.line(x, [{"name": "{} ({})".format(c["ticker"], q.get("currency") or ""), "cls": "s1", "values": vals}],
                       "{} share price, {}".format(c["name"], sub), area=True, chart_id="price-chart")


def quarters(upcoming, n=3):
    if not upcoming:
        return []
    start = (TODAY.year, (TODAY.month - 1) // 3 + 1)
    qs = []
    y, q = start
    for _ in range(n):
        qs.append({"y": y, "q": q, "label": "Q{} {}".format(q, y), "items": []})
        q += 1
        if q == 5:
            y, q = y + 1, 1
    idx = {(x["y"], x["q"]): x for x in qs}
    later = {"label": "Later", "items": []}
    for c in upcoming:
        k = quarter_of(c["date"])
        if k in idx:
            idx[k]["items"].append(c)
        elif k and k > (qs[-1]["y"], qs[-1]["q"]):
            later["items"].append(c)
    return qs + ([later] if later["items"] else [])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    # Development-only switches for reproducible renders (numerical regression checks). Defaults leave the
    # production build untouched: live site/data and today's date.
    ap.add_argument("--data-dir", default=None, help="read JSON from this folder instead of site/data")
    ap.add_argument("--today", default=None, help="render as if today were YYYY-MM-DD")
    ap.add_argument("--styleguide", action="store_true", help="also render the development-only /styleguide/ page")
    a = ap.parse_args()
    if a.data_dir:
        DATA_JSON = pathlib.Path(a.data_dir).resolve()
    if a.today:
        TODAY = dt.date.fromisoformat(a.today)
    try:
        render(pathlib.Path(a.out), styleguide=a.styleguide)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
