"""Daily build: curated YAML + live primary-source data -> site/data/*.json.

Run:  python -m pipeline.build            (full refresh)
      python -m pipeline.build --offline  (re-render from curated data + last fetched JSON)
      python -m pipeline.build --skip news,links

Every live source is fetched independently. If one fails, the previous day's data for
that source is kept and marked stale in meta.json, so the site never goes blank.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import traceback

import yaml

from . import ctgov, markets, news, openfda, pubmed, sec
from .http import session

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "site" / "data"

GRADES = ["preclinical", "phase1", "phase2", "phase3", "filed", "approved"]
APPROACHES = {"cell_replacement", "gene_edited", "encapsulation", "immune"}
STOPPED = {"TERMINATED", "WITHDRAWN", "SUSPENDED"}
ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION"}
CURATION_STALE_DAYS = 120
TODAY = dt.date.today()

health = {}  # source -> {"ok": bool, "detail": str, "at": iso}


# ------------------------------------------------------------------ helpers
def load_yaml(name):
    with open(DATA / name) as f:
        return yaml.safe_load(f)


def load_prev(name):
    p = OUT / name
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:
            return None
    return None


def write(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=1, default=str, ensure_ascii=False))


def run_source(name, fn, fallback=None):
    """Run one live source; on failure, log it and return the fallback (previous data)."""
    try:
        val = fn()
        health[name] = {"ok": True, "detail": "refreshed", "at": dt.datetime.utcnow().isoformat() + "Z"}
        return val
    except Exception as e:  # noqa: BLE001 - every source must fail soft
        traceback.print_exc()
        health[name] = {"ok": False, "detail": "{}: {}".format(type(e).__name__, str(e)[:200]),
                        "at": dt.datetime.utcnow().isoformat() + "Z"}
        return fallback


def parse_date(s):
    """Registry dates come as YYYY, YYYY-MM or YYYY-MM-DD. Month-only → end of month."""
    if not s:
        return None
    if isinstance(s, dt.date):
        return s
    s = str(s)
    try:
        if len(s) == 7:
            y, m = map(int, s.split("-"))
            nxt = dt.date(y + (m == 12), m % 12 + 1, 1)
            return nxt - dt.timedelta(days=1)
        if len(s) == 4:
            return dt.date(int(s), 12, 31)
        return dt.date.fromisoformat(s[:10])
    except ValueError:
        return None


# ------------------------------------------------------------------ validation
def validate(programs, devices, notes):
    errs = []
    ids = set()
    for p in programs:
        pid = p.get("id", "?")
        if pid in ids:
            errs.append("duplicate id " + pid)
        ids.add(pid)
        for k in ("name", "company", "stage", "evidence", "status", "summary", "reality_check", "sources", "verified_on"):
            if not p.get(k):
                errs.append("{}: missing '{}'".format(pid, k))
        for k in ("stage", "evidence"):
            if p.get(k) and p[k] not in GRADES:
                errs.append("{}: {} '{}' not in {}".format(pid, k, p[k], GRADES))
        if p.get("section") == "cure" and p.get("approach") not in APPROACHES:
            errs.append("{}: approach must be one of {}".format(pid, sorted(APPROACHES)))
        if p.get("stage") in GRADES and p.get("evidence") in GRADES and \
                GRADES.index(p["evidence"]) > GRADES.index(p["stage"]):
            errs.append("{}: evidence cannot be ahead of stage".format(pid))
        for n in p.get("nct_ids") or []:
            if not re.fullmatch(r"NCT\d{8}", n):
                errs.append("{}: bad NCT id {}".format(pid, n))
    dev_ids = {d["id"] for d in devices}
    for k in (notes.get("devices") or {}):
        if k not in dev_ids:
            errs.append("my_notes.yaml: device '{}' not found in devices.yaml".format(k))
    for k in (notes.get("programs") or {}):
        if k not in ids:
            errs.append("my_notes.yaml: program '{}' not found in programs.yaml".format(k))
    return errs


# ------------------------------------------------------------------ link check
def check_links(urls, prev):
    prev = prev or {}
    out = {}
    s = session()
    for u in sorted(urls):
        try:
            r = s.head(u, allow_redirects=True, timeout=15)
            if r.status_code in (403, 405, 400) or r.status_code >= 500:
                r = s.get(u, allow_redirects=True, timeout=20, stream=True)
                r.close()
            code = r.status_code
        except Exception:
            code = None
        if code in (404, 410):
            state = "broken"
        elif code and code < 400:
            state = "ok"
        else:
            state = "unreachable"  # bot-blocked or timeout: not proof the link is wrong
        out[u] = {"state": state, "code": code, "checked": TODAY.isoformat()}
    for u, v in prev.items():
        out.setdefault(u, v)
    return out


# ------------------------------------------------------------------ main build
def build(skip, offline):
    progs_y, devs_y = load_yaml("programs.yaml"), load_yaml("devices.yaml")
    comps_y, cats_y = load_yaml("companies.yaml"), load_yaml("catalysts.yaml")
    market_y, notes = load_yaml("market.yaml"), load_yaml("my_notes.yaml") or {}
    programs, devices = progs_y["programs"], devs_y["devices"]

    errs = validate(programs, devices, notes)
    if errs:
        print("Curated data has errors:\n  " + "\n  ".join(errs), file=sys.stderr)
        sys.exit(1)

    prev_trials = (load_prev("trials.json") or {}).get("trials", {})
    prev_glp = load_prev("glp1.json") or {}
    prev_comp = {c["ticker"]: c for c in (load_prev("companies.json") or {}).get("companies", [])}
    prev_meta = load_prev("meta.json") or {}
    prev_cure = load_prev("programs.json") or {}
    live = not offline

    # ---- ClinicalTrials.gov: every tracked trial
    nct_ids = sorted({n for p in programs for n in (p.get("nct_ids") or [])})
    trials = dict(prev_trials)
    if live and "ctgov" not in skip:
        def fetch_all():
            got, failed = {}, []
            for n in nct_ids:
                try:
                    got[n] = ctgov.fetch_study(n)
                except Exception:
                    failed.append(n)
            if failed and not got:
                raise RuntimeError("all registry fetches failed")
            if failed:
                print("registry fetch failed for", failed, file=sys.stderr)
            return got
        trials.update(run_source("ClinicalTrials.gov", fetch_all, {}) or {})
        write("trials.json", {"trials": trials})

    # ---- change log: registry status / date moves since last run
    changes = (load_prev("changes.json") or {}).get("changes", [])
    for n, t in trials.items():
        old = prev_trials.get(n)
        if not old or t is old:
            continue
        if old.get("status") != t.get("status"):
            changes.insert(0, {"date": TODAY.isoformat(), "nct_id": n, "kind": "status",
                               "from": old.get("status"), "to": t.get("status"), "title": t.get("title")})
        if old.get("primary_completion") != t.get("primary_completion"):
            o, nw = parse_date(old.get("primary_completion")), parse_date(t.get("primary_completion"))
            slip = (nw - o).days if o and nw else None
            changes.insert(0, {"date": TODAY.isoformat(), "nct_id": n, "kind": "date",
                               "from": old.get("primary_completion"), "to": t.get("primary_completion"),
                               "slip_days": slip, "title": t.get("title")})
    changes = changes[:300]

    # ---- link check (weekly is plenty; daily run re-checks only new URLs)
    all_urls = {s["url"] for p in programs for s in p.get("sources", [])}
    all_urls |= {s["url"] for d in devices for s in d.get("sources", [])}
    all_urls |= {c["source"] for c in cats_y["catalysts"] if c.get("source")}
    prev_links = prev_meta.get("links", {})
    links = prev_links
    if live and "links" not in skip:
        weekly = TODAY.weekday() == 0
        todo = all_urls if weekly or not prev_links else all_urls - set(prev_links)
        links = run_source("Source link check", lambda: check_links(todo, prev_links), prev_links)
        write("meta.json", {**prev_meta, "links": links})

    # ---- programs: merge registry data + compute verification flags
    out_programs = []
    for p in programs:
        rec = dict(p)
        rec["trials"] = [trials[n] for n in p.get("nct_ids") or [] if n in trials]
        flags = []
        missing = [n for n in p.get("nct_ids") or [] if n not in trials]
        if missing:
            flags.append({"level": "warn", "text": "Registry data not retrieved for " + ", ".join(missing)})
        has_live = any(t["status"] in ACTIVE for t in rec["trials"])
        for t in rec["trials"]:
            if t["status"] in STOPPED and p["status"] == "active":
                if has_live:
                    flags.append({"level": "info", "text": "{} is {} on ClinicalTrials.gov; the program continues in other registered trials."
                                  .format(t["nct_id"], t["status"].lower())})
                else:
                    flags.append({"level": "alert", "text": "{} is {} on ClinicalTrials.gov but the program is marked active — review."
                                  .format(t["nct_id"], t["status"].lower())})
            pcd = parse_date(t.get("primary_completion"))
            if t["status"] in ("RECRUITING", "NOT_YET_RECRUITING") and pcd and pcd < TODAY:
                flags.append({"level": "warn", "text": "{}: registry primary completion ({}) has passed but status is still {} — registry likely out of date."
                              .format(t["nct_id"], t["primary_completion"], t["status"].lower().replace("_", " "))})
            lu = parse_date(t.get("last_update"))
            if t["status"] in ACTIVE and lu and (TODAY - lu).days > 540:
                flags.append({"level": "info", "text": "{}: registry record not updated since {}.".format(t["nct_id"], t["last_update"])})
        active_grades = [t["phase_grade"] for t in rec["trials"] if t.get("phase_grade") and t["status"] in ACTIVE]
        if active_grades and p["status"] == "active" and "registry_phase" not in (p.get("skip_checks") or []):
            top = max(active_grades, key=GRADES.index)
            if GRADES.index(top) > GRADES.index(p["stage"]) and p["stage"] != "approved":
                flags.append({"level": "warn", "text": "Registry lists an active {} trial, ahead of the curated stage ({}).".format(top, p["stage"])})
        verified = parse_date(p.get("verified_on"))
        if verified and (TODAY - verified).days > CURATION_STALE_DAYS:
            flags.append({"level": "warn", "text": "Curated summary last verified {} ({} days ago).".format(p["verified_on"], (TODAY - verified).days)})
        for u in p.get("unverified") or []:
            flags.append({"level": "info", "text": "Unverified: " + u})
        for s in p.get("sources", []):
            if links.get(s["url"], {}).get("state") == "broken":
                flags.append({"level": "warn", "text": "Source link appears broken: " + s["label"]})
        rec["flags"] = flags
        # Fill next catalyst from the registry when the curated record leaves the date open.
        nc = dict(p["next_catalyst"]) if p.get("next_catalyst") else None
        if nc and not nc.get("date"):
            pinned = nc.get("nct_id")
            fut = sorted(((parse_date(t["primary_completion"]), t) for t in rec["trials"]
                          if (not pinned or t["nct_id"] == pinned) and t["status"] in ACTIVE and parse_date(t.get("primary_completion"))
                          and parse_date(t["primary_completion"]) >= TODAY - dt.timedelta(days=60)),
                         key=lambda x: x[0])
            if fut:
                d, t = fut[0]
                nc.update({"date": d.isoformat(), "date_precision": "registry",
                           "nct_id": t["nct_id"], "registry_date_type": t.get("primary_completion_type")})
        rec["next_catalyst"] = nc
        rec["my_commentary"] = _note(notes, "programs", p["id"], "commentary")
        rec["verified_on"] = str(p.get("verified_on"))
        out_programs.append(rec)

    # ---- PubMed: recent literature per approach (citations only)
    cure_queries = {
        "cell_replacement": '("stem cell-derived islet*" OR "islet transplantation" OR zimislecel) AND "type 1 diabetes"',
        "gene_edited": '(hypoimmune OR "gene-edited" OR "immune-evasive" OR CRISPR) AND islet* AND "type 1 diabetes"',
        "encapsulation": '(encapsulat* OR macroencapsulation OR "cell pouch") AND islet* AND diabetes',
        "immune": '(teplizumab OR baricitinib OR "disease-modifying" OR "beta-cell preservation") AND "type 1 diabetes" AND (trial OR randomized)',
    }
    papers = (prev_cure.get("papers") or {})
    if live and "pubmed" not in skip:
        papers = run_source("PubMed (cure literature)",
                            lambda: {k: pubmed.recent(q, retmax=6) for k, q in cure_queries.items()}, papers)

    # ---- headlines (link-out only)
    news_items = prev_cure.get("news") or {}
    if live and "news" not in skip:
        def fetch_news():
            out = {}
            for p in programs:
                if p["status"] == "discontinued":
                    continue
                short = re.split(r"[(—]", p["name"])[0].strip()
                out[p["id"]] = news.headlines('"{}" diabetes'.format(short), n=3)
            return out
        news_items = run_source("Google News RSS (headlines)", fetch_news, news_items)
    for rec in out_programs:
        rec["news"] = (news_items or {}).get(rec["id"], [])

    write("programs.json", {"programs": out_programs, "papers": papers, "news": news_items})
    write("trials.json", {"trials": trials})
    write("changes.json", {"changes": changes})

    # ---- GLP-1: registry scan, literature, FDA label check
    glp_terms = "semaglutide OR tirzepatide OR liraglutide OR dulaglutide OR exenatide OR retatrutide OR orforglipron OR cagrilintide OR survodutide OR \"GLP-1\""
    tracked = set(nct_ids)
    scan = prev_glp.get("registry_scan", [])
    if live and "ctgov" not in skip:
        def do_scan():
            res = ctgov.search(glp_terms, statuses=sorted(ACTIVE) + ["COMPLETED"], page_size=100)
            keep = []
            for t in res:
                conds = " ".join(t.get("conditions") or []) + " " + (t.get("title") or "")
                if not re.search(r"type 1|T1D|T1DM|type I diab", conds, re.I):
                    continue
                if t["status"] == "COMPLETED" and (parse_date(t.get("completion")) or dt.date(1900, 1, 1)) < TODAY - dt.timedelta(days=730):
                    continue
                t["tracked"] = t["nct_id"] in tracked
                keep.append(t)
            return keep
        scan = run_source("ClinicalTrials.gov (GLP-1 scan)", do_scan, scan)
    glp_queries = {
        "adjunct": '(semaglutide OR tirzepatide OR liraglutide OR "GLP-1 receptor agonist*") AND "type 1 diabetes" AND (adjunct* OR "time in range" OR HbA1c OR weight)',
        "beta_cell": '("GLP-1" OR semaglutide OR liraglutide OR tirzepatide) AND ("new-onset" OR "recent-onset" OR "beta-cell function" OR "C-peptide" OR "stage 2") AND "type 1 diabetes"',
        "safety": '("GLP-1" OR semaglutide OR tirzepatide OR liraglutide) AND "type 1 diabetes" AND (ketoacidosis OR DKA OR hypoglycemia OR ketosis)',
    }
    glp_papers = prev_glp.get("papers", {})
    if live and "pubmed" not in skip:
        glp_papers = run_source("PubMed (GLP-1 in T1D)",
                                lambda: {k: pubmed.recent(q, retmax=8) for k, q in glp_queries.items()}, glp_papers)
    labels = prev_glp.get("labels", [])
    if live and "openfda" not in skip:
        labels = run_source("openFDA drug labels", openfda.glp1_label_checks, labels)
    write("glp1.json", {"registry_scan": scan, "papers": glp_papers, "labels": labels,
                        "any_t1d_label": any(l.get("approved_for_t1d") for l in labels or [])})

    # ---- Devices + FDA decision feed
    fda_feed = (load_prev("devices.json") or {}).get("fda_feed", [])
    if live and "openfda" not in skip:
        fda_feed = run_source("openFDA device decisions", openfda.device_decisions, fda_feed)
    out_devices = []
    for d in devices:
        rec = dict(d)
        note = (notes.get("devices") or {}).get(d["id"]) or {}
        rec["my_take"] = _note(notes, "devices", d["id"], "user_take")
        rec["my_rating"] = note.get("rating")
        out_devices.append(rec)
    write("devices.json", {"devices": out_devices, "fda_feed": fda_feed, "code_labels": openfda.DEVICE_CODES})

    # ---- Companies: quotes + SEC filings
    out_comp = []
    for c in comps_y["companies"]:
        rec = dict(c)
        prev = prev_comp.get(c["ticker"], {})
        q = prev.get("quote")
        if live and "markets" not in skip:
            q = run_source("Market data: " + c["ticker"], lambda: markets.quote(c["ticker"]), q)
        rec["quote"] = q
        f, cik = prev.get("filings", []), prev.get("cik")
        if live and c.get("sec") and "sec" not in skip:
            got = run_source("SEC EDGAR: " + c["ticker"], lambda: sec.recent_filings(c["ticker"]), (cik, f))
            cik, f = got if got else (cik, f)
        rec["cik"], rec["filings"] = cik, f
        out_comp.append(rec)
    write("companies.json", {"companies": out_comp})

    # ---- Catalyst calendar
    cats = []
    for c in cats_y["catalysts"]:
        cats.append({**c, "date": str(c["date"]), "end": str(c["end"]) if c.get("end") else None, "origin": "curated"})
    for p in out_programs:
        nc = p.get("next_catalyst")
        if nc and nc.get("date") and nc.get("date_precision") != "registry":
            cats.append({"date": str(nc["date"]), "type": "company", "precision": nc.get("date_precision", "exact"),
                         "title": "{} — {}".format(p["name"], nc["label"]), "related": p["id"],
                         "source": p["sources"][0]["url"], "origin": "program"})
    seen = set()
    for p in out_programs:
        for t in p["trials"]:
            pcd = parse_date(t.get("primary_completion"))
            if t["nct_id"] in seen or t["status"] not in ACTIVE or not pcd:
                continue
            if pcd < TODAY - dt.timedelta(days=120) or pcd > TODAY + dt.timedelta(days=365 * 4):
                continue
            seen.add(t["nct_id"])
            cats.append({"date": pcd.isoformat(), "type": "readout",
                         "precision": "registry-" + (t.get("primary_completion_type") or "").lower(),
                         "title": "{} — primary completion ({})".format(t.get("acronym") or p["name"], t["nct_id"]),
                         "related": p["id"], "source": t["url"], "origin": "registry",
                         "note": "Registry primary completion is when the last patient finishes the primary endpoint, not a results date. Toplines typically follow 1–6 months later."})
    for c in out_comp:
        e = (c.get("quote") or {}).get("next_earnings")
        ed = parse_date(e)
        if ed and TODAY - dt.timedelta(days=7) <= ed <= TODAY + dt.timedelta(days=120):
            cats.append({"date": ed.isoformat(), "type": "earnings", "precision": "exact",
                         "title": "{} ({}) earnings".format(c["name"], c["ticker"]), "origin": "yfinance",
                         "source": "https://finance.yahoo.com/quote/" + c["ticker"]})
    cats.sort(key=lambda x: x["date"])
    write("catalysts.json", {"catalysts": cats})

    # ---- Market model inputs
    write("market.json", market_y)

    # ---- Meta
    n_flags = sum(len(p["flags"]) for p in out_programs)
    write("meta.json", {
        "built_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "offline_build": offline,
        "counts": {"programs": len(out_programs), "trials": len(trials), "devices": len(out_devices),
                   "companies": len(out_comp), "catalysts": len(cats), "flags": n_flags},
        "sources": {**prev_meta.get("sources", {}), **health},
        "links": links,
    })
    bad = [k for k, v in health.items() if not v["ok"]]
    print("Built {} programs, {} trials, {} catalysts, {} flags. Source failures: {}".format(
        len(out_programs), len(trials), len(cats), n_flags, bad or "none"))


def _note(notes, kind, key, field):
    v = ((notes.get(kind) or {}).get(key) or {}).get(field)
    if not v or not str(v).strip() or str(v).strip().startswith("(Placeholder"):
        return None
    return str(v).strip()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="no network; rebuild from curated + last JSON")
    ap.add_argument("--skip", default="", help="comma list: ctgov,pubmed,openfda,sec,markets,news,links")
    a = ap.parse_args()
    build({s.strip() for s in a.skip.split(",") if s.strip()}, a.offline)
