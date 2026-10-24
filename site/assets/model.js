/* Cure Impact Model — browser port of pipeline/model.py `run()` so the inputs can move.
   Keep the two in step: tests/test_model.py pins the Python results, and on load this
   script checks its own preset outputs against the Python numbers embedded in the page
   (window.TTC.modelCheck reports any mismatch). */
(function () {
  "use strict";
  var TTC = window.TTC, el = document.getElementById("model-data");
  if (!TTC || !el) return;
  var D = JSON.parse(el.textContent), M = D.market, START = 2025, END = 2040;
  var money = TTC.money, pct = TTC.pct, num = TTC.num, esc = TTC.esc;
  var KEYS = ["approval", "peak", "ramp", "cap", "price", "sh_cgm", "sh_pump", "sh_ins", "residual", "g_cgm", "g_pump", "g_ins"];
  var FMT = {
    approval: String, ramp: function (v) { return v + " yrs"; }, cap: function (v) { return Math.round(v / 1000) + "K"; },
    price: function (v) { return money(v, 2); }, g_cgm: function (v) { return pct(v, 1); }, g_pump: function (v) { return pct(v, 1); },
    g_ins: function (v) { return pct(v, 1); }
  };

  // ---------------------------------------------------------- the model (mirror of model.run)
  function smooth(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }
  function run(v) {
    var mk = M.markets, pop = M.population.t1d_global_m * 1e6, size = v.size || "value", rows = [], prev = 0;
    for (var y = START; y <= END; y++) {
      var t = y - M.base_year;
      var b = { cgm: mk.cgm[size] * 1e9 * Math.pow(1 + v.g_cgm, t), pump: mk.pump[size] * 1e9 * Math.pow(1 + v.g_pump, t), insulin: mk.insulin[size] * 1e9 * Math.pow(1 + v.g_ins, t) };
      var target = y < v.approval ? 0 : v.peak * smooth((y - v.approval + 1) / v.ramp) * pop;
      var cured = Math.min(target, prev + v.cap), p = cured / pop;
      var t1d = { cgm: b.cgm * v.sh_cgm, pump: b.pump * v.sh_pump, insulin: b.insulin * v.sh_ins };
      var disp = { cgm: t1d.cgm * p * (1 - v.residual), pump: t1d.pump * p, insulin: t1d.insulin * p };
      var nw = Math.max(0, cured - prev);
      rows.push({ year: y, penetration: p, cured: cured, new_patients: nw, t1d_baseline: t1d, displaced: disp,
        displaced_total: disp.cgm + disp.pump + disp.insulin, t1d_baseline_total: t1d.cgm + t1d.pump + t1d.insulin, cure_sales: nw * v.price });
      prev = cured;
    }
    return { rows: rows, summary: summarize(rows) };
  }
  function summarize(rows) {
    var by = {}, peak = rows[0], cum = 0, cumD = 0;
    rows.forEach(function (r) { by[r.year] = r; if (r.cure_sales > peak.cure_sales) peak = r; cum += r.cure_sales; cumD += r.displaced_total; });
    var out = {};
    [2030, 2035, 2040].forEach(function (y) {
      var r = by[y];
      out[y] = { displaced: r.displaced, displaced_total: r.displaced_total, share_of_t1d: r.t1d_baseline_total ? r.displaced_total / r.t1d_baseline_total : 0, penetration: r.penetration, cured: r.cured };
    });
    out.peak_cure_sales = peak.cure_sales; out.peak_cure_year = peak.cure_sales > 0 ? peak.year : null;
    out.cum_cure_sales = cum; out.cum_displaced = cumD;
    return out;
  }
  TTC.runModel = run;

  // ---------------------------------------------------------- self-check against Python output
  var mism = [];
  Object.keys(D.check).forEach(function (k) {
    var s = run(D.defaults[k]).summary, c = D.check[k];
    [["d2035", s[2035].displaced_total], ["d2040", s[2040].displaced_total], ["cum", s.cum_cure_sales]].forEach(function (p) {
      if (Math.abs(p[1] - c[p[0]]) > Math.max(1, Math.abs(c[p[0]]) * 1e-9)) mism.push(k + "." + p[0] + ": js " + p[1] + " vs py " + c[p[0]]);
    });
  });
  TTC.modelCheck = mism.length ? mism : "ok";
  if (mism.length && window.console) console.error("Cure Impact Model: JS and Python disagree", mism);

  // ---------------------------------------------------------- inputs
  var form = document.getElementById("model-inputs");
  function input(k) { return document.getElementById("in-" + k); }
  function read() {
    var v = {};
    KEYS.forEach(function (k) { v[k] = parseFloat(input(k).value); });
    v.size = document.getElementById("in-size").value;
    return v;
  }
  function write(v) {
    KEYS.forEach(function (k) { if (v[k] != null) input(k).value = v[k]; });
    if (v.size) document.getElementById("in-size").value = v.size;
  }
  function outputs(v) {
    KEYS.forEach(function (k) { var o = document.getElementById("out-" + k); if (o) o.textContent = (FMT[k] || function (x) { return pct(x, 0); })(v[k]); });
  }
  function matchPreset(v) {
    var hit = null;
    Object.keys(D.defaults).forEach(function (k) {
      var d = D.defaults[k], same = KEYS.every(function (key) { return Math.abs(d[key] - v[key]) < 1e-9; }) && d.size === v.size;
      if (same) hit = k;
    });
    return hit;
  }

  // ---------------------------------------------------------- rendering
  var chartEl = document.getElementById("model-chart");
  var chartCfg = JSON.parse(chartEl.getAttribute("data-chart"));
  function stat(v, l, d) { return '<div class="stat"><div class="v">' + v + '</div><div class="l">' + l + "</div>" + (d ? '<div class="d">' + d + "</div>" : "") + "</div>"; }
  function render(v) {
    var res = run(v), s = res.summary, rows = res.rows, r40 = rows[rows.length - 1];
    document.getElementById("model-stats").innerHTML =
      stat(money(s[2035].displaced_total), "Displaced in 2035", pct(s[2035].share_of_t1d, 1) + " of T1D-attributable revenue") +
      stat(money(s[2040].displaced_total), "Displaced in 2040", pct(s[2040].share_of_t1d, 1) + " of T1D-attributable revenue") +
      stat(pct(s[2040].penetration, 1), "T1D patients cured by 2040", Math.round(s[2040].cured / 1000) + "K people") +
      stat(money(s.peak_cure_sales), "Peak annual cure sales", s.peak_cure_year ? "in " + s.peak_cure_year : "no approval in window") +
      stat(money(s.cum_cure_sales), "Cumulative cure sales", START + "–" + END + " vs " + money(s.cum_displaced) + " displaced");
    // chart
    chartCfg.series = [
      { name: "Insulin", cls: "s1", values: rows.map(function (r) { return r.displaced.insulin; }) },
      { name: "CGM", cls: "s2", values: rows.map(function (r) { return r.displaced.cgm; }) },
      { name: "Pumps / AID", cls: "s3", values: rows.map(function (r) { return r.displaced.pump; }) }
    ];
    chartCfg.marks = [2035, 2040];
    chartCfg.label = "Projected T1D-attributable revenue displaced by a functional cure, 2025 to 2040";
    chartEl.innerHTML = TTC.stackSvg(chartCfg);
    TTC.attachChart(chartEl, chartCfg);
    // market table
    var mt = [["insulin", "Insulin"], ["cgm", "CGM"], ["pump", "Pumps / AID"]].map(function (m) {
      return "<tr><td>" + m[1] + '</td><td class="num">' + money(s[2030].displaced[m[0]]) + '</td><td class="num">' + money(s[2035].displaced[m[0]]) + '</td><td class="num">' + money(s[2040].displaced[m[0]]) + '</td><td class="num">' + pct(r40.t1d_baseline[m[0]] ? r40.displaced[m[0]] / r40.t1d_baseline[m[0]] : 0, 1) + "</td></tr>";
    }).join("");
    mt += '<tr class="total"><td>Total</td><td class="num">' + money(s[2030].displaced_total) + '</td><td class="num">' + money(s[2035].displaced_total) + '</td><td class="num">' + money(s[2040].displaced_total) + '</td><td class="num">' + pct(s[2040].share_of_t1d, 1) + "</td></tr>";
    document.querySelector("#market-table tbody").innerHTML = mt;
    // year table
    document.querySelector("#year-table tbody").innerHTML = rows.map(function (r) {
      return '<tr><td class="num">' + r.year + '</td><td class="num">' + num(r.cured) + '</td><td class="num">' + pct(r.penetration, 1) + '</td><td class="num">' + num(r.new_patients) + '</td><td class="num">' + money(r.displaced.insulin) + '</td><td class="num">' + money(r.displaced.cgm) + '</td><td class="num">' + money(r.displaced.pump) + '</td><td class="num"><b>' + money(r.displaced_total) + '</b></td><td class="num">' + money(r.cure_sales) + "</td></tr>";
    }).join("");
    sensitivity(v);
    readAcross(v, rows);
    return res;
  }

  function heatBins(grid) {
    var flat = [].concat.apply([], grid).slice().sort(function (a, b) { return a - b; }), n = flat.length;
    return grid.map(function (row) { return row.map(function (x) { return Math.min(5, Math.floor(6 * flat.indexOf(x) / n)); }); });
  }
  function sensitivity(v) {
    var S = D.sens;
    var g1 = S.approval.map(function (ap) { return S.peak.map(function (pk) { return run(Object.assign({}, v, { approval: ap, peak: pk })).summary[2040].displaced_total; }); });
    var g2 = S.price.map(function (pr) { return S.cap.map(function (cp) { return run(Object.assign({}, v, { price: pr, cap: cp })).summary.cum_cure_sales; }); });
    fillHeat("sens-ap", g1, function (ri, ci) { return S.approval[ri] === v.approval && Math.abs(S.peak[ci] - v.peak) < 1e-9; });
    fillHeat("sens-pc", g2, function (ri, ci) { return Math.abs(S.price[ri] - v.price) < 1 && Math.abs(S.cap[ci] - v.cap) < 1; });
  }
  function fillHeat(id, grid, isCur) {
    var bins = heatBins(grid), rows = document.querySelectorAll("#" + id + " tbody tr");
    rows.forEach(function (tr, ri) {
      tr.querySelectorAll("td.cell").forEach(function (td, ci) {
        td.textContent = money(grid[ri][ci]);
        td.setAttribute("data-b", bins[ri][ci]);
        td.classList.toggle("cur", isCur(ri, ci));
      });
    });
  }
  function readAcross(v, rows) {
    var by = {}; rows.forEach(function (r) { by[r.year] = r; });
    var share = { cgm: v.sh_cgm, pump: v.sh_pump, insulin: v.sh_ins }, growth = { cgm: v.g_cgm, pump: v.g_pump, insulin: v.g_ins };
    D.companies.forEach(function (c) {
      var tr = document.querySelector('#ra-table tr[data-ticker="' + c.ticker + '"]');
      if (!tr) return;
      var tds = tr.querySelectorAll("td");
      var keys = Object.keys(c.exposure || {});
      if (c.revenue && keys.length) {
        tds[4].textContent = pct(keys.reduce(function (a, m) { return a + c.exposure[m] * share[m]; }, 0), 1);
        [2035, 2040].forEach(function (y, j) {
          var d = keys.reduce(function (a, m) {
            return a + c.revenue * c.exposure[m] * Math.pow(1 + growth[m], y - M.base_year) * share[m] * by[y].penetration * (m === "cgm" ? 1 - v.residual : 1);
          }, 0);
          tds[5 + j * 2].textContent = money(d);
          tds[6 + j * 2].innerHTML = "<b>" + pct(d / c.revenue, 1) + "</b>";
        });
      }
    });
  }

  // ---------------------------------------------------------- state, presets, URL
  var desc = document.getElementById("scenario-desc");
  var current;
  function update(pushUrl) {
    var v = read();
    outputs(v);
    var pre = matchPreset(v);
    document.querySelectorAll("[data-preset]").forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-preset") === pre ? "true" : "false"); });
    desc.textContent = pre ? D.scenarios[pre].thesis : "Custom inputs. Pick a preset to reset the scenario levers.";
    current = render(v);
    current.inputs = v;
    if (pushUrl) {
      var q = KEYS.map(function (k) { return k + "=" + v[k]; }).join("&") + "&size=" + v.size;
      try { history.replaceState(null, "", pre ? "#" + pre : "#" + q); } catch (e) { /* file:// or sandboxed: skip */ }
    }
  }
  var raf = 0;
  form.addEventListener("input", function () { cancelAnimationFrame(raf); raf = requestAnimationFrame(function () { update(true); }); });
  form.addEventListener("change", function () { update(true); });
  document.querySelectorAll("[data-preset]").forEach(function (b) {
    b.addEventListener("click", function () {
      var k = b.getAttribute("data-preset"), d = D.defaults[k];
      write(d); update(true);
    });
  });
  document.getElementById("reset-btn").addEventListener("click", function () { write(D.defaults.base); update(true); });
  document.getElementById("print-btn").addEventListener("click", function () { window.print(); });
  document.getElementById("share-btn").addEventListener("click", function () {
    var b = this, url = location.href, old = b.textContent;
    function done() { b.textContent = "Link copied"; setTimeout(function () { b.textContent = old; }, 1600); }
    if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { window.prompt("Copy this link:", url); });
    else window.prompt("Copy this link:", url);
  });
  document.getElementById("csv-current").addEventListener("click", function () {
    var v = current.inputs, lines = ["# Tracking the Cure — Cure Impact Model, custom inputs. Model output, not a forecast. Not investment advice.",
      "# inputs: " + KEYS.map(function (k) { return k + "=" + v[k]; }).join("; ") + "; size=" + v.size,
      "year,t1d_patients_cured,share_of_t1d_cured,new_patients_treated,insulin_displaced_usd,cgm_displaced_usd,pump_displaced_usd,total_displaced_usd,t1d_attributable_baseline_usd,cure_sales_usd"];
    current.rows.forEach(function (r) {
      lines.push([r.year, Math.round(r.cured), r.penetration.toFixed(6), Math.round(r.new_patients), Math.round(r.displaced.insulin), Math.round(r.displaced.cgm), Math.round(r.displaced.pump), Math.round(r.displaced_total), Math.round(r.t1d_baseline_total), Math.round(r.cure_sales)].join(","));
    });
    var blob = new Blob([lines.join("\n") + "\n"], { type: "text/csv" }), a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = "cure-impact-model-custom.csv";
    document.body.appendChild(a); a.click(); setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  });

  // initial state from the URL (#bull, or #approval=...&peak=...)
  var h = decodeURIComponent(location.hash.slice(1));
  write(D.defaults.base);  // never trust browser-restored form state
  if (D.defaults[h]) write(D.defaults[h]);
  else if (h.indexOf("=") > 0) {
    var v = {};
    h.split("&").forEach(function (kv) {
      var p = kv.split("="), k = p[0];
      if (KEYS.indexOf(k) >= 0 && !isNaN(parseFloat(p[1]))) v[k] = parseFloat(p[1]);
      if (k === "size" && /^(value|low|high)$/.test(p[1])) v.size = p[1];
    });
    write(v);
  }
  update(false);
})();
