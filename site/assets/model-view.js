/* Cure Impact Model — presentation layer for the visuals added in the redesign.
   Calculations stay in model.js (TTC.runModel, a port of pipeline/model.py). This file only reads the same
   inputs, calls TTC.runModel, and draws: the "In context" chart, the company read-across bars, and the
   sensitivity legends. It never writes to any element model.js owns. */
(function () {
  "use strict";
  var TTC = window.TTC, dataEl = document.getElementById("model-data");
  if (!TTC || !TTC.runModel || !dataEl) return;
  var D = JSON.parse(dataEl.textContent), money = TTC.money, pct = TTC.pct, esc = TTC.esc;
  var KEYS = ["approval", "peak", "ramp", "cap", "price", "sh_cgm", "sh_pump", "sh_ins", "residual", "g_cgm", "g_pump", "g_ins"];
  var form = document.getElementById("model-inputs");

  function read() {
    var v = {};
    KEYS.forEach(function (k) { v[k] = parseFloat(document.getElementById("in-" + k).value); });
    v.size = document.getElementById("in-size").value;
    return v;
  }
  function presetOf(v) {
    var hit = null;
    Object.keys(D.defaults).forEach(function (k) {
      var d = D.defaults[k];
      if (KEYS.every(function (key) { return Math.abs(d[key] - v[key]) < 1e-9; }) && d.size === v.size) hit = k;
    });
    return hit;
  }
  function niceStep(span) {
    var raw = span / 4, p = Math.pow(10, Math.floor(Math.log10(raw)));
    var ms = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < ms.length; i++) if (raw <= ms[i] * p) return ms[i] * p;
    return 10 * p;
  }

  // ---------------------------------------------------------- "In context" chart (same geometry as charts.context_area)
  function contextSvg(x, base, disp, approval, w, h, compact) {
    var n = x.length, m = { t: 34, r: compact ? 16 : 150, b: 28, l: 50 };
    var vmax = Math.max.apply(null, base) || 1, step = niceStep(vmax), top = step * Math.ceil(vmax / step);
    var pw = w - m.l - m.r, ph = h - m.t - m.b;
    function X(i) { return m.l + (i / (n - 1)) * pw; }
    function Y(v) { return m.t + ph - (v / top) * ph; }
    var o = ['<svg viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="T1D-attributable revenue in the no-cure baseline and the part a cure displaces, ' + x[0] + " to " + x[n - 1] + '" preserveAspectRatio="xMidYMid meet"><g class="grid">'];
    for (var v = 0; v <= top + 1e-9; v += step) o.push('<line x1="' + m.l + '" x2="' + (w - m.r) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"/>');
    o.push("</g>");
    for (v = 0; v <= top + 1e-9; v += step) o.push('<text x="' + (m.l - 8) + '" y="' + Y(v).toFixed(1) + '" text-anchor="end" dy="0.32em">' + (v ? money(v, 0) : "$0") + "</text>");
    function pts(a) { return a.map(function (val, i) { return X(i).toFixed(1) + "," + Y(val).toFixed(1); }).join(" "); }
    var floor = X(n - 1).toFixed(1) + "," + Y(0).toFixed(1) + " " + X(0).toFixed(1) + "," + Y(0).toFixed(1);
    o.push('<polygon class="fill-baseline" points="' + pts(base) + " " + floor + '"/><polyline class="line stroke-baseline" points="' + pts(base) + '"/>');
    o.push('<polygon class="fill-accent" points="' + pts(disp) + " " + floor + '"/><polyline class="line stroke-accent" points="' + pts(disp) + '"/>');
    o.push('<line class="base" x1="' + m.l + '" x2="' + (w - m.r) + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"/>');
    x.forEach(function (xv, i) { if (i % 5 === 0 || i === n - 1) o.push('<text x="' + X(i).toFixed(1) + '" y="' + (h - 8) + '" text-anchor="middle">' + xv + "</text>"); });
    var ai = x.indexOf(String(approval));
    if (ai >= 0) {
      o.push('<line class="xmark" x1="' + X(ai).toFixed(1) + '" x2="' + X(ai).toFixed(1) + '" y1="' + (m.t - 14) + '" y2="' + Y(0).toFixed(1) + '"/>');
      o.push('<text class="lbl" x="' + X(ai).toFixed(1) + '" y="' + (m.t - 20) + '" text-anchor="middle">Approval ' + approval + " · assumption</text>");
    }
    var xe = X(n - 1), bl = base[n - 1], dl = disp[n - 1];
    o.push('<circle class="marker" cx="' + xe.toFixed(1) + '" cy="' + Y(bl).toFixed(1) + '" r="4" fill="var(--ink-2)"/><circle class="marker" cx="' + xe.toFixed(1) + '" cy="' + Y(dl).toFixed(1) + '" r="4" fill="var(--accent)"/>');
    if (compact) {
      o.push('<text class="val" x="' + (xe - 8).toFixed(1) + '" y="' + (Y(bl) - 10).toFixed(1) + '" text-anchor="end">' + money(bl) + "</text>");
      o.push('<text class="val accent" x="' + (xe - 8).toFixed(1) + '" y="' + (Y(dl) - 10).toFixed(1) + '" text-anchor="end">' + money(dl) + "</text>");
    } else {
      o.push('<text class="val" x="' + (xe + 10).toFixed(1) + '" y="' + (Y(bl) + 4).toFixed(1) + '">' + money(bl) + '</text><text x="' + (xe + 10).toFixed(1) + '" y="' + (Y(bl) + 20).toFixed(1) + '">T1D-attributable</text><text x="' + (xe + 10).toFixed(1) + '" y="' + (Y(bl) + 34).toFixed(1) + '">revenue, no cure</text>');
      o.push('<text class="val accent" x="' + (xe + 10).toFixed(1) + '" y="' + (Y(dl) - 2).toFixed(1) + '">' + money(dl) + '</text><text x="' + (xe + 10).toFixed(1) + '" y="' + (Y(dl) + 12).toFixed(1) + '">displaced</text>');
    }
    o.push('<text x="' + (X(0) + 6).toFixed(1) + '" y="' + (Y(base[0]) - 8).toFixed(1) + '" text-anchor="start" class="val">' + money(base[0]) + "</text></svg>");
    return { svg: o.join(""), cfg: { type: "context", x: x, w: w, h: h, m: m, top: top,
      series: [{ name: "T1D-attributable revenue, no cure", cls: "baseline", values: base }, { name: "Displaced by a cure", cls: "accent", values: disp }] } };
  }
  var ctxEl = document.getElementById("model-context-chart");
  function drawContext(res, v) {
    var rows = res.rows, x = rows.map(function (r) { return String(r.year); });
    var base = rows.map(function (r) { return r.t1d_baseline_total; }), disp = rows.map(function (r) { return r.displaced_total; });
    var width = ctxEl.clientWidth || 760, compact = width < 600;
    var out = contextSvg(x, base, disp, v.approval, compact ? Math.max(300, width) : 760, compact ? 300 : 360, compact);
    var holder = document.createElement("div");
    holder.className = "chart";
    holder.innerHTML = out.svg;
    ctxEl.innerHTML = "";
    ctxEl.appendChild(holder);
    TTC.attachChart(holder, out.cfg);
  }

  // ---------------------------------------------------------- company read-across bars (same formula as model.read_across)
  var barsEl = document.getElementById("ra-bars");
  function displacedPct(c, v, res, year) {
    var r = res.rows.filter(function (row) { return row.year === year; })[0];
    var share = { cgm: v.sh_cgm, pump: v.sh_pump, insulin: v.sh_ins }, growth = { cgm: v.g_cgm, pump: v.g_pump, insulin: v.g_ins };
    var d = 0;
    Object.keys(c.exposure).forEach(function (mk) {
      d += c.revenue * c.exposure[mk] * Math.pow(1 + growth[mk], year - D.market.base_year) * share[mk] * r.penetration * (mk === "cgm" ? 1 - v.residual : 1);
    });
    return d / c.revenue;
  }
  function drawBars(res, v) {
    if (!barsEl || !D.categories) return;
    var byT = {}; D.companies.forEach(function (c) { byT[c.ticker] = c; });
    var items = D.categories.map(function (cat) { return { cat: cat, val: displacedPct(byT[cat.tickers[0]], v, res, 2040) }; });
    items.sort(function (a, b) { return b.val - a.val; });
    var max = Math.max.apply(null, items.map(function (i) { return i.val; })) || 1;
    barsEl.innerHTML = items.map(function (i) {
      return '<li><span class="bl">' + esc(i.cat.label) + (i.cat.members ? '<span class="sub">' + esc(i.cat.members) + "</span>" : "") + '</span><span class="bar" aria-hidden="true"><i style="width:' + (100 * i.val / max).toFixed(1) + '%"></i></span><span class="bv">' + pct(i.val, 1) + "</span></li>";
    }).join("");
  }

  // ---------------------------------------------------------- sensitivity legends (shading is by rank within each grid)
  function drawLegends(v) {
    // Same grids as the heatmaps (D.sens axes, same run()), so the legend never depends on model.js's DOM timing.
    var S = D.sens;
    var g1 = [], g2 = [];
    S.approval.forEach(function (ap) { S.peak.forEach(function (pk) { g1.push(TTC.runModel(Object.assign({}, v, { approval: ap, peak: pk })).summary[2040].displaced_total); }); });
    S.price.forEach(function (pr) { S.cap.forEach(function (cp) { g2.push(TTC.runModel(Object.assign({}, v, { price: pr, cap: cp })).summary.cum_cure_sales); }); });
    [["sens-ap", g1], ["sens-pc", g2]].forEach(function (p) {
      var lo = document.querySelector('[data-legend-lo="' + p[0] + '"]'), hi = document.querySelector('[data-legend-hi="' + p[0] + '"]');
      if (lo && hi) { lo.textContent = money(Math.min.apply(null, p[1])); hi.textContent = money(Math.max.apply(null, p[1])); }
    });
  }

  // ---------------------------------------------------------- labels that say which inputs are shown
  function drawLabels(v) {
    var pre = presetOf(v), txt = pre ? D.scenarios[pre].label.split(":")[0].toLowerCase() + " case" : "current inputs";
    if (pre === "immuno") txt = "immunosuppression-required case";
    document.querySelectorAll("[data-scenario-label]").forEach(function (el) { el.textContent = txt; });
  }

  function update() {
    var v = read(), res = TTC.runModel(v);
    drawContext(res, v);
    drawBars(res, v);
    drawLegends(v);
    drawLabels(v);
  }
  var pending = 0;
  function later() { clearTimeout(pending); pending = setTimeout(update, 0); }
  form.addEventListener("input", later);
  form.addEventListener("change", later);
  document.querySelectorAll("[data-preset], #reset-btn").forEach(function (b) { b.addEventListener("click", later); });

  // ---------------------------------------------------------- view toggle
  var views = { market: document.getElementById("view-market"), context: document.getElementById("view-context") };
  document.querySelectorAll("[data-view]").forEach(function (b) {
    b.addEventListener("click", function () {
      var k = b.getAttribute("data-view");
      document.querySelectorAll("[data-view]").forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      Object.keys(views).forEach(function (name) { views[name].hidden = name !== k; });
      if (k === "context") update();
    });
  });
  var lastW = window.innerWidth;
  window.addEventListener("resize", function () { if (window.innerWidth !== lastW) { lastW = window.innerWidth; update(); } });
  update();
})();
