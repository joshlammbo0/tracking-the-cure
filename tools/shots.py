"""Full-page screenshots and layout/accessibility metrics for the redesign (development only).

    python -m tools.shots --site _site --out docs/redesign/phase1/after

Renders 6 configurations per representative page (1440x900, 768x1024, 375x812 x light/dark) and writes
metrics.json with the measurements used as acceptance criteria:
  first_viz_top   top of the first chart / pipeline viz (px from page top)
  chrome_h        height of disclaimer bar + masthead
  overflow        elements extending past the viewport width (outside scroll containers)
  contrast_fails  text nodes below WCAG AA, computed from rendered colours
  heading_skips   heading-level jumps inside <main>
  page_h          full page height
"""
import argparse
import functools
import http.server
import json
import pathlib
import socketserver
import threading

from playwright.sync_api import sync_playwright

PAGES = {"home": "", "model": "model/", "pipeline": "pipeline/", "company-dxcm": "companies/dxcm/",
         "program-zimislecel": "programs/vertex-zimislecel/"}
METRIC_ONLY = {"companies": "companies/", "catalysts": "catalysts/", "glp1": "glp1/", "research": "research/",
               "medtech-pumps": "medtech/pumps/", "methodology": "methodology/", "about": "about/"}
VIEWPORTS = [(1440, 900), (768, 1024), (375, 812)]

METRICS_JS = """() => {
  const W = innerWidth, d = document;
  const viz = [...d.querySelectorAll('main .chart svg, main .hype, main .quarters, main .dumbbell')].find(e => e.getClientRects().length);
  const mast = d.querySelector('.masthead');
  const over = [...d.querySelectorAll('main *, header *, footer *')].filter(e => {
    const r = e.getBoundingClientRect();
    return r.width && r.right > W + 1 && !e.closest('.table-scroll,.quarters,.nav,.nav-panel,.skip,.sr-only,.scroll-x');
  }).map(e => e.tagName + '.' + (e.className.baseVal ?? e.className)).slice(0, 5);
  function lum(c){const m=c.match(/[\\d.]+/g).map(Number);return m.slice(0,3).map(v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)}).reduce((a,v,i)=>a+v*[0.2126,0.7152,0.0722][i],0)}
  const fails = [];
  for (const el of d.querySelectorAll('body *')) {
    if (![...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) continue;
    if (el.closest('svg,.sr-only,.skip')) continue;
    const r = el.getBoundingClientRect(); if (!r.width) continue;
    const cs = getComputedStyle(el); let b = el, bg = null;
    while (b) { const c = getComputedStyle(b).backgroundColor; if (c && c !== 'rgba(0, 0, 0, 0)' && c !== 'transparent') { bg = c; break } b = b.parentElement }
    bg = bg || 'rgb(255,255,255)';
    const L1 = lum(cs.color), L2 = lum(bg), ratio = (Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05);
    const size = parseFloat(cs.fontSize), bold = parseInt(cs.fontWeight) >= 700;
    const need = (size >= 24 || (size >= 18.66 && bold)) ? 3 : 4.5;
    if (ratio < need) fails.push(el.tagName + '.' + el.className + ' ' + ratio.toFixed(2));
  }
  const hs = [...d.querySelectorAll('main h1, main h2, main h3, main h4, main h5')].map(h => +h.tagName[1]);
  let skips = 0; for (let i = 1; i < hs.length; i++) if (hs[i] - hs[i-1] > 1) skips++;
  const fig = [...d.querySelectorAll('main .display-figure')].find(e => e.getClientRects().length);
  return {hero_figure_bottom: fig ? Math.round(fig.getBoundingClientRect().bottom + scrollY) : null, first_viz_top: viz ? Math.round(viz.getBoundingClientRect().top + scrollY) : null,
          chrome_h: mast ? Math.round(mast.getBoundingClientRect().bottom) : null,
          overflow: over, contrast_fails: [...new Set(fails)].slice(0, 6), n_contrast_fails: fails.length,
          heading_skips: skips, page_h: d.documentElement.scrollHeight,
          model_check: window.TTC && window.TTC.modelCheck ? window.TTC.modelCheck : null};
}"""


def serve(root):
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, "http://127.0.0.1:{}/".format(httpd.server_address[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--site", default="_site")
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    httpd, base = serve(pathlib.Path(a.site).resolve())
    metrics = {}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in ("light", "dark"):
            for w, h in VIEWPORTS:
                ctx = browser.new_context(viewport={"width": w, "height": h}, color_scheme=theme,
                                          device_scale_factor=1, reduced_motion="reduce")
                page = ctx.new_page()
                for name, path in {**PAGES, **METRIC_ONLY}.items():
                    page.goto(base + path, wait_until="networkidle")
                    page.wait_for_timeout(250)
                    metrics["{}@{}-{}".format(name, w, theme)] = page.evaluate(METRICS_JS)
                    if name in PAGES and not a.no_images:
                        page.screenshot(path=str(out / "{}-{}-{}.jpg".format(name, w, theme)), full_page=True,
                                        type="jpeg", quality=72)
                ctx.close()
        browser.close()
    httpd.shutdown()
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print("Wrote {} screenshots and metrics for {} page-configurations to {}".format(
        0 if a.no_images else len(PAGES) * 6, len(metrics), out))


if __name__ == "__main__":
    main()
