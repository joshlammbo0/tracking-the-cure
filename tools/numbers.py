"""Numerical-integrity guard for the visual redesign (development only; never deployed).

Renders the site from the frozen data snapshot at a fixed date, extracts every displayed number, unit and
caveat, and compares it with the pre-redesign baseline.

    python -m tools.numbers baseline      # capture docs/redesign/baseline/numbers.json (run once, before changes)
    python -m tools.numbers check         # re-render + compare; exit 1 on any unapproved difference

What is captured, per page:
  * every text run containing a digit, "$", "%" or "×"   -> values, units, precision
  * every text run containing a caveat keyword            -> "not a forecast", "assumption", "estimate", ...
  * SVG <text> (chart axes, direct labels, annotations)
Plus the model outputs (data/model.json, all scenarios, sensitivities, read-across) and the CSV export.

A value that only moved (same text, different heading or element) is reported as MOVED, not as a change.
Approved differences are listed in docs/redesign/approved_changes.yaml (page + text, added or removed).
"""
import argparse
import collections
import hashlib
import html.parser
import json
import pathlib
import re
import subprocess
import sys
import tempfile

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
BASE = ROOT / "docs" / "redesign" / "baseline"
SNAPSHOT = BASE / "data"
TODAY = "2026-10-26"
APPROVED = ROOT / "docs" / "redesign" / "approved_changes.yaml"

NUMERIC = re.compile(r"[0-9$%×]")
CAVEATS = re.compile(r"assumption|estimate|forecast|not (?:medical|investment) advice|not advice|analysis|registry|"
                     r"unverified|model output|not disclosed|not modelled|guidance|placeholder|approx|unknown|"
                     r"not a results date|personal perspective", re.I)
SKIP_TAGS = {"script", "style", "noscript", "title"}


class Extract(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.heading, self.items, self._h, self._htext = [], "", [], None, []
        self.in_main = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "circle", "line", "rect", "path", "polygon", "polyline"):
            return
        cls = (a.get("class") or "").split()
        self.stack.append(tag + ("." + cls[0] if cls else ""))
        if tag in ("h1", "h2", "h3", "h4"):
            self._h, self._htext = tag, []
        if tag == "main":
            self.in_main = True

    def handle_endtag(self, tag):
        if tag in ("br", "img", "input", "meta", "link", "hr", "source", "circle", "line", "rect", "path", "polygon", "polyline"):
            return
        if self._h == tag:
            self.heading = " ".join("".join(self._htext).split())[:80]
            self._h = None
        while self.stack:
            t = self.stack.pop()
            if t.split(".")[0] == tag:
                break
        if tag == "main":
            self.in_main = False

    def handle_data(self, data):
        if self._h:
            self._htext.append(data)
        if any(t.split(".")[0] in SKIP_TAGS for t in self.stack):
            return
        text = " ".join(data.split())
        if not text or not (NUMERIC.search(text) or CAVEATS.search(text)):
            return
        region = "svg" if any(t.startswith("svg") for t in self.stack) else ("main" if self.in_main else "chrome")
        self.items.append({"text": text, "heading": self.heading, "region": region,
                           "el": "/".join(self.stack[-3:])})


def extract_site(site):
    site = pathlib.Path(site)
    pages = {}
    for f in sorted(site.rglob("*.html")):
        rel = str(f.relative_to(site))
        p = Extract()
        p.feed(f.read_text())
        pages[rel] = p.items
    model = json.loads((site / "data" / "model.json").read_text())
    csv = (site / "model" / "cure-impact-model.csv").read_bytes()
    return {"pages": pages, "model": model, "csv_sha256": hashlib.sha256(csv).hexdigest()}


def render_frozen(out):
    subprocess.run([sys.executable, "-m", "pipeline.render", "--data-dir", str(SNAPSHOT), "--today", TODAY, "--out", str(out)],
                   cwd=ROOT, check=True, capture_output=True)


def flatten(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, "{}.{}".format(prefix, k) if prefix else str(k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from flatten(v, "{}[{}]".format(prefix, i))
    else:
        yield prefix, obj


def compare(base, cur, approved):
    report = {"changed_model": [], "csv_changed": base["csv_sha256"] != cur["csv_sha256"], "pages": {}}
    bm, cm = dict(flatten(base["model"])), dict(flatten(cur["model"]))
    for k in sorted(set(bm) | set(cm)):
        if bm.get(k) != cm.get(k):
            report["changed_model"].append({"key": k, "before": bm.get(k), "after": cm.get(k)})
    ok_add = {(a["page"], a["text"]) for a in (approved.get("added") or [])}
    ok_rem = {(a["page"], a["text"]) for a in (approved.get("removed") or [])}
    for page in sorted(set(base["pages"]) | set(cur["pages"])):
        b = collections.Counter(i["text"] for i in base["pages"].get(page, []))
        c = collections.Counter(i["text"] for i in cur["pages"].get(page, []))
        removed = [t for t in (b - c).elements() if (page, t) not in ok_rem]
        added = [t for t in (c - b).elements() if (page, t) not in ok_add]
        bctx = {i["text"]: (i["heading"], i["region"]) for i in base["pages"].get(page, [])}
        cctx = {i["text"]: (i["heading"], i["region"]) for i in cur["pages"].get(page, [])}
        moved = sorted(t for t in set(bctx) & set(cctx) if bctx[t] != cctx[t])
        if removed or added or moved:
            report["pages"][page] = {"removed": removed, "added": added, "moved": moved}
    report["blocking"] = bool(report["changed_model"] or report["csv_changed"] or
                              any(v["removed"] or v["added"] for v in report["pages"].values()))
    return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["baseline", "check"])
    ap.add_argument("--report", default=str(ROOT / "docs" / "redesign" / "numbers_report.json"))
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        out = pathlib.Path(tmp) / "site"
        render_frozen(out)
        cur = extract_site(out)
    if a.cmd == "baseline":
        (BASE / "numbers.json").write_text(json.dumps(cur, indent=1, ensure_ascii=False))
        n = sum(len(v) for v in cur["pages"].values())
        print("Baseline captured: {} pages, {} text items, {} model values.".format(len(cur["pages"]), n, len(dict(flatten(cur["model"])))))
        return 0
    base = json.loads((BASE / "numbers.json").read_text())
    approved = yaml.safe_load(APPROVED.read_text()) if APPROVED.exists() else {}
    rep = compare(base, cur, approved or {})
    pathlib.Path(a.report).write_text(json.dumps(rep, indent=1, ensure_ascii=False))
    n_pages = len(rep["pages"])
    moved = sum(len(v["moved"]) for v in rep["pages"].values())
    rem = sum(len(v["removed"]) for v in rep["pages"].values())
    add = sum(len(v["added"]) for v in rep["pages"].values())
    print("Model values changed: {} · CSV changed: {} · pages with differences: {} · removed: {} · added: {} · moved only: {}"
          .format(len(rep["changed_model"]), rep["csv_changed"], n_pages, rem, add, moved))
    print("RESULT:", "BLOCKING differences, see " + a.report if rep["blocking"] else "no unapproved numerical or caveat changes")
    return 1 if rep["blocking"] else 0


if __name__ == "__main__":
    sys.exit(main())
