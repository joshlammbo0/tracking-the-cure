/* Tracking the Cure — progressive enhancement for server-rendered pages.
   Pages work without JavaScript; this adds theme switching, sortable tables, chart
   tooltips (mouse + keyboard), catalyst filters, and shared helpers for model.js. */
(function () {
  "use strict";
  var TTC = (window.TTC = window.TTC || {});

  // ------------------------------------------------------------ formatting (mirrors pipeline/charts.py)
  function money(n, dp) {
    if (n == null || isNaN(n)) return "—";
    dp = dp == null ? 1 : dp;
    var a = Math.abs(n), sign = n < 0 ? "−" : "";
    var units = [[1e12, "T"], [1e9, "B"], [1e6, "M"], [1e3, "K"]];
    for (var i = 0; i < units.length; i++) {
      if (a >= units[i][0]) {
        var v = a / units[i][0], d = v < 100 ? dp : 0;
        return sign + "$" + v.toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) + units[i][1];
      }
    }
    return sign + "$" + Math.round(a).toLocaleString("en-US");
  }
  function pct(x, dp) {
    if (x == null || isNaN(x)) return "—";
    return (x * 100).toLocaleString("en-US", { minimumFractionDigits: dp || 0, maximumFractionDigits: dp || 0 }) + "%";
  }
  function num(x) { return x == null ? "—" : Math.round(x).toLocaleString("en-US"); }
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); }
  function niceStep(span, target) {
    target = target || 4;
    if (span <= 0) return 1;
    var raw = span / target, p = Math.pow(10, Math.floor(Math.log10(raw)));
    var ms = [1, 2, 2.5, 5, 10];
    for (var i = 0; i < ms.length; i++) if (raw <= ms[i] * p) return ms[i] * p;
    return 10 * p;
  }
  TTC.money = money; TTC.pct = pct; TTC.num = num; TTC.esc = esc;

  // ------------------------------------------------------------ theme
  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    try { localStorage.setItem("ttc-theme", t); } catch (e) { /* storage blocked: theme still applies this page */ }
  }
  function currentTheme() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t) return t;
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  var tb = document.getElementById("theme-btn");
  if (tb) {
    var sync = function () { tb.setAttribute("aria-label", "Switch to " + (currentTheme() === "dark" ? "light" : "dark") + " theme"); };
    sync();
    tb.addEventListener("click", function () { setTheme(currentTheme() === "dark" ? "light" : "dark"); sync(); });
  }

  // ------------------------------------------------------------ stacked area (same geometry as charts.stacked_area)
  TTC.stackSvg = function (cfg) {
    var x = cfg.x, n = x.length, M = cfg.m, w = cfg.w, h = cfg.h, series = cfg.series;
    var tot = x.map(function (_, i) { return series.reduce(function (s, se) { return s + se.values[i]; }, 0); });
    var vmax = Math.max.apply(null, tot) || 1, step = niceStep(vmax), top = step * Math.ceil(vmax / step);
    cfg.top = top;
    var pw = w - M.l - M.r, ph = h - M.t - M.b;
    function X(i) { return M.l + (i / (n - 1)) * pw; }
    function Y(v) { return M.t + ph - (v / top) * ph; }
    var o = ['<svg viewBox="0 0 ' + w + " " + h + '" role="img" aria-label="' + esc(cfg.label || "") + '" preserveAspectRatio="xMidYMid meet"><g class="grid">'];
    for (var v = 0; v <= top + 1e-9; v += step) o.push('<line x1="' + M.l + '" x2="' + (w - M.r) + '" y1="' + Y(v).toFixed(1) + '" y2="' + Y(v).toFixed(1) + '"/>');
    o.push("</g>");
    for (v = 0; v <= top + 1e-9; v += step) o.push('<text x="' + (M.l - 8) + '" y="' + Y(v).toFixed(1) + '" text-anchor="end" dy="0.32em">' + (v ? money(v, 0) : "$0") + "</text>");
    var cum = x.map(function () { return 0; });
    series.forEach(function (s) {
      var lo = cum.slice(), hi = lo.map(function (l, i) { return l + s.values[i]; });
      var pts = hi.map(function (vv, i) { return X(i).toFixed(1) + "," + Y(vv).toFixed(1); }).join(" ");
      var back = lo.map(function (vv, i) { return X(i).toFixed(1) + "," + Y(vv).toFixed(1); }).reverse().join(" ");
      o.push('<polygon class="area fill-' + s.cls + '" points="' + pts + " " + back + '"/>');
      o.push('<polyline fill="none" stroke="var(--surface)" stroke-width="1" points="' + pts + '"/>');
      cum = hi;
    });
    o.push('<line class="base" x1="' + M.l + '" x2="' + (w - M.r) + '" y1="' + Y(0).toFixed(1) + '" y2="' + Y(0).toFixed(1) + '"/>');
    var every = n <= 8 ? 1 : n <= 16 ? 2 : 5;
    x.forEach(function (xv, i) { if (i % every === 0 || i === n - 1) o.push('<text x="' + X(i).toFixed(1) + '" y="' + (h - 8) + '" text-anchor="middle">' + esc(xv) + "</text>"); });
    (cfg.marks || []).forEach(function (mk) {
      var i = x.indexOf(String(mk)); if (i < 0) return;
      o.push('<line x1="' + X(i).toFixed(1) + '" x2="' + X(i).toFixed(1) + '" y1="' + M.t + '" y2="' + Y(0).toFixed(1) + '" stroke="var(--ink-2)" stroke-dasharray="2 3"/>');
      o.push('<circle class="marker" cx="' + X(i).toFixed(1) + '" cy="' + Y(tot[i]).toFixed(1) + '" r="4" fill="var(--ink)"/>');
      var end = i > n * 0.8;
      o.push('<text class="val" x="' + (X(i) - (end ? 6 : 0)).toFixed(1) + '" y="' + (Y(tot[i]) - 10).toFixed(1) + '" text-anchor="' + (end ? "end" : "middle") + '">' + money(tot[i]) + "</text>");
    });
    var ends = [], prev = 0;
    series.forEach(function (s) { var last = s.values[n - 1]; ends.push([Y(prev + last / 2), s]); prev += last; });
    ends.sort(function (a, b) { return a[0] - b[0]; });
    for (var k = 1; k < ends.length; k++) if (ends[k][0] - ends[k - 1][0] < 13) ends[k][0] = ends[k - 1][0] + 13;
    ends.forEach(function (e) { if (e[1].values[n - 1] > 0) o.push('<text class="lbl" x="' + (w - M.r + 8) + '" y="' + e[0].toFixed(1) + '" dy="0.32em">' + esc(e[1].name) + "</text>"); });
    o.push("</svg>");
    return o.join("");
  };

  // ------------------------------------------------------------ hover + keyboard layer for any .chart[data-chart]
  TTC.attachChart = function (el, cfg) {
    cfg = cfg || JSON.parse(el.getAttribute("data-chart"));
    var svg = el.querySelector("svg");
    if (!svg) return;
    var n = cfg.x.length, M = cfg.m, pw = cfg.w - M.l - M.r, ph = cfg.h - M.t - M.b;
    var NS = "http://www.w3.org/2000/svg";
    var xh = document.createElementNS(NS, "line");
    xh.setAttribute("class", "xhair"); xh.setAttribute("y1", M.t); xh.setAttribute("y2", M.t + ph); xh.style.display = "none";
    svg.appendChild(xh);
    var hit = document.createElementNS(NS, "rect");
    hit.setAttribute("class", "hit"); hit.setAttribute("x", M.l); hit.setAttribute("y", M.t); hit.setAttribute("width", pw); hit.setAttribute("height", ph);
    hit.setAttribute("tabindex", "0"); hit.setAttribute("role", "slider");
    hit.setAttribute("aria-label", "Chart data: use left and right arrow keys to read each point");
    hit.setAttribute("aria-valuemin", 0); hit.setAttribute("aria-valuemax", n - 1);
    svg.appendChild(hit);
    var tip = el.querySelector(".tip");
    if (!tip) { tip = document.createElement("div"); tip.className = "tip"; tip.setAttribute("aria-hidden", "true"); el.appendChild(tip); }
    var live = el.querySelector(".sr-only[aria-live]");
    if (!live) { live = document.createElement("div"); live.className = "sr-only"; live.setAttribute("aria-live", "polite"); el.appendChild(live); }
    var cur = n - 1;
    function X(i) { return M.l + (i / Math.max(1, n - 1)) * pw; }
    function fmt(v) { return cfg.type === "line" ? (v == null ? "—" : v.toLocaleString("en-US", { maximumFractionDigits: 2, minimumFractionDigits: 2 })) : money(v); }
    function show(i) {
      cur = Math.max(0, Math.min(n - 1, i));
      var x = X(cur);
      xh.setAttribute("x1", x); xh.setAttribute("x2", x); xh.style.display = "";
      var rows = cfg.series.slice().reverse().map(function (s) {
        return '<div class="r"><i class="sw-' + s.cls + '"></i><span>' + esc(s.name) + '</span><span class="num">' + fmt(s.values[cur]) + "</span></div>";
      }).join("");
      var total = "";
      if (cfg.type === "stack") {
        var t = cfg.series.reduce(function (a, s) { return a + s.values[cur]; }, 0);
        total = '<div class="r" style="border-top:1px solid var(--rule);margin-top:4px;padding-top:4px"><i></i><span>Total</span><span class="num">' + money(t) + "</span></div>";
      }
      var label = cfg.type === "line" ? fmtDate(cfg.x[cur]) : cfg.x[cur];
      tip.innerHTML = "<b>" + esc(label) + "</b>" + rows + total;
      tip.style.display = "block";
      var box = svg.getBoundingClientRect(), scale = box.width / cfg.w;
      var left = x * scale + 12;
      if (left + tip.offsetWidth > box.width) left = x * scale - tip.offsetWidth - 12;
      tip.style.left = Math.max(0, left) + "px";
      tip.style.top = (M.t * scale) + "px";
      hit.setAttribute("aria-valuenow", cur);
      hit.setAttribute("aria-valuetext", label + ": " + cfg.series.map(function (s) { return s.name + " " + fmt(s.values[cur]); }).join(", "));
    }
    function hide() { tip.style.display = "none"; xh.style.display = "none"; }
    function idx(e) {
      var box = svg.getBoundingClientRect(), sx = (e.clientX - box.left) * (cfg.w / box.width);
      return Math.round(((sx - M.l) / pw) * (n - 1));
    }
    hit.addEventListener("pointermove", function (e) { show(idx(e)); });
    hit.addEventListener("pointerleave", hide);
    hit.addEventListener("focus", function () { show(cur); });
    hit.addEventListener("blur", hide);
    hit.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight" || e.key === "ArrowUp") { show(cur + 1); e.preventDefault(); }
      else if (e.key === "ArrowLeft" || e.key === "ArrowDown") { show(cur - 1); e.preventDefault(); }
      else if (e.key === "Home") { show(0); e.preventDefault(); }
      else if (e.key === "End") { show(n - 1); e.preventDefault(); }
      else if (e.key === "Escape") { hide(); }
    });
  };
  function fmtDate(s) {
    var m = String(s).match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return s;
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][+m[2] - 1] + " " + (+m[3]) + ", " + m[1];
  }
  document.querySelectorAll(".chart[data-chart]").forEach(function (el) { TTC.attachChart(el); });

  // ------------------------------------------------------------ sortable tables: <table class="data sortable">
  function cellVal(td) {
    var v = td.getAttribute("data-sort");
    if (v == null) v = td.textContent.trim();
    var n = parseFloat(String(v).replace(/[^0-9.\-−]/g, "").replace("−", "-"));
    return v !== "" && !isNaN(n) && /^[\s$−\-+]*[\d.,]+/.test(v) ? n : String(v).toLowerCase();
  }
  document.querySelectorAll("table.sortable").forEach(function (table) {
    var ths = table.querySelectorAll("thead th");
    ths.forEach(function (th, col) {
      if (th.hasAttribute("data-nosort")) return;
      var b = document.createElement("button");
      b.type = "button"; b.className = "sort"; b.innerHTML = th.innerHTML;
      th.innerHTML = ""; th.appendChild(b);
      b.addEventListener("click", function () {
        var dir = th.getAttribute("aria-sort") === "ascending" ? "descending" : "ascending";
        ths.forEach(function (o) { o.removeAttribute("aria-sort"); });
        th.setAttribute("aria-sort", dir);
        var tb = table.tBodies[0], rows = Array.prototype.slice.call(tb.rows);
        rows.sort(function (a, c) {
          var x = cellVal(a.cells[col]), y = cellVal(c.cells[col]);
          var blankX = x === "—" || x === "" || x === "unknown", blankY = y === "—" || y === "" || y === "unknown";
          if (blankX !== blankY) return blankX ? 1 : -1;
          var r = typeof x === "number" && typeof y === "number" ? x - y : String(x).localeCompare(String(y));
          return dir === "ascending" ? r : -r;
        });
        rows.forEach(function (r) { tb.appendChild(r); });
      });
    });
  });

  // ------------------------------------------------------------ filter chips: <div data-filter-for="id" data-attr="type">
  document.querySelectorAll("[data-filter-for]").forEach(function (bar) {
    var targets = bar.getAttribute("data-filter-for").split(",").map(function (id) { return document.getElementById(id.trim()); }).filter(Boolean);
    var attr = bar.getAttribute("data-attr");
    var status = document.getElementById(bar.getAttribute("data-status") || "");
    bar.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-val]");
      if (!b) return;
      bar.querySelectorAll("button[data-val]").forEach(function (o) { o.setAttribute("aria-pressed", o === b ? "true" : "false"); });
      var val = b.getAttribute("data-val"), shown = 0;
      targets.forEach(function (t) {
        t.querySelectorAll("[data-" + attr + "]").forEach(function (item) {
          var ok = val === "all" || item.getAttribute("data-" + attr).split(" ").indexOf(val) >= 0;
          item.classList.toggle("hidden", !ok);
          if (ok && item.tagName === "TR") shown++;
        });
      });
      if (status) status.textContent = shown + " shown";
    });
  });

  // ------------------------------------------------------------ open a closed <details> when a link targets something inside it
  function revealHash() {
    var id = decodeURIComponent(location.hash.slice(1)), t = id && document.getElementById(id);
    for (var d = t && t.parentElement; d; d = d.parentElement) if (d.tagName === "DETAILS") d.open = true;
    if (t) t.scrollIntoView();
  }
  window.addEventListener("hashchange", revealHash);
  if (location.hash.length > 1) revealHash();

  // ------------------------------------------------------------ copy buttons
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    b.addEventListener("click", function () {
      var txt = b.getAttribute("data-copy"), old = b.textContent;
      function done() { b.textContent = "Copied"; setTimeout(function () { b.textContent = old; }, 1600); }
      if (navigator.clipboard) navigator.clipboard.writeText(txt).then(done, function () { window.prompt("Copy this link:", txt); });
      else window.prompt("Copy this link:", txt);
    });
  });
})();
