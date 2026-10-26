"""Server-side SVG charts. Same geometry as site/assets/app.js so the browser can attach a
hover/keyboard layer (and, on the model page, redraw) without changing the look.

Every chart is emitted as <div class="chart" data-chart='{json}'> + inline <svg>, with a
text alternative (role="img" + aria-label) and the numbers available in a nearby table.
"""
import html
import json
import math

W, H = 760, 320
M = {"t": 16, "r": 64, "b": 28, "l": 52}


def esc(s):
    return html.escape(str(s), quote=True)


def money(n, dp=1):
    """$1.2B style. Matches fmtMoney() in app.js."""
    if n is None:
        return "—"
    a = abs(n)
    sign = "−" if n < 0 else ""
    for div, suf in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if a >= div:
            v = a / div
            d = dp if v < 100 else 0
            return "{}${:,.{}f}{}".format(sign, v, d, suf)
    return "{}${:,.0f}".format(sign, a)


def nice_step(span, target=4):
    if span <= 0:
        return 1
    raw = span / target
    p = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * p:
            return m * p
    return 10 * p


def _scale(vmax):
    step = nice_step(vmax or 1)
    top = step * math.ceil((vmax or 1) / step)
    return step, top


def stacked_area(x, series, label, axis_fmt=money, marks=(), w=W, h=H, chart_id=None):
    """Stacked area. series = [{name, key, cls ('s1'..), values}], bottom first."""
    n = len(x)
    tot = [sum(s["values"][i] for s in series) for i in range(n)]
    step, top = _scale(max(tot) if tot else 1)
    pw, ph = w - M["l"] - M["r"], h - M["t"] - M["b"]

    def X(i):
        return M["l"] + (i / (n - 1)) * pw

    def Y(v):
        return M["t"] + ph - (v / top) * ph

    out = ['<svg viewBox="0 0 {} {}" role="img" aria-label="{}" preserveAspectRatio="xMidYMid meet">'.format(w, h, esc(label))]
    out.append('<g class="grid">')
    v = 0.0
    while v <= top + 1e-9:
        out.append('<line x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(M["l"], w - M["r"], Y(v), Y(v)))
        v += step
    out.append("</g>")
    v = 0.0
    while v <= top + 1e-9:
        out.append('<text x="{}" y="{:.1f}" text-anchor="end" dy="0.32em">{}</text>'.format(M["l"] - 8, Y(v), esc(axis_fmt(v, 0) if v else "$0")))
        v += step
    cum = [0.0] * n
    for s in series:
        lo = cum[:]
        hi = [lo[i] + s["values"][i] for i in range(n)]
        pts = " ".join("{:.1f},{:.1f}".format(X(i), Y(hi[i])) for i in range(n))
        back = " ".join("{:.1f},{:.1f}".format(X(i), Y(lo[i])) for i in reversed(range(n)))
        out.append('<polygon class="area fill-{}" points="{} {}"/>'.format(s["cls"], pts, back))
        # 1px surface seam between bands (the 2px-gap spec, scaled to a thin area chart)
        out.append('<polyline fill="none" stroke="var(--surface)" stroke-width="1" points="{}"/>'.format(pts))
        cum = hi
    out.append('<line class="base" x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(M["l"], w - M["r"], Y(0), Y(0)))
    every = 1 if n <= 8 else (2 if n <= 16 else 5)
    for i, xv in enumerate(x):
        if i % every == 0 or i == n - 1:
            out.append('<text x="{:.1f}" y="{}" text-anchor="middle">{}</text>'.format(X(i), h - 8, esc(xv)))
    for mk in marks:
        if str(mk) in [str(v) for v in x]:
            i = [str(v) for v in x].index(str(mk))
            out.append('<line x1="{0:.1f}" x2="{0:.1f}" y1="{1}" y2="{2:.1f}" stroke="var(--ink-2)" stroke-dasharray="2 3"/>'.format(X(i), M["t"], Y(0)))
            out.append('<circle class="marker" cx="{:.1f}" cy="{:.1f}" r="4" fill="var(--ink)"/>'.format(X(i), Y(tot[i])))
            anchor = "end" if i > n * 0.8 else "middle"
            out.append('<text class="val" x="{:.1f}" y="{:.1f}" text-anchor="{}">{}</text>'.format(X(i) - (6 if anchor == "end" else 0), Y(tot[i]) - 10, anchor, esc(money(tot[i]))))
    # direct labels at right edge (<= 4 series), de-overlapped
    ends, prev = [], 0.0
    for s in series:
        mid = prev + s["values"][-1] / 2
        prev += s["values"][-1]
        ends.append([Y(mid), s])
    ends.sort(key=lambda e: e[0])
    for k in range(1, len(ends)):
        if ends[k][0] - ends[k - 1][0] < 13:
            ends[k][0] = ends[k - 1][0] + 13
    for yy, s in ends:
        if s["values"][-1] > 0:
            out.append('<text class="lbl" x="{}" y="{:.1f}" dy="0.32em">{}</text>'.format(w - M["r"] + 8, yy, esc(s["name"])))
    out.append("</svg>")
    cfg = {"type": "stack", "x": [str(v) for v in x], "w": w, "h": h, "m": M, "top": top,
           "series": [{"name": s["name"], "cls": s["cls"], "values": [round(v) for v in s["values"]]} for s in series]}
    return _wrap(out, cfg, chart_id)


def line(x, series, label, axis_fmt=None, w=W, h=280, area=False, chart_id=None, y_min=None):
    """Simple line chart, auto-scaled (used for price history)."""
    n = len(x)
    allv = [v for s in series for v in s["values"] if v is not None]
    lo, hi = min(allv), max(allv)
    if y_min is not None:
        lo = y_min
    pad = (hi - lo) * 0.08 or 1
    lo2, hi2 = lo - pad, hi + pad
    step = nice_step(hi2 - lo2)
    lo2 = step * math.floor(lo2 / step)
    hi2 = step * math.ceil(hi2 / step)
    m = dict(M, r=16)
    pw, ph = w - m["l"] - m["r"], h - m["t"] - m["b"]
    fmt = axis_fmt or (lambda v: "{:,.0f}".format(v) if step >= 1 else "{:,.2f}".format(v))

    def X(i):
        return m["l"] + (i / max(1, n - 1)) * pw

    def Y(v):
        return m["t"] + ph - ((v - lo2) / (hi2 - lo2)) * ph

    out = ['<svg viewBox="0 0 {} {}" role="img" aria-label="{}">'.format(w, h, esc(label)), '<g class="grid">']
    v = lo2
    while v <= hi2 + 1e-9:
        out.append('<line x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(m["l"], w - m["r"], Y(v), Y(v)))
        v += step
    out.append("</g>")
    v = lo2
    while v <= hi2 + 1e-9:
        out.append('<text x="{}" y="{:.1f}" text-anchor="end" dy="0.32em">{}</text>'.format(m["l"] - 8, Y(v), esc(fmt(v))))
        v += step
    for s in series:
        pts = [(X(i), Y(v)) for i, v in enumerate(s["values"]) if v is not None]
        d = " ".join(("M" if k == 0 else "L") + "{:.1f} {:.1f}".format(px, py) for k, (px, py) in enumerate(pts))
        if area and pts:
            out.append('<path d="{} L{:.1f} {:.1f} L{:.1f} {:.1f} Z" class="fill-{}" opacity="0.10"/>'.format(d, pts[-1][0], Y(lo2), pts[0][0], Y(lo2), s["cls"]))
        out.append('<path class="line stroke-{}" d="{}"/>'.format(s["cls"], d))
    ticks = _date_ticks(x)
    for i in ticks:
        out.append('<text x="{:.1f}" y="{}" text-anchor="middle">{}</text>'.format(X(i), h - 8, esc(_short_date(x[i]))))
    out.append("</svg>")
    cfg = {"type": "line", "x": x, "w": w, "h": h, "m": m, "lo": lo2, "hi": hi2,
           "series": [{"name": s["name"], "cls": s["cls"], "values": s["values"]} for s in series]}
    return _wrap(out, cfg, chart_id)


def _date_ticks(x, k=5):
    n = len(x)
    if n <= 1:
        return [0]
    return sorted({round(i * (n - 1) / (k - 1)) for i in range(k)})


def _short_date(s):
    s = str(s)
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    if len(s) >= 7 and s[4] == "-":
        return "{} {}".format(months[int(s[5:7]) - 1], s[2:4] and "’" + s[2:4])
    return s


def spark(values, w=96, h=28):
    vals = [v for v in values or [] if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    rng = (hi - lo) or 1
    d = " ".join(("M" if i == 0 else "L") + "{:.1f} {:.1f}".format(i / (len(vals) - 1) * w, h - 2 - (v - lo) / rng * (h - 4))
                 for i, v in enumerate(vals))
    cls = "up" if vals[-1] >= vals[0] else "down"
    return '<svg class="spark {}" viewBox="0 0 {} {}" aria-hidden="true" focusable="false"><path d="{}"/></svg>'.format(cls, w, h, d)


def _wrap(out, cfg, chart_id):
    idattr = ' id="{}"'.format(esc(chart_id)) if chart_id else ""
    return '<div class="chart"{} data-chart="{}">{}</div>'.format(idattr, esc(json.dumps(cfg, separators=(",", ":"))), "".join(out))


def context_area(x, baseline, displaced, label, marker=None, w=760, h=360, compact=False, chart_id=None):
    """Displaced revenue drawn inside the revenue it is a share of (same year, same denominator).

    baseline  : T1D-attributable revenue in the no-cure baseline, per year (model output)
    displaced : revenue displaced by the cure, per year (model output; always <= baseline)
    marker    : (year, text) for an assumption marker such as the approval year
    Direct labels sit at the right edge; compact=True is the narrow (phone) layout.
    """
    n = len(x)
    m = {"t": 34, "r": 16 if compact else 150, "b": 28, "l": 50}
    step, top = _scale(max(baseline) if baseline else 1)
    pw, ph = w - m["l"] - m["r"], h - m["t"] - m["b"]

    def X(i):
        return m["l"] + (i / (n - 1)) * pw

    def Y(v):
        return m["t"] + ph - (v / top) * ph

    out = ['<svg viewBox="0 0 {} {}" role="img" aria-label="{}" preserveAspectRatio="xMidYMid meet">'.format(w, h, esc(label))]
    out.append('<g class="grid">')
    v = 0.0
    while v <= top + 1e-9:
        out.append('<line x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(m["l"], w - m["r"], Y(v), Y(v)))
        v += step
    out.append("</g>")
    v = 0.0
    while v <= top + 1e-9:
        out.append('<text x="{}" y="{:.1f}" text-anchor="end" dy="0.32em">{}</text>'.format(m["l"] - 8, Y(v), esc(money(v, 0) if v else "$0")))
        v += step
    base_pts = " ".join("{:.1f},{:.1f}".format(X(i), Y(baseline[i])) for i in range(n))
    floor = "{:.1f},{:.1f} {:.1f},{:.1f}".format(X(n - 1), Y(0), X(0), Y(0))
    out.append('<polygon class="fill-baseline" points="{} {}"/>'.format(base_pts, floor))
    out.append('<polyline class="line stroke-baseline" points="{}"/>'.format(base_pts))
    disp_pts = " ".join("{:.1f},{:.1f}".format(X(i), Y(displaced[i])) for i in range(n))
    out.append('<polygon class="fill-accent" points="{} {}"/>'.format(disp_pts, floor))
    out.append('<polyline class="line stroke-accent" points="{}"/>'.format(disp_pts))
    out.append('<line class="base" x1="{}" x2="{}" y1="{:.1f}" y2="{:.1f}"/>'.format(m["l"], w - m["r"], Y(0), Y(0)))
    every = 5 if n > 8 else 1
    for i, xv in enumerate(x):
        if i % every == 0 or i == n - 1:
            out.append('<text x="{:.1f}" y="{}" text-anchor="middle">{}</text>'.format(X(i), h - 8, esc(xv)))
    if marker and str(marker[0]) in [str(v) for v in x]:
        i = [str(v) for v in x].index(str(marker[0]))
        out.append('<line class="xmark" x1="{0:.1f}" x2="{0:.1f}" y1="{1}" y2="{2:.1f}"/>'.format(X(i), m["t"] - 14, Y(0)))
        out.append('<text class="lbl" x="{:.1f}" y="{}" text-anchor="middle">{}</text>'.format(X(i), m["t"] - 20, esc(marker[1])))
    # end values: the baseline and the displaced share of it in the last year
    xe = X(n - 1)
    out.append('<circle class="marker" cx="{:.1f}" cy="{:.1f}" r="4" fill="var(--ink-2)"/>'.format(xe, Y(baseline[-1])))
    out.append('<circle class="marker" cx="{:.1f}" cy="{:.1f}" r="4" fill="var(--accent)"/>'.format(xe, Y(displaced[-1])))
    if compact:
        out.append('<text class="val" x="{:.1f}" y="{:.1f}" text-anchor="end">{}</text>'.format(xe - 8, Y(baseline[-1]) - 10, esc(money(baseline[-1]))))
        out.append('<text class="val accent" x="{:.1f}" y="{:.1f}" text-anchor="end">{}</text>'.format(xe - 8, Y(displaced[-1]) - 10, esc(money(displaced[-1]))))
    else:
        out.append('<text class="val" x="{:.1f}" y="{:.1f}">{}</text>'.format(xe + 10, Y(baseline[-1]) + 4, esc(money(baseline[-1]))))
        out.append('<text x="{:.1f}" y="{:.1f}">T1D-attributable</text>'.format(xe + 10, Y(baseline[-1]) + 20))
        out.append('<text x="{:.1f}" y="{:.1f}">revenue, no cure</text>'.format(xe + 10, Y(baseline[-1]) + 34))
        out.append('<text class="val accent" x="{:.1f}" y="{:.1f}">{}</text>'.format(xe + 10, Y(displaced[-1]) - 2, esc(money(displaced[-1]))))
        out.append('<text x="{:.1f}" y="{:.1f}">displaced</text>'.format(xe + 10, Y(displaced[-1]) + 12))
    out.append('<text x="{:.1f}" y="{:.1f}" text-anchor="start" class="val">{}</text>'.format(X(0) + 6, Y(baseline[0]) - 8, esc(money(baseline[0]))))
    out.append("</svg>")
    cfg = {"type": "context", "x": [str(v) for v in x], "w": w, "h": h, "m": m, "top": top,
           "series": [{"name": "T1D-attributable revenue, no cure", "cls": "baseline", "values": [round(v) for v in baseline]},
                      {"name": "Displaced by a cure", "cls": "accent", "values": [round(v) for v in displaced]}]}
    return _wrap(out, cfg, chart_id)
