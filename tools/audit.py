"""Full regression audit of a rendered site (development only).

    python -m tools.audit --site _site --out docs/redesign/final/audit.json

1. Every page x 1440/768/375 x light/dark: console errors, failed requests, horizontal overflow,
   WCAG AA text contrast, heading order inside <main>.
2. Scripted interactions: theme toggle, More menu, mobile menu, model presets/sliders/views/export menu,
   JS = Python model check, pipeline arrange/matrix, sortable tables, filter chips, chart keyboard tooltips,
   print stylesheet on the model page.
Exit code 1 if anything fails.
"""
import argparse
import functools
import http.server
import json
import pathlib
import socketserver
import sys
import threading

from playwright.sync_api import sync_playwright

from tools.shots import METRICS_JS


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


def serve(root):
    httpd = socketserver.TCPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(root)))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:{}/".format(httpd.server_address[1])


def interactions(page, base):
    """Each check returns (name, ok, detail)."""
    out = []

    def check(name, fn):
        try:
            ok, detail = fn()
        except Exception as e:  # a crash is a failure, with the reason
            ok, detail = False, "{}: {}".format(type(e).__name__, e)
        out.append({"check": name, "ok": bool(ok), "detail": detail})

    page.set_viewport_size({"width": 1440, "height": 900})
    page.goto(base, wait_until="networkidle")

    def theme():
        before = page.evaluate("document.documentElement.getAttribute('data-theme')")
        page.click("#theme-btn")
        after = page.evaluate("document.documentElement.getAttribute('data-theme')")
        page.reload(wait_until="networkidle")
        kept = page.evaluate("document.documentElement.getAttribute('data-theme')")
        page.click("#theme-btn")
        return after in ("dark", "light") and after != before and kept == after, "{}→{} (kept after reload: {})".format(before, after, kept)
    check("Theme toggle switches and persists", theme)

    def more():
        page.click(".nav-more > summary")
        opened = page.evaluate("document.querySelector('.nav-more').open")
        page.keyboard.press("Escape")
        closed = not page.evaluate("document.querySelector('.nav-more').open")
        return opened and closed, "opens, Escape closes"
    check("More menu", more)

    def hero_tip():
        page.focus(".chart-wide .hit")
        page.keyboard.press("End")
        t = page.inner_text(".chart-wide .tip")
        return "3.5%" in t and "$91.0B" in t, t.replace("\n", " ")
    check("Homepage chart keyboard tooltip", hero_tip)

    page.goto(base + "model/", wait_until="networkidle")

    def model_check():
        return page.evaluate("TTC.modelCheck") == "ok", page.evaluate("JSON.stringify(TTC.modelCheck)")
    check("Model: JS equals Python for all presets", model_check)

    def presets():
        res = {}
        for k in ("bear", "base", "bull", "immuno"):
            page.click('[data-preset="{}"]'.format(k))
            page.wait_for_timeout(120)
            res[k] = page.inner_text("#model-stats .stat:nth-child(2) .v")
        expect = page.evaluate("Object.fromEntries(Object.entries(JSON.parse(document.getElementById('model-data').textContent).check).map(([k,v])=>[k, TTC.money(v.d2040)]))")
        return res == expect, "2040 tiles {} vs Python {}".format(res, expect)
    check("Model: presets update tiles to Python values", presets)

    def slider_sync():
        page.click('[data-preset="base"]')
        page.eval_on_selector("#in-cap", "e => { e.value = 60000; e.dispatchEvent(new Event('input', {bubbles: true})); e.dispatchEvent(new Event('change', {bubbles: true})); }")
        page.wait_for_timeout(250)
        tile = page.inner_text("#model-stats .stat:nth-child(2) .v")
        ctx = page.eval_on_selector_all("#model-context-chart text.val.accent", "els => els.map(e => e.textContent)")
        bar = page.inner_text("#ra-bars li:first-child .bv")
        row = page.eval_on_selector('#ra-table tr[data-ticker="PODD"]', "tr => tr.querySelectorAll('td')[8].textContent.trim()")
        label = page.inner_text("[data-scenario-label]")
        ok = tile in ctx and bar == row and label == "current inputs"
        page.click('[data-preset="base"]')
        return ok, "tile {} context {} bar {} table {} label {}".format(tile, ctx, bar, row, label)
    check("Model: sliders keep tiles, context chart, bars and table in sync", slider_sync)

    def views():
        page.click('[data-view="context"]')
        a = page.is_visible("#view-context") and not page.is_visible("#view-market")
        page.click('[data-view="market"]')
        b = page.is_visible("#view-market")
        return a and b, "context/market toggle"
    check("Model: chart view toggle", views)

    def export():
        page.click(".menu-btn > summary")
        visible = page.is_visible("#csv-current")
        with page.expect_download() as d:
            page.click("#csv-current")
        name = d.value.suggested_filename
        return visible and name.endswith(".csv"), "download " + name
    check("Model: Export menu downloads CSV", export)

    def printable():
        page.emulate_media(media="print")
        hidden = page.evaluate("getComputedStyle(document.querySelector('.menu-btn')).display === 'none' && getComputedStyle(document.querySelector('.masthead')).display === 'none'")
        page.emulate_media(media="screen")
        return hidden, "print hides chrome and export menu"
    check("Model: print stylesheet", printable)

    page.goto(base + "pipeline/", wait_until="networkidle")

    def arrange():
        page.click('[data-arrange="gap"]')
        first = page.eval_on_selector("#pipe-track .hype-row:not(.hidden)", "e => e.dataset.gap")
        gaps = page.eval_on_selector_all("#pipe-track .hype-row:not(.hidden)", "els => els.map(e => +e.dataset.gap)")
        page.click('[data-pview="matrix"]')
        m = page.is_visible("#pipe-matrix")
        page.click('[data-pview="track"]')
        page.click('[data-arrange="approach"]')
        groups = page.eval_on_selector_all("#pipe-track .hype-group:not(.hidden)", "els => els.length")
        active = [g for g in gaps if g >= 0]
        return active == sorted(active, reverse=True) and m and groups > 0, "gap order {}, matrix {}, groups restored {}".format(gaps, m, groups)
    check("Pipeline: arrange by gap, matrix view, restore grouping", arrange)

    page.goto(base + "companies/", wait_until="networkidle")

    def companies():
        page.click('[data-filter-for="co-table"] [data-val="cgm_pump"]')
        shown = page.inner_text("#co-count")
        page.click('[data-filter-for="co-table"] [data-val="all"]')
        page.click("#co-table thead th:nth-child(2) button")
        page.click("#co-table thead th:nth-child(2) button")
        sort = page.eval_on_selector("#co-table thead th:nth-child(2)", "e => e.getAttribute('aria-sort')")
        return shown.startswith("9") and sort == "descending", "filter: {}, sort: {}".format(shown, sort)
    check("Companies: group filter and sortable column", companies)

    page.goto(base + "catalysts/", wait_until="networkidle")

    def catalysts():
        page.click("#all-catalysts > summary")
        page.click('[data-filter-for="cat-table"] [data-val="readout"]')
        shown = page.inner_text("#cat-count")
        return page.is_visible("#cat-table") and shown != "", "readouts: " + shown
    check("Catalysts: full table opens and filters", catalysts)

    page.set_viewport_size({"width": 375, "height": 812})
    page.goto(base, wait_until="networkidle")

    def mobile_menu():
        page.click(".nav-toggle > summary")
        n = page.eval_on_selector_all(".nav-panel a", "els => els.filter(e => e.offsetParent).length")
        return n >= 10, "{} links visible".format(n)
    check("Mobile menu lists every destination", mobile_menu)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="_site")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    site = pathlib.Path(a.site).resolve()
    pages = sorted(("" if p.parent == site else str(p.parent.relative_to(site)) + "/") for p in site.rglob("index.html"))
    pages = [p for p in pages if not p.startswith("styleguide")]
    httpd, base = serve(site)
    report = {"pages": {}, "interactions": []}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for theme in ("light", "dark"):
            for w, h in ((1440, 900), (768, 1024), (375, 812)):
                ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=theme)
                page = ctx.new_page()
                errors, failed = [], []
                page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("requestfailed", lambda r: failed.append(r.url) if r.url.startswith(base) else None)
                page.on("response", lambda r: failed.append("{} {}".format(r.status, r.url)) if r.url.startswith(base) and r.status >= 400 else None)
                for p in pages:
                    errors.clear(); failed.clear()
                    page.goto(base + p, wait_until="networkidle")
                    m = page.evaluate(METRICS_JS)
                    issues = {}
                    if errors: issues["console"] = list(errors)
                    if failed: issues["requests"] = list(failed)
                    if m["overflow"]: issues["overflow"] = m["overflow"]
                    if m["n_contrast_fails"]: issues["contrast"] = m["contrast_fails"]
                    if m["heading_skips"]: issues["heading_skips"] = m["heading_skips"]
                    if issues:
                        report["pages"]["{}@{}-{}".format(p or "home", w, theme)] = issues
                ctx.close()
        ctx = browser.new_context(accept_downloads=True)
        report["interactions"] = interactions(ctx.new_page(), base)
        ctx.close()
        browser.close()
    httpd.shutdown()
    report["summary"] = {"page_configurations": len(pages) * 6, "with_issues": len(report["pages"]),
                         "interactions_passed": sum(i["ok"] for i in report["interactions"]),
                         "interactions_total": len(report["interactions"])}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(report, indent=1))
    print(json.dumps(report["summary"]))
    for i in report["interactions"]:
        print("  {} {} — {}".format("PASS" if i["ok"] else "FAIL", i["check"], i["detail"][:140]))
    for k, v in list(report["pages"].items())[:20]:
        print("  ISSUE", k, v)
    ok = not report["pages"] and all(i["ok"] for i in report["interactions"])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
