/* Tracking the Cure — static frontend. Reads ./data/*.json written by the Python pipeline. */
(function () {
  "use strict";

  // ------------------------------------------------------------ constants
  var GRADES = ["preclinical", "phase1", "phase2", "phase3", "filed", "approved"];
  var GRADE_LABEL = { preclinical: "Preclinical", phase1: "Phase 1", phase2: "Phase 2", phase3: "Phase 3", filed: "Filed", approved: "Approved" };
  var APPROACH = {
    cell_replacement: { label: "Cell replacement", blurb: "Replace lost beta cells with donor or stem-cell-derived islets. Works today, but needs chronic immunosuppression." },
    gene_edited: { label: "Gene-edited / immune-evasive cells", blurb: "Engineer cells to hide from the immune system, so no immunosuppression is needed. This is the 'real cure' thesis, and it's the earliest stage." },
    encapsulation: { label: "Encapsulation & devices", blurb: "Physically shield cells inside a device. Historically hard: cells starve for oxygen, or the body walls off the device." },
    immune: { label: "Immune / disease-modifying", blurb: "Stop or slow the autoimmune attack. Today these delay or preserve function; none is a cure." }
  };
  var GLP_TOPIC = { adjunct: "Add-on therapy trials", beta_cell: "Beta-cell preservation", safety: "Safety & history" };
  var CAT_TYPE = { conference: "Conference", fda: "FDA", readout: "Readout", company: "Company", launch: "Launch", earnings: "Earnings" };
  var STATUS_LABEL = {
    RECRUITING: "Recruiting", NOT_YET_RECRUITING: "Not yet recruiting", ACTIVE_NOT_RECRUITING: "Active, not recruiting",
    ENROLLING_BY_INVITATION: "Enrolling by invitation", COMPLETED: "Completed", TERMINATED: "Terminated",
    WITHDRAWN: "Withdrawn", SUSPENDED: "Suspended", UNKNOWN: "Unknown"
  };
  var DEVICE_CAT = { cgm: "Continuous glucose monitors", pump: "Insulin pumps & AID systems", aid_algorithm: "AID algorithms", other: "Other diabetes software" };
  var DEVICE_STATUS = { marketed: "Marketed", cleared_not_launched: "Cleared, not yet launched", pipeline: "Pipeline", discontinued: "Discontinued" };

  var D = {}; // loaded data
  var state = { pipeFilter: "all", pipeStatus: "active", catType: "all", catPast: false, catSort: 1, compSort: { k: "market_cap_usd", d: -1 }, fdaCode: "all" };

  // ------------------------------------------------------------ helpers
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function safeUrl(u) { return /^https?:\/\//i.test(u || "") ? u : "#"; }
  function link(url, text, cls) {
    return '<a href="' + esc(safeUrl(url)) + '" target="_blank" rel="noopener"' + (cls ? ' class="' + cls + '"' : "") + ">" + esc(text) + "</a>";
  }
  function today() { var d = new Date(); return new Date(d.getFullYear(), d.getMonth(), d.getDate()); }
  function pdate(s) {
    if (!s) return null;
    s = String(s);
    if (/^\d{4}-\d{2}$/.test(s)) { var p = s.split("-"); return new Date(+p[0], +p[1], 0); }
    if (/^\d{4}$/.test(s)) return new Date(+s, 11, 31);
    var m = s.match(/^(\d{4})-(\d{2})-(\d{2})/);
    return m ? new Date(+m[1], +m[2] - 1, +m[3]) : null;
  }
  var MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fdate(s, precision) {
    var d = pdate(s); if (!d) return "—";
    if (precision === "quarter") return "Q" + (Math.floor(d.getMonth() / 3) + 1) + " " + d.getFullYear();
    if (precision === "half" || precision === "guided") return (d.getMonth() < 6 ? "H1 " : "H2 ") + d.getFullYear();
    if (precision === "year") return String(d.getFullYear());
    if (precision === "month" || /^\d{4}-\d{2}$/.test(String(s))) return MON[d.getMonth()] + " " + d.getFullYear();
    return MON[d.getMonth()] + " " + d.getDate() + ", " + d.getFullYear();
  }
  function daysFrom(s) { var d = pdate(s); return d ? Math.round((d - today()) / 864e5) : null; }
  function money(n, dp) {
    if (n == null || isNaN(n)) return "—";
    var a = Math.abs(n), sgn = n < 0 ? "−" : "";
    dp = dp == null ? 1 : dp;
    if (a >= 1e12) return sgn + "$" + (a / 1e12).toFixed(dp) + "T";
    if (a >= 1e9) return sgn + "$" + (a / 1e9).toFixed(dp) + "B";
    if (a >= 1e6) return sgn + "$" + (a / 1e6).toFixed(a >= 1e8 ? 0 : dp) + "M";
    if (a >= 1e3) return sgn + "$" + (a / 1e3).toFixed(0) + "K";
    return sgn + "$" + a.toFixed(0);
  }
  function pct(x, dp, signed) {
    if (x == null || isNaN(x)) return "—";
    var v = (x * 100).toFixed(dp == null ? 1 : dp);
    return (signed && x > 0 ? "+" : "") + v.replace("-", "−") + "%";
  }
  function retCell(x) { return '<td class="r num ' + (x == null ? "" : x >= 0 ? "pos" : "neg") + '">' + pct(x, 1, true) + "</td>"; }
  function gidx(g) { return GRADES.indexOf(g); }
  function byId(list) { var m = {}; (list || []).forEach(function (x) { m[x.id] = x; }); return m; }

  function ladder(stage, evidence) {
    var s = gidx(stage), e = gidx(evidence), h = '<div class="ladder" role="img" aria-label="Stage ' + esc(GRADE_LABEL[stage]) + ", evidence " + esc(GRADE_LABEL[evidence]) + '">';
    for (var i = 0; i < GRADES.length; i++) h += '<span class="step ' + (i <= e ? "ev" : i <= s ? "stage" : "") + '"></span>';
    return h + "</div>";
  }
  function ladderLabels() {
    return '<div class="ladder-labels" aria-hidden="true">' + GRADES.map(function (g) { return "<span>" + GRADE_LABEL[g].replace("Preclinical", "Preclin.") + "</span>"; }).join("") + "</div>";
  }
  function statusBadge(st) {
    var lbl = { active: "Active", paused: "Paused", discontinued: "Discontinued" }[st] || st;
    return '<span class="badge ' + esc(st) + '"><span class="dot"></span>' + esc(lbl) + "</span>";
  }
  function flagList(flags) {
    if (!flags || !flags.length) return "";
    var ic = { alert: "!", warn: "!", info: "i" };
    return '<div class="flags">' + flags.map(function (f) {
      return '<div class="flag ' + esc(f.level) + '"><span class="ic" aria-hidden="true">' + ic[f.level] + '</span><span><span class="sr">' + esc(f.level) + ": </span>" + esc(f.text) + "</span></div>";
    }).join("") + "</div>";
  }
  function sourcesList(srcs) {
    return '<ul class="src-list">' + (srcs || []).map(function (s) { return "<li>" + link(s.url, s.label) + "</li>"; }).join("") + "</ul>";
  }
  function trialStatus(st) {
    var c = { RECRUITING: "pos", ACTIVE_NOT_RECRUITING: "", NOT_YET_RECRUITING: "muted", TERMINATED: "neg", WITHDRAWN: "neg", SUSPENDED: "neg", COMPLETED: "ink2" }[st] || "";
    return '<span class="trial-status ' + c + '">' + esc(STATUS_LABEL[st] || st) + "</span>";
  }
  function trialsTable(trials) {
    if (!trials || !trials.length) return '<p class="small muted">No registry entry tracked.</p>';
    return '<div class="table-wrap"><table class="mini-table"><thead><tr><th>Trial</th><th>Status</th><th>Phase</th><th class="r">N</th><th>Primary completion</th></tr></thead><tbody>' +
      trials.map(function (t) {
        return "<tr><td>" + link(t.url, t.nct_id) + (t.acronym ? ' <span class="muted">' + esc(t.acronym) + "</span>" : "") +
          '<div class="xs muted">' + esc(t.sponsor || "") + "</div></td><td>" + trialStatus(t.status) +
          (t.why_stopped ? '<div class="xs muted">' + esc(t.why_stopped) + "</div>" : "") + "</td><td>" + esc((t.phases || []).join(" / ") || "—") +
          '</td><td class="r num">' + (t.enrollment != null ? esc(t.enrollment) + (t.enrollment_type === "ESTIMATED" ? '<span class="muted">e</span>' : "") : "—") +
          '</td><td class="num">' + esc(fdate(t.primary_completion)) + (t.primary_completion_type === "ESTIMATED" ? ' <span class="xs muted">est.</span>' : "") + "</td></tr>";
      }).join("") + "</tbody></table></div>";
  }
  function nextCatalyst(nc) {
    if (!nc) return '<div class="next muted">No dated catalyst</div>';
    var when = nc.date ? fdate(nc.date, nc.date_precision === "registry" ? null : nc.date_precision) : "Undated";
    var dd = daysFrom(nc.date);
    var tag = nc.date_precision === "guided" ? '<span class="xs muted">company guidance</span>' : nc.date_precision === "registry" ? '<span class="xs muted">registry estimate (' + esc(nc.nct_id) + ")</span>" : "";
    return '<div class="next"><span class="muted xs">NEXT</span><span class="when">' + esc(when) + "</span><span>" + esc(nc.label) + "</span>" + tag +
      (dd != null && dd >= 0 ? '<span class="xs muted">· in ' + dd + " days</span>" : dd != null ? '<span class="xs muted">· date passed</span>' : "") + "</div>";
  }
  function newsList(items) {
    if (!items || !items.length) return "";
    return '<details><summary>Recent headlines (' + items.length + ')</summary><ul class="src-list">' + items.map(function (n) {
      return "<li>" + link(n.url, n.title) + ' <span class="xs muted">' + esc(n.outlet || "") + (n.date ? " · " + esc(fdate(n.date)) : "") + "</span></li>";
    }).join("") + '</ul><p class="xs muted" style="margin-top:4px">Auto-collected headline links, not vetted. Read critically.</p></details>';
  }
  function mineBlock(text, label) {
    if (!text) return "";
    return '<div class="mine"><span class="k">' + esc(label || "My take · personal perspective") + "</span>" + esc(text) + "</div>";
  }
  function endpointsTable(eps) {
    if (!eps || !eps.length) return "";
    return '<table class="mini-table endpoints"><tbody>' + eps.map(function (e) { return "<tr><td>" + esc(e.metric) + "</td><td>" + esc(e.result) + "</td></tr>"; }).join("") + "</tbody></table>";
  }

  function programCard(p) {
    return '<article class="card prog" id="p-' + esc(p.id) + '">' +
      '<div class="prog-head"><div><h3>' + esc(p.name) + '</h3><div class="co">' + esc(p.company) + (p.ticker ? ' · <span class="tk">' + esc(p.ticker) + "</span>" : "") + "</div></div>" + statusBadge(p.status) + "</div>" +
      '<div class="modality">' + esc(p.modality || "") + "</div>" +
      "<div>" + ladder(p.stage, p.evidence) + ladderLabels() +
      '<div class="grade-line" style="margin-top:4px">Stage <b>' + esc(GRADE_LABEL[p.stage]) + "</b> · Evidence <b>" + esc(GRADE_LABEL[p.evidence]) + "</b></div></div>" +
      '<div class="reality"><span class="k">Reality check</span>' + esc(p.reality_check) + "</div>" +
      mineBlock(p.my_commentary, "My commentary · personal perspective") +
      endpointsTable(p.endpoints) +
      '<p class="small ink2" style="margin:0">' + esc(p.summary) + "</p>" +
      nextCatalyst(p.next_catalyst) +
      flagList(p.flags) +
      "<details><summary>Registry trials (" + (p.trials || []).length + ")</summary>" + trialsTable(p.trials) + "</details>" +
      "<details><summary>Sources (" + (p.sources || []).length + ')</summary>' + sourcesList(p.sources) + '<p class="xs muted">Verified ' + esc(fdate(p.verified_on)) + "</p></details>" +
      newsList(p.news) + "</article>";
  }

  function papersList(list, n) {
    if (!list || !list.length) return '<p class="small muted">No papers in the last 12 months matched.</p>';
    return '<ul class="feed">' + list.slice(0, n || 8).map(function (r) {
      var tags = (r.is_rct ? ' <span class="pill-type readout">RCT</span>' : "") + (r.is_review ? ' <span class="pill-type">Review</span>' : "");
      return '<li><span class="d">' + esc(fdate(r.sortdate)) + "</span><span>" + link(r.url, r.title) + tags + '<div class="xs muted">' + esc(r.authors) + " · <i>" + esc(r.journal) + "</i></div></span></li>";
    }).join("") + "</ul>";
  }

  // ------------------------------------------------------------ chart (line, crosshair tooltip)
  function lineChart(el, cfg) {
    var W = 720, H = 300, m = { t: 14, r: 16, b: 28, l: 56 };
    var xs = cfg.x, n = xs.length;
    var max = 0;
    cfg.series.forEach(function (s) { s.values.forEach(function (v) { if (v > max) max = v; }); });
    var stepV = niceStep((max || 1) / 4); max = stepV * 4;
    function X(i) { return m.l + (i / (n - 1)) * (W - m.l - m.r); }
    function Y(v) { return H - m.b - (v / max) * (H - m.t - m.b); }
    var svg = '<svg viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' + esc(cfg.label) + '">';
    for (var k = 0; k <= 4; k++) {
      var v = stepV * k, y = Y(v);
      svg += '<line class="' + (k === 0 ? "axisline" : "gridline") + '" x1="' + m.l + '" x2="' + (W - m.r) + '" y1="' + y + '" y2="' + y + '"/>';
      svg += '<text class="tick" x="' + (m.l - 8) + '" y="' + (y + 4) + '" text-anchor="end">' + esc(cfg.yFmt(v, false, true)) + "</text>";
    }
    var step = n > 12 ? 2 : 1;
    for (var i = 0; i < n; i += step) svg += '<text class="tick" x="' + X(i) + '" y="' + (H - 8) + '" text-anchor="middle">' + esc(xs[i]) + "</text>";
    cfg.series.forEach(function (s) {
      var d = s.values.map(function (v, i) { return (i ? "L" : "M") + X(i).toFixed(1) + " " + Y(v).toFixed(1); }).join(" ");
      svg += '<path d="' + d + '" fill="none" stroke="' + s.color + '" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
    });
    // direct labels at line ends (<= 4 series)
    var ends = cfg.series.map(function (s) { return { s: s, y: Y(s.values[n - 1]) }; }).sort(function (a, b) { return a.y - b.y; });
    for (var j = 1; j < ends.length; j++) if (ends[j].y - ends[j - 1].y < 13) ends[j].y = ends[j - 1].y + 13;
    svg += '<line class="xhair" x1="0" x2="0" y1="' + m.t + '" y2="' + (H - m.b) + '" stroke="var(--axis)" stroke-width="1" style="display:none"/>';
    svg += '<rect class="hit" x="' + m.l + '" y="' + m.t + '" width="' + (W - m.l - m.r) + '" height="' + (H - m.t - m.b) + '" fill="transparent" tabindex="0"/>';
    svg += "</svg>";
    el.innerHTML = '<div class="legend">' + cfg.series.map(function (s) { return '<span><i style="background:' + s.color + '"></i>' + esc(s.name) + "</span>"; }).join("") + "</div>" +
      '<div class="chart">' + svg + '<div class="tooltip"></div></div>';
    var root = el.querySelector(".chart"), svgEl = root.querySelector("svg"), tip = root.querySelector(".tooltip"), xh = svgEl.querySelector(".xhair"), hit = svgEl.querySelector(".hit");
    function show(i) {
      xh.setAttribute("x1", X(i)); xh.setAttribute("x2", X(i)); xh.style.display = "";
      tip.textContent = "";
      var h = document.createElement("div"); h.className = "tt-h"; h.textContent = cfg.tipTitle ? cfg.tipTitle(i) : xs[i]; tip.appendChild(h);
      cfg.series.forEach(function (s) {
        var r = document.createElement("div"); r.className = "tt-r";
        var l = document.createElement("span"); var key = document.createElement("i"); key.style.background = s.color; l.appendChild(key); l.appendChild(document.createTextNode(s.name));
        var b = document.createElement("b"); b.textContent = cfg.yFmt(s.values[i], true);
        r.appendChild(l); r.appendChild(b); tip.appendChild(r);
      });
      tip.style.display = "block";
      var bw = svgEl.getBoundingClientRect().width, px = (X(i) / W) * bw;
      tip.style.left = Math.min(Math.max(px + 12, 0), bw - tip.offsetWidth) + "px";
      tip.style.top = "30px";
    }
    function hide() { tip.style.display = "none"; xh.style.display = "none"; }
    function idxFromEvent(e) {
      var r = svgEl.getBoundingClientRect(), x = ((e.clientX - r.left) / r.width) * W;
      return Math.max(0, Math.min(n - 1, Math.round(((x - m.l) / (W - m.l - m.r)) * (n - 1))));
    }
    var cur = n - 1;
    hit.addEventListener("pointermove", function (e) { cur = idxFromEvent(e); show(cur); });
    hit.addEventListener("pointerleave", hide);
    hit.addEventListener("focus", function () { show(cur); });
    hit.addEventListener("blur", hide);
    hit.addEventListener("keydown", function (e) {
      if (e.key === "ArrowRight") { cur = Math.min(n - 1, cur + 1); show(cur); e.preventDefault(); }
      if (e.key === "ArrowLeft") { cur = Math.max(0, cur - 1); show(cur); e.preventDefault(); }
    });
  }
  function niceStep(v) {
    var p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * p;
  }
  function spark(values) {
    if (!values || values.length < 2) return "";
    var mn = Math.min.apply(null, values), mx = Math.max.apply(null, values), W = 90, H = 26;
    var d = values.map(function (v, i) { return (i ? "L" : "M") + ((i / (values.length - 1)) * W).toFixed(1) + " " + (H - 2 - ((v - mn) / ((mx - mn) || 1)) * (H - 4)).toFixed(1); }).join(" ");
    var up = values[values.length - 1] >= values[0];
    return '<svg class="spark" viewBox="0 0 90 26" aria-hidden="true"><path d="' + d + '" stroke="' + (up ? "var(--good-ink)" : "var(--bad-ink)") + '"/></svg>';
  }

  // ------------------------------------------------------------ views
  var views = {};

  views[""] = function () {
    var progs = D.programs.programs, cure = progs.filter(function (p) { return p.section === "cure"; });
    var active = progs.filter(function (p) { return p.status === "active"; });
    var late = active.filter(function (p) { return gidx(p.stage) >= gidx("phase3"); });
    var lateEv = active.filter(function (p) { return gidx(p.evidence) >= gidx("phase3"); });
    var approved = active.filter(function (p) { return p.stage === "approved"; });
    var upcoming = D.catalysts.catalysts.filter(function (c) { var d = daysFrom(c.date); return d != null && d >= 0; });
    var flags = progs.reduce(function (a, p) { return a + p.flags.filter(function (f) { return f.level !== "info"; }).length; }, 0);
    var h = '<div class="page-head"><div class="eyebrow">Type 1 diabetes · cure, medtech & GLP-1 tracker</div><h1>Separating clinical progress from hype</h1>' +
      '<p class="lede">Each program is a tracked record with two grades: how far it has <b>advanced</b>, and how far its <b>evidence</b> has actually read out. The gap between those two grades is where hype lives. The data refreshes daily from ClinicalTrials.gov, PubMed, openFDA, SEC EDGAR and market data, and every record cites its sources.</p></div>';
    h += '<div class="kpis">' +
      kpi(active.length, "Active programs tracked", (progs.length - active.length) + " discontinued kept on record") +
      kpi(late.length, "At Phase 3 or beyond", "only " + lateEv.length + " have Phase 3+ data read out") +
      kpi(approved.length, "Approved therapies", approved.map(function (p) { return p.name.split(" (")[0]; }).join(", ")) +
      kpi(D.glp1.any_t1d_label ? "Yes" : "None", "GLP-1s FDA-labeled for T1D", "openFDA label check, live") +
      kpi(flags, "Open verification flags", "registry conflicts, stale or unverified items") +
      "</div>";
    // hype map
    var order = cure.slice().sort(function (a, b) { return (a.status === "discontinued") - (b.status === "discontinued") || gidx(b.stage) - gidx(a.stage) || gidx(b.evidence) - gidx(a.evidence); });
    h += '<div class="grid" style="grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:14px" id="ov-grid"><section class="card"><h3>Hype map: stage vs. evidence</h3>' +
      '<p class="small ink2">Outlined = how far it has advanced. Filled = the evidence actually in hand. Struck-through programs have been discontinued.</p>' +
      '<div class="ladder-key"><span><i class="ev"></i>Evidence read out</span><span><i class="stage"></i>Stage reached, not yet proven</span></div>' +
      '<div class="hype-axis" style="margin-top:10px"><span></span><div class="ticks">' + GRADES.map(function (g) { return "<span>" + GRADE_LABEL[g].replace("Preclinical", "Preclin.") + "</span>"; }).join("") + "</div></div>" +
      order.map(function (p) {
        return '<div class="hype-row"><div class="hype-name"><a href="#/pipeline?p=' + esc(p.id) + '" class="' + (p.status === "discontinued" ? "disc" : "") + '">' + esc(p.name.split(" (")[0]) + '</a> <span class="xs muted">' + esc(p.ticker || "") + "</span></div>" + ladder(p.stage, p.evidence) + "</div>";
      }).join("") + "</section>";
    h += '<div style="display:flex;flex-direction:column;gap:14px"><section class="card"><h3>Next catalysts</h3><ul class="feed">' +
      upcoming.slice(0, 7).map(function (c) {
        return '<li><span class="d">' + esc(fdate(c.date, c.precision)) + '</span><span><span class="pill-type ' + esc(c.type) + '">' + esc(CAT_TYPE[c.type] || c.type) + "</span> " + esc(c.title) + "</span></li>";
      }).join("") + '</ul><p class="small" style="margin:8px 0 0"><a href="#/catalysts">Full calendar →</a></p></section>';
    var ch = (D.changes.changes || []).slice(0, 6);
    h += '<section class="card"><h3>What changed in the registry</h3>' + (ch.length ? '<ul class="feed">' + ch.map(changeItem).join("") + "</ul>" :
      '<p class="small muted">Status changes and date slips on tracked trials will appear here as the daily refresh detects them.</p>') + "</section></div></div>";
    // approach summary
    h += '<h2>By approach</h2><div class="grid g2">' + Object.keys(APPROACH).map(function (k) {
      var ps = cure.filter(function (p) { return p.approach === k; }), act = ps.filter(function (p) { return p.status === "active"; });
      var best = act.slice().sort(function (a, b) { return gidx(b.evidence) - gidx(a.evidence); })[0];
      return '<a class="card" href="#/pipeline?a=' + k + '" style="color:inherit;text-decoration:none"><div class="eyebrow">' + act.length + " active · " + (ps.length - act.length) + " stopped</div><h3>" + esc(APPROACH[k].label) +
        '</h3><p class="small ink2">' + esc(APPROACH[k].blurb) + "</p>" + (best ? '<div class="small">Best evidence: <b>' + esc(best.name.split(" (")[0]) + "</b> (" + esc(GRADE_LABEL[best.evidence]) + ")</div>" : "") + "</a>";
    }).join("") + "</div>";
    return h;
  };
  function kpi(v, l, d) { return '<div class="card kpi"><div class="v">' + esc(v) + '</div><div class="l">' + esc(l) + '</div><div class="d">' + esc(d) + "</div></div>"; }
  function changeItem(c) {
    var t = c.kind === "status" ? "Status: " + (STATUS_LABEL[c.from] || c.from) + " → " + (STATUS_LABEL[c.to] || c.to)
      : "Primary completion: " + fdate(c.from) + " → " + fdate(c.to) + (c.slip_days ? " (" + (c.slip_days > 0 ? "+" : "") + c.slip_days + " days)" : "");
    return '<li><span class="d">' + esc(fdate(c.date)) + "</span><span>" + link("https://clinicaltrials.gov/study/" + c.nct_id, c.nct_id) + " · " + esc(t) + '<div class="xs muted">' + esc(c.title || "") + "</div></span></li>";
  }

  views.pipeline = function (q) {
    if (q.a) state.pipeFilter = q.a;
    var cure = D.programs.programs.filter(function (p) { return p.section === "cure"; });
    var h = '<div class="page-head"><div class="eyebrow">Section 1</div><h1>Cure pipeline</h1><p class="lede">Programs aiming to restore insulin production or stop the autoimmune attack, grouped by approach. "Stage" is where development stands. "Evidence" is what the data has actually shown so far.</p></div>';
    h += '<div class="controls" role="toolbar">' + chip("all", "All approaches", state.pipeFilter, "pf") +
      Object.keys(APPROACH).map(function (k) { return chip(k, APPROACH[k].label, state.pipeFilter, "pf"); }).join("") +
      '<span class="sep"></span>' + chip("active", "Active only", state.pipeStatus, "ps") + chip("all", "Include discontinued", state.pipeStatus, "ps") + "</div>";
    h += '<div class="ladder-key" style="margin-bottom:6px"><span><i class="ev"></i>Evidence read out</span><span><i class="stage"></i>Stage reached</span></div>';
    Object.keys(APPROACH).forEach(function (k) {
      if (state.pipeFilter !== "all" && state.pipeFilter !== k) return;
      var ps = cure.filter(function (p) { return p.approach === k && (state.pipeStatus === "all" || p.status !== "discontinued"); })
        .sort(function (a, b) { return gidx(b.stage) - gidx(a.stage) || gidx(b.evidence) - gidx(a.evidence); });
      h += '<div class="approach-head"><h2>' + esc(APPROACH[k].label) + "</h2><p>" + esc(APPROACH[k].blurb) + "</p></div>";
      h += ps.length ? '<div class="grid g2">' + ps.map(programCard).join("") + "</div>" : '<div class="empty">Nothing matches this filter.</div>';
    });
    h += '<h2>Recent literature</h2><p class="small ink2">The most recent PubMed citations for each approach, refreshed daily (titles and links only).</p><div class="grid g2">' +
      Object.keys(APPROACH).map(function (k) { return '<section class="card"><h3>' + esc(APPROACH[k].label) + "</h3>" + papersList((D.programs.papers || {})[k], 5) + "</section>"; }).join("") + "</div>";
    return h;
  };
  function chip(val, label, cur, group) {
    return '<button type="button" class="chip' + (val === cur ? " on" : "") + '" data-g="' + group + '" data-v="' + esc(val) + '">' + esc(label) + "</button>";
  }

  views.medtech = function () {
    var devs = D.devices.devices;
    var h = '<div class="page-head"><div class="eyebrow">Section 2</div><h1>Medtech: CGMs, pumps & automated insulin delivery</h1><p class="lede">The products people with T1D actually use today, and what\'s coming next. FDA numbers are checked against openFDA, and the decision feed below updates every day.</p></div>';
    ["cgm", "pump", "other"].forEach(function (cat) {
      var list = devs.filter(function (d) { return d.category === cat; });
      if (!list.length) return;
      h += '<div class="approach-head"><h2>' + esc(DEVICE_CAT[cat]) + "</h2></div><div class='grid g2'>" + list.map(deviceCard).join("") + "</div>";
    });
    var feed = D.devices.fda_feed || [], codes = {};
    feed.forEach(function (f) { codes[f.product_code] = f.code_label || f.product_code; });
    var shown = feed.filter(function (f) { return state.fdaCode === "all" || f.product_code === state.fdaCode; });
    h += '<h2>FDA device decisions: live feed</h2><p class="small ink2">Every 510(k), De Novo and PMA decision in the diabetes-device product codes over the past 24 months (manufacturing-only PMA supplements are excluded). Source: openFDA.</p>';
    h += '<div class="controls">' + chip("all", "All codes", state.fdaCode, "fc") + Object.keys(codes).sort().map(function (c) { return chip(c, c + " · " + codes[c], state.fdaCode, "fc"); }).join("") + "</div>";
    h += '<div class="table-wrap"><table><thead><tr><th>Date</th><th>Device</th><th>Applicant</th><th>Type</th><th>Number</th></tr></thead><tbody>' +
      shown.map(function (f) {
        return '<tr><td class="num" style="white-space:nowrap">' + esc(fdate(f.date)) + "</td><td>" + esc(f.device) + '<div class="xs muted">' + esc(f.code_label || "") + "</div></td><td>" + esc(f.applicant) + "</td><td>" + esc(f.kind) + "</td><td>" + link(f.url, f.number) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    return h;
  };
  function deviceCard(d) {
    var rating = d.my_rating ? " · " + "★★★★★".slice(0, d.my_rating) + "☆☆☆☆☆".slice(0, 5 - d.my_rating) : "";
    return '<article class="card prog"><div class="prog-head"><div><h3>' + esc(d.name) + '</h3><div class="co">' + esc(d.company) + (d.ticker ? ' · <span class="tk">' + esc(d.ticker) + "</span>" : "") + "</div></div>" +
      '<span class="badge">' + esc(DEVICE_STATUS[d.status] || d.status) + "</span></div>" +
      '<div class="small">' + esc(d.key_specs || "") + "</div>" +
      '<div class="small ink2"><b>FDA:</b> ' + esc(d.fda || "—") + "</div>" +
      (d.pipeline_note ? '<div class="reality"><span class="k">Why it matters</span>' + esc(d.pipeline_note) + "</div>" : "") +
      (d.my_take ? mineBlock(d.my_take + rating, "User's take · personal perspective") :
        '<div class="mine" style="opacity:.75"><span class="k">User\'s take · personal perspective</span><span class="muted small">Not written yet.</span></div>') +
      flagList((d.unverified || []).map(function (u) { return { level: "info", text: "Unverified: " + u }; })) +
      "<details><summary>Sources (" + (d.sources || []).length + ")</summary>" + sourcesList(d.sources) + "</details></article>";
  }

  views.glp1 = function () {
    var progs = D.programs.programs.filter(function (p) { return p.section === "glp1"; });
    var labels = D.glp1.labels || [];
    var h = '<div class="page-head"><div class="eyebrow">Section 3</div><h1>GLP-1s in type 1 diabetes</h1><p class="lede">GLP-1 and dual agonists are widely used off-label by people with T1D for weight and smoother glucose. This section tracks whether that is turning into evidence and an FDA label, and what it would be worth.</p></div>';
    h += '<div class="banner ' + (D.glp1.any_t1d_label ? "go" : "neutral") + '"><div><div class="big">' + (D.glp1.any_t1d_label ? "A GLP-1-class label now mentions type 1 diabetes. Review below." : "No GLP-1 or dual agonist is FDA-approved for type 1 diabetes.") + "</div>" +
      '<div class="small ink2">The pipeline checks the current FDA label of each drug below every day (openFDA). If any indication starts to include T1D, this banner flips automatically.</div></div></div>';
    h += '<div class="table-wrap" style="margin-top:12px"><table><thead><tr><th>Brand</th><th>Molecule</th><th>Labeled indications cover</th><th>T1D wording on label</th><th>Label date</th></tr></thead><tbody>' +
      labels.map(function (l) {
        return "<tr><td>" + link(l.url, l.brand) + "</td><td>" + esc(l.generic || "—") + "</td><td>" + esc(l.indication_scope || "—") + '</td><td class="small">' + esc(l.t1d_statement || "No T1D indication") + '</td><td class="num">' + esc(fdate(l.effective)) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    ["adjunct", "beta_cell", "safety"].forEach(function (t) {
      var ps = progs.filter(function (p) { return p.glp1_topic === t; });
      h += '<div class="approach-head"><h2>' + esc(GLP_TOPIC[t]) + "</h2>" + (t === "safety" ? "<p>T1D-specific risks: hypoglycemia as insulin needs fall, and ketosis/DKA if insulin is cut too far. Novo's liraglutide program stalled on exactly these.</p>" : "") + "</div>";
      if (ps.length) h += '<div class="grid g2">' + ps.map(programCard).join("") + "</div>";
      h += '<div class="card" style="margin-top:12px"><h3>Latest PubMed: ' + esc(GLP_TOPIC[t].toLowerCase()) + "</h3>" + papersList((D.glp1.papers || {})[t], 6) + "</div>";
    });
    var scan = (D.glp1.registry_scan || []).slice().sort(function (a, b) { return (b.sponsor_class === "INDUSTRY") - (a.sponsor_class === "INDUSTRY") || String(a.primary_completion || "9").localeCompare(String(b.primary_completion || "9")); });
    h += '<h2>Registry scan: every GLP-1-class trial in T1D</h2><p class="small ink2">This is an automatic ClinicalTrials.gov search (active, or completed in the last 2 years), so it surfaces new trials before they are curated above. Industry-sponsored trials are listed first, because only those can lead to a label.</p>';
    h += '<div class="table-wrap"><table><thead><tr><th>Trial</th><th>Sponsor</th><th>Phase</th><th>Status</th><th class="r">N</th><th>Primary completion</th></tr></thead><tbody>' +
      scan.map(function (t) {
        return "<tr><td>" + link(t.url, t.nct_id) + (t.tracked ? ' <span class="badge">tracked</span>' : "") + '<div class="xs">' + esc(t.title) + "</div></td><td class='small'>" + esc(t.sponsor) + (t.sponsor_class === "INDUSTRY" ? ' <span class="tag-src">industry</span>' : "") +
          "</td><td>" + esc((t.phases || []).join("/") || "—") + "</td><td>" + trialStatus(t.status) + '</td><td class="r num">' + esc(t.enrollment == null ? "—" : t.enrollment) + '</td><td class="num">' + esc(fdate(t.primary_completion)) + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    h += '<h2>Market angle: what a T1D label would be worth</h2><div class="card" id="glp-model"></div>';
    return h;
  };

  function glpModel() {
    var el = document.getElementById("glp-model"); if (!el) return;
    var pop = D.market.population, comps = byTicker();
    var lly = (comps.LLY || {}).quote || {}, nvo = (comps.NVO || {}).quote || {};
    var inputs = [
      { id: "pop", label: "US people with T1D", min: 1, max: 2, step: 0.1, val: pop.t1d_us_m, fmt: function (v) { return v.toFixed(1) + "M"; }, src: true, hint: pop.source_label },
      { id: "adult", label: "Adults with overweight/obesity (share)", min: 0.2, max: 0.8, step: 0.05, val: 0.5, fmt: function (v) { return pct(v, 0); }, hint: "Assumption: published estimates vary by cohort." },
      { id: "uptake", label: "Peak uptake among eligible", min: 0.05, max: 0.6, step: 0.05, val: 0.25, fmt: function (v) { return pct(v, 0); }, hint: "Assumption: on-label adoption at peak." },
      { id: "price", label: "Net price per patient-year", min: 2000, max: 12000, step: 500, val: 6000, fmt: function (v) { return money(v); }, hint: "Assumption: US net, after rebates." },
      { id: "share", label: "Lilly share of T1D GLP-1 use", min: 0, max: 1, step: 0.05, val: 0.6, fmt: function (v) { return pct(v, 0); }, hint: "Assumption: first label likely tirzepatide (only industry Phase 3)." }
    ];
    el.innerHTML = '<p class="small ink2">This is a US-only, back-of-the-envelope estimate of peak annual sales from a T1D label. It sits alongside live trailing revenue so you can see the scale. Inputs tagged <span class="tag-assume">assumption</span> are judgment calls, not sourced facts.</p><div class="model" style="grid-template-columns:300px 1fr">' +
      '<div class="inputs" style="position:static">' + inputs.map(sliderHtml).join("") + '</div><div id="glp-out"></div></div>';
    function calc() {
      var v = readInputs(inputs);
      var patients = v.pop * 1e6 * v.adult * v.uptake, rev = patients * v.price;
      var lr = lly.revenue_ttm_usd, nr = nvo.revenue_ttm_usd;
      document.getElementById("glp-out").innerHTML = '<div class="kpis" style="margin-top:0">' +
        kpi(Math.round(patients / 1000) + "K", "US patients on therapy at peak", "pop × overweight share × uptake") +
        kpi(money(rev), "Peak US annual sales (class)", "patients × net price") +
        kpi(money(rev * v.share), "Lilly share", lr ? pct(rev * v.share / lr, 1) + " of Lilly TTM revenue (" + money(lr) + ")" : "Lilly TTM revenue unavailable") +
        kpi(money(rev * (1 - v.share)), "Novo share", nr ? pct(rev * (1 - v.share) / nr, 1) + " of Novo TTM revenue (" + money(nr) + ")" : "Novo TTM revenue unavailable") + "</div>" +
        '<p class="small ink2"><b>So what:</b> even an optimistic T1D label is a low-single-digit-percent revenue event for Lilly or Novo. The bigger strategic value is defensive. A label converts existing off-label use into reimbursed, guideline-backed use, and the safety data (DKA, hypoglycemia) shapes how both companies talk about combining incretins with insulin. For CGM makers, GLP-1 use in T1D is if anything a tailwind: tighter dose titration raises the value of continuous monitoring and ketone sensing.</p>';
    }
    bindInputs(el, inputs, calc); calc();
  }

  views.catalysts = function () {
    var cats = D.catalysts.catalysts.filter(function (c) {
      var d = daysFrom(c.date);
      return (state.catType === "all" || c.type === state.catType) && (state.catPast || d == null || d >= -1);
    }).sort(function (a, b) { return state.catSort * String(a.date).localeCompare(String(b.date)); });
    var types = {}; D.catalysts.catalysts.forEach(function (c) { types[c.type] = 1; });
    var h = '<div class="page-head"><div class="eyebrow">Section 4</div><h1>Catalyst calendar</h1><p class="lede">Trial readouts, FDA actions, launches, earnings, and the ADA / EASD / ATTD meetings where data is usually presented first. Each date carries its precision: an exact date is not the same thing as company guidance or a registry estimate.</p></div>';
    h += '<div class="controls">' + chip("all", "All", state.catType, "ct") + Object.keys(types).sort().map(function (t) { return chip(t, CAT_TYPE[t] || t, state.catType, "ct"); }).join("") +
      '<span class="sep"></span><label class="small" style="display:flex;gap:6px;align-items:center"><input type="checkbox" id="catpast"' + (state.catPast ? " checked" : "") + "> Show past</label></div>";
    h += '<div class="table-wrap"><table><thead><tr><th class="sortable" id="catsort">Date <span class="arr">' + (state.catSort > 0 ? "▲" : "▼") + '</span></th><th>Type</th><th>Event</th><th>Date basis</th><th>Source</th></tr></thead><tbody>' +
      (cats.length ? cats.map(function (c) {
        var d = daysFrom(c.date), prec = c.precision || "exact";
        var basis = /^registry/.test(prec) ? "Registry " + (prec.indexOf("actual") > 0 ? "(actual)" : "estimate") : prec === "guided" || prec === "half" || prec === "quarter" ? "Company guidance" : c.origin === "yfinance" ? "Market calendar" : "Scheduled";
        return '<tr class="' + (d != null && d < 0 ? "row-past" : "") + '"><td class="num" style="white-space:nowrap">' + esc(fdate(c.date, /^registry/.test(prec) ? null : prec)) +
          (c.end ? "–" + esc(fdate(c.end).replace(/, \d{4}$/, "")) : "") + (d != null && d >= 0 ? '<div class="xs muted">in ' + d + " d</div>" : "") +
          '</td><td><span class="pill-type ' + esc(c.type) + '">' + esc(CAT_TYPE[c.type] || c.type) + "</span></td><td>" + (c.related ? '<a href="#/' + (isGlp(c.related) ? "glp1" : isDevice(c.related) ? "medtech" : "pipeline") + '">' + esc(c.title) + "</a>" : esc(c.title)) +
          (c.note ? '<div class="xs muted">' + esc(c.note) + "</div>" : "") + '</td><td class="small">' + esc(basis) + "</td><td>" + (c.source ? link(c.source, "Source") : "—") + "</td></tr>";
      }).join("") : '<tr><td colspan="5" class="empty">No events match.</td></tr>') + "</tbody></table></div>";
    h += '<p class="xs muted" style="margin-top:8px">A registry "primary completion" date is when the last participant reaches the primary endpoint. Topline results usually follow 1–6 months later, and sponsors often update these dates. Slips are logged on the Overview page.</p>';
    return h;
  };
  function isGlp(id) { return D.programs.programs.some(function (p) { return p.id === id && p.section === "glp1"; }); }
  function isDevice(id) { return D.devices.devices.some(function (d) { return d.id === id; }); }
  function byTicker() { var m = {}; D.companies.companies.forEach(function (c) { m[c.ticker] = c; }); return m; }

  views.companies = function () {
    var GROUP = { cgm_pump: "Devices", pharma: "Pharma", cell_gene: "Cell & gene", immune: "Immunology" };
    var rows = D.companies.companies.map(function (c) { var q = c.quote || {}; return Object.assign({}, c, q, { quote: q }); });
    var k = state.compSort.k, dir = state.compSort.d;
    rows.sort(function (a, b) { var x = a[k], y = b[k]; if (x == null) return 1; if (y == null) return -1; return (typeof x === "string" ? x.localeCompare(y) : x - y) * dir; });
    var groups = {};
    rows.forEach(function (r) { var g = groups[r.group] = groups[r.group] || { mc: 0, n: 0, ret: [] }; if (r.market_cap_usd) g.mc += r.market_cap_usd; g.n++; if (r.ret_1y != null) g.ret.push(r.ret_1y); });
    var asOf = rows.map(function (r) { return r.as_of; }).filter(Boolean).sort().pop();
    var h = '<div class="page-head"><div class="eyebrow">Section 5</div><h1>Company exposure</h1><p class="lede">Public companies with real exposure to T1D, refreshed daily. The diabetes revenue share is shown only where a filing discloses it or it can be derived; otherwise it reads "not disclosed".</p></div>';
    h += '<div class="kpis">' + Object.keys(GROUP).filter(function (g) { return groups[g]; }).map(function (g) {
      var med = groups[g].ret.slice().sort(function (a, b) { return a - b; })[Math.floor(groups[g].ret.length / 2)];
      return kpi(money(groups[g].mc, 0), GROUP[g] + " · " + groups[g].n + " companies", "median 1-yr return " + pct(med, 0, true));
    }).join("") + "</div>";
    function th(key, label, r) { return '<th class="sortable' + (r ? " r" : "") + '" data-sort="' + key + '">' + label + (k === key ? ' <span class="arr">' + (dir > 0 ? "▲" : "▼") + "</span>" : "") + "</th>"; }
    h += '<div class="table-wrap"><table><thead><tr>' + th("ticker", "Ticker") + th("name", "Company") + th("price", "Price", 1) + th("market_cap_usd", "Mkt cap (USD)", 1) +
      th("ret_1m", "1M", 1) + th("ret_ytd", "YTD", 1) + th("ret_1y", "1Y", 1) + "<th>1Y trend</th>" + th("revenue_ttm_usd", "Revenue TTM", 1) + th("diabetes_rev_pct", "Diabetes % rev", 1) + th("next_earnings", "Next earnings") + "<th>Latest filing</th></tr></thead><tbody>" +
      rows.map(function (r) {
        var f = (r.filings || [])[0];
        return '<tr><td><b>' + esc(r.ticker) + '</b><div class="xs muted">' + esc(GROUP[r.group] || "") + "</div></td><td>" + esc(r.name) + '</td><td class="r num">' + (r.price != null ? esc((r.currency && r.currency !== "USD" ? r.currency + " " : "$") + r.price.toFixed(2)) : "—") +
          '</td><td class="r num">' + money(r.market_cap_usd) + "</td>" + retCell(r.ret_1m) + retCell(r.ret_ytd) + retCell(r.ret_1y) + "<td>" + spark(r.spark) + '</td><td class="r num">' + money(r.revenue_ttm_usd) +
          '</td><td class="r num">' + (r.diabetes_rev_pct != null ? link(r.pct_source, r.diabetes_rev_pct + "%") : '<span class="muted">not disclosed</span>') + '<div class="xs muted" style="min-width:150px;max-width:200px;margin-left:auto">' + esc(r.pct_note || "") + "</div>" +
          '</td><td class="num small">' + esc(r.next_earnings ? fdate(r.next_earnings) : "—") + '</td><td class="small">' + (f ? link(f.url, f.form) + ' <span class="muted">' + esc(fdate(f.date)) + "</span>" : '<span class="muted">non-SEC filer</span>') + "</td></tr>";
      }).join("") + "</tbody></table></div>";
    h += '<p class="xs muted" style="margin-top:8px">Prices and returns come from Yahoo Finance via yfinance (unofficial and possibly delayed), as of ' + esc(fdate(asOf)) + '. Non-USD market caps are converted at the live FX rate. Returns are price returns, dividend-adjusted. Filings come from SEC EDGAR.</p>';
    return h;
  };

  // ------------------------------------------------------------ cure impact model
  var PRESETS = {
    base: { label: "Base: immune-evasive cells work", approval: 2031, peak: 0.15, ramp: 12, price: 500000, cap: 40000, residual: 0.3 },
    bull: { label: "Bull: fast, broad adoption", approval: 2029, peak: 0.35, ramp: 9, price: 400000, cap: 150000, residual: 0.15 },
    immuno: { label: "Narrow: needs immunosuppression", approval: 2028, peak: 0.02, ramp: 8, price: 1000000, cap: 5000, residual: 0.6 },
    bear: { label: "Bear: late and niche", approval: 2034, peak: 0.05, ramp: 14, price: 750000, cap: 15000, residual: 0.5 }
  };
  views.analysis = function () {
    var M = D.market;
    var h = '<div class="page-head"><div class="eyebrow">Section 6 · analysis</div><h1>What if a functional cure works?</h1><p class="lede">This model estimates how much T1D-driven revenue in the CGM, pump and insulin markets a one-time functional cure would displace, and how large the cure itself could be. Market sizes are cited. Everything tagged <span class="tag-assume">assumption</span> is a judgment call you can move.</p></div>';
    h += '<div class="controls">' + Object.keys(PRESETS).map(function (k) { return '<button type="button" class="chip" data-preset="' + k + '">' + esc(PRESETS[k].label) + "</button>"; }).join("") + "</div>";
    h += '<div class="model"><div class="card inputs" id="model-inputs"></div><div><div id="model-kpis"></div><div class="card"><h3>T1D-attributable revenue displaced by the cure</h3><p class="small ink2">This is annual revenue that would have existed in the no-cure baseline. Hover or use the arrow keys for each year.</p><div id="model-chart"></div></div>' +
      '<div class="card" style="margin-top:14px"><h3>Year-by-year</h3><div id="model-table"></div></div>' +
      '<div class="card" style="margin-top:14px"><h3>Sources & assumptions</h3>' + assumptionsTable(M) + "</div></div></div>";
    return h;
  };
  function assumptionsTable(M) {
    var rows = Object.keys(M.markets).map(function (k) {
      var m = M.markets[k];
      return "<tr><td>" + esc(m.label) + '</td><td class="num">$' + m.value + "B (range $" + m.low + "–" + m.high + 'B)</td><td class="num">' + pct(m.cagr, 1) + (m.cagr_note ? ' <span class="tag-assume">assumption</span>' : "") + "</td><td>" + link(m.source, m.source_label) + (m.cross_check ? '<div class="xs muted">' + esc(m.cross_check) + "</div>" : "") + (m.cagr_note ? '<div class="xs muted">' + esc(m.cagr_note) + "</div>" : "") + "</td></tr>";
    });
    rows.push("<tr><td>People with T1D</td><td class='num'>" + M.population.t1d_global_m + "M global · " + M.population.t1d_us_m + "M US</td><td>—</td><td>" + link(M.population.source, M.population.source_label) + "</td></tr>");
    Object.keys(M.assumptions).forEach(function (k) {
      var a = M.assumptions[k];
      rows.push("<tr><td>" + esc(k.replace(/_/g, " ")) + ' <span class="tag-assume">assumption</span></td><td class="num">' + esc(a.value > 1 ? a.value.toLocaleString() : pct(a.value, 0)) + "</td><td>—</td><td class='small'>" + esc(a.note) + (a.source ? " " + link(a.source, "source") : "") + "</td></tr>");
    });
    return '<div class="table-wrap"><table class="mini-table"><thead><tr><th>Input</th><th>Value</th><th>Growth</th><th>Source / note</th></tr></thead><tbody>' + rows.join("") + "</tbody></table></div>" +
      '<p class="xs muted" style="margin-top:8px"><b>Mechanics:</b> baseline market(y) = 2025 size × (1+CAGR)^(y−2025). Demand(y) = peak share of the global T1D population × a smooth S-curve that starts at approval and reaches peak after the ramp. Patients actually treated each year are capped by treatment capacity, and penetration = cumulative treated ÷ T1D population. Displaced CGM = baseline × T1D share × penetration × (1 − residual CGM use). Displaced pumps and insulin = baseline × T1D share × penetration. Cure revenue = newly treated patients × one-time price. The model ignores new-onset incidence, geographic price tiers, and payer budget caps, so read it as an order of magnitude, not a forecast.</p>';
  }
  function sliderHtml(i) {
    return '<div class="inp"><label for="in-' + i.id + '"><span>' + esc(i.label) + (i.src ? ' <span class="tag-src">sourced</span>' : ' <span class="tag-assume">assumption</span>') + '</span><output id="out-' + i.id + '"></output></label>' +
      '<input type="range" id="in-' + i.id + '" min="' + i.min + '" max="' + i.max + '" step="' + i.step + '" value="' + i.val + '">' + (i.hint ? '<div class="hint">' + esc(i.hint) + "</div>" : "") + "</div>";
  }
  function readInputs(inputs) {
    var v = {};
    inputs.forEach(function (i) { var el = document.getElementById("in-" + i.id); v[i.id] = el ? parseFloat(el.value) : i.val; var o = document.getElementById("out-" + i.id); if (o) o.textContent = i.fmt(v[i.id]); });
    return v;
  }
  function bindInputs(root, inputs, fn) { root.addEventListener("input", function (e) { if (e.target.type === "range" || e.target.tagName === "SELECT") fn(); }); }

  function cureModel() {
    var M = D.market, A = M.assumptions, mk = M.markets;
    var inputs = [
      { group: "Cure scenario", id: "approval", label: "First broad approval year", min: 2027, max: 2038, step: 1, val: 2031, fmt: String, hint: "Zimislecel filing timeline is being reset; SC451 has no human data yet." },
      { id: "peak", label: "Peak share of all T1D patients cured", min: 0.01, max: 0.6, step: 0.01, val: 0.15, fmt: function (v) { return pct(v, 0); }, hint: "Constrained by manufacturing, surgical capacity, eligibility, and patient willingness." },
      { id: "ramp", label: "Years from approval to peak", min: 4, max: 20, step: 1, val: 12, fmt: function (v) { return v + " yrs"; } },
      { id: "cap", label: "Treatment capacity (patients / year)", min: 1000, max: 300000, step: 1000, val: 40000, fmt: function (v) { return Math.round(v / 1000) + "K"; }, hint: "Cell manufacturing + transplant-center throughput. Usually the binding constraint early on." },
      { id: "price", label: "Blended one-time price per patient", min: 100000, max: 3000000, step: 50000, val: 500000, fmt: function (v) { return money(v, 2); }, hint: "One-time US gene therapies list at roughly $2–4M. A global blended price, with ex-US discounts, would be far lower." },
      { group: "Market exposure", id: "sh_cgm", label: "T1D share of CGM revenue", min: 0.1, max: 0.8, step: 0.05, val: A.t1d_share_cgm.value, fmt: function (v) { return pct(v, 0); }, hint: A.t1d_share_cgm.note },
      { id: "sh_pump", label: "T1D share of pump revenue", min: 0.5, max: 1, step: 0.05, val: A.t1d_share_pump.value, fmt: function (v) { return pct(v, 0); }, hint: A.t1d_share_pump.note },
      { id: "sh_ins", label: "T1D share of insulin revenue", min: 0.05, max: 0.5, step: 0.05, val: A.t1d_share_insulin.value, fmt: function (v) { return pct(v, 0); }, hint: A.t1d_share_insulin.note },
      { id: "residual", label: "Cured patients still using CGM", min: 0, max: 1, step: 0.05, val: A.residual_cgm_use.value, fmt: function (v) { return pct(v, 0); }, hint: A.residual_cgm_use.note },
      { group: "Market growth", id: "g_cgm", label: "CGM market CAGR", min: 0, max: 0.2, step: 0.01, val: mk.cgm.cagr, fmt: function (v) { return pct(v, 0); }, src: true, hint: mk.cgm.source_label },
      { id: "g_pump", label: "Pump market CAGR", min: 0, max: 0.2, step: 0.01, val: mk.pump.cagr, fmt: function (v) { return pct(v, 1); }, src: true, hint: mk.pump.source_label },
      { id: "g_ins", label: "Insulin market CAGR", min: -0.05, max: 0.08, step: 0.01, val: mk.insulin.cagr, fmt: function (v) { return pct(v, 0); } }
    ];
    var box = document.getElementById("model-inputs");
    var html = '<div class="inp"><label for="in-size"><span>2025 market sizes <span class="tag-src">sourced</span></span></label><select id="in-size" style="width:100%"><option value="value">Base estimates</option><option value="low">Low end of range</option><option value="high">High end of range</option></select></div>';
    var last = null;
    inputs.forEach(function (i) {
      if (i.group && i.group !== last) { html += (last ? "</div>" : "") + '<div class="inp-group"><div class="eyebrow">' + esc(i.group) + "</div>"; last = i.group; }
      html += sliderHtml(i);
    });
    box.innerHTML = html + "</div>";
    function setPreset(k) {
      var p = PRESETS[k];
      [["approval", p.approval], ["peak", p.peak], ["ramp", p.ramp], ["price", p.price], ["cap", p.cap], ["residual", p.residual]].forEach(function (x) { document.getElementById("in-" + x[0]).value = x[1]; });
      document.querySelectorAll("[data-preset]").forEach(function (b) { b.classList.toggle("on", b.getAttribute("data-preset") === k); });
      calc();
    }
    document.querySelectorAll("[data-preset]").forEach(function (b) { b.addEventListener("click", function () { setPreset(b.getAttribute("data-preset")); }); });
    function smooth(t) { t = Math.max(0, Math.min(1, t)); return t * t * (3 - 2 * t); }
    function calc() {
      var v = readInputs(inputs), size = document.getElementById("in-size").value;
      var years = [], cgm = [], pump = [], ins = [], cureRev = [], pen = [], base = [];
      var pop = M.population.t1d_global_m * 1e6, prevCured = 0;
      for (var y = 2025; y <= 2040; y++) {
        var t = y - M.base_year;
        var bC = mk.cgm[size] * 1e9 * Math.pow(1 + v.g_cgm, t), bP = mk.pump[size] * 1e9 * Math.pow(1 + v.g_pump, t), bI = mk.insulin[size] * 1e9 * Math.pow(1 + v.g_ins, t);
        var target = y < v.approval ? 0 : v.peak * smooth((y - v.approval + 1) / v.ramp) * pop;
        var cured = Math.min(target, prevCured + v.cap), p = cured / pop;
        years.push(String(y)); pen.push(p); base.push(bC * v.sh_cgm + bP * v.sh_pump + bI * v.sh_ins);
        cgm.push(bC * v.sh_cgm * p * (1 - v.residual)); pump.push(bP * v.sh_pump * p); ins.push(bI * v.sh_ins * p);
        cureRev.push(Math.max(0, cured - prevCured) * v.price); prevCured = cured;
      }
      var i35 = years.indexOf("2035"), iEnd = years.length - 1;
      function sum(a) { return a.reduce(function (s, x) { return s + x; }, 0); }
      var disp35 = cgm[i35] + pump[i35] + ins[i35], dispEnd = cgm[iEnd] + pump[iEnd] + ins[iEnd];
      var peakCure = Math.max.apply(null, cureRev), peakYr = years[cureRev.indexOf(peakCure)];
      document.getElementById("model-kpis").innerHTML = '<div class="kpis" style="margin-top:0">' +
        kpi(money(disp35), "Displaced revenue in 2035", pct(disp35 / base[i35], 1) + " of T1D-attributable revenue") +
        kpi(money(dispEnd), "Displaced revenue in 2040", pct(pen[iEnd], 1) + " of T1D patients cured") +
        kpi(money(peakCure), "Peak annual cure sales", peakCure > 0 ? "in " + peakYr : "no approval in window") +
        kpi(money(sum(cureRev)), "Cumulative cure sales 2025–40", "vs " + money(sum(cgm) + sum(pump) + sum(ins)) + " cumulative displaced") + "</div>";
      lineChart(document.getElementById("model-chart"), {
        x: years, label: "Displaced revenue by market, 2025 to 2040",
        series: [{ name: "Insulin", color: "var(--s1)", values: ins }, { name: "CGM", color: "var(--s2)", values: cgm }, { name: "Pumps / AID", color: "var(--s3)", values: pump }],
        yFmt: function (x, tip, axis) { return axis ? money(x, 2).replace(/\.?0+([KMBT])$/, "$1") : money(x, tip ? 2 : 0); }
      });
      var rows = years.map(function (y, i) {
        return '<tr><td class="num">' + y + '</td><td class="r num">' + pct(pen[i], 1) + '</td><td class="r num">' + money(ins[i]) + '</td><td class="r num">' + money(cgm[i]) + '</td><td class="r num">' + money(pump[i]) + '</td><td class="r num"><b>' + money(ins[i] + cgm[i] + pump[i]) + '</b></td><td class="r num">' + money(cureRev[i]) + "</td></tr>";
      });
      document.getElementById("model-table").innerHTML = '<div class="table-wrap"><table class="mini-table"><thead><tr><th>Year</th><th class="r">T1D cured</th><th class="r">Insulin</th><th class="r">CGM</th><th class="r">Pumps</th><th class="r">Total displaced</th><th class="r">Cure sales</th></tr></thead><tbody>' + rows.join("") + "</tbody></table></div>" +
        '<p class="small ink2" style="margin-top:10px"><b>Read-across:</b> pump makers carry the most concentrated risk, because nearly all of their revenue is T1D. CGM makers are partly hedged by T2D, OTC, and the post-cure monitoring that may continue. Insulin is the largest dollar pool, but the most diversified one for Lilly, Novo, and Sanofi. Even in the bull case the displacement plays out over a decade-plus, which is longer than most equity holding periods. So the near-term tell is less about revenue and more about multiples (terminal-value risk) for the pump pure-plays.</p>';
    }
    box.addEventListener("input", calc); box.addEventListener("change", calc);
    setPreset("base");
  }

  views.method = function () {
    var meta = D.meta, src = meta.sources || {};
    var names = Object.keys(src).filter(function (k) { return !/^(Market data|SEC EDGAR): /.test(k); });
    var mk = Object.keys(src).filter(function (k) { return /^Market data: /.test(k); }), secs = Object.keys(src).filter(function (k) { return /^SEC EDGAR: /.test(k); });
    function okCount(list) { return list.filter(function (k) { return src[k].ok; }).length + "/" + list.length + " refreshed"; }
    var links = meta.links || {}, broken = Object.keys(links).filter(function (u) { return links[u].state === "broken"; });
    var h = '<div class="page-head"><div class="eyebrow">Methodology</div><h1>How this tracker works</h1></div><div class="grid g2">';
    h += '<section class="card"><h3>Two grades per program</h3><p class="small"><b>Stage</b> is the furthest point of active development, for example a Phase 3 that is enrolling. <b>Evidence</b> is the highest-quality human data that has actually been read out. A program at Phase 3 stage with Phase 1 evidence has a lot left to prove.</p>' +
      '<table class="mini-table"><tbody>' + [["Preclinical", "No human data (an IND filed or a registry entry alone doesn't count)."], ["Phase 1", "First-in-human safety; tiny n; open label."], ["Phase 2", "Dose/efficacy signal, often randomized, usually < 200 patients."], ["Phase 3", "Pivotal randomized data, the kind a filing rests on."], ["Filed", "Under regulatory review."], ["Approved", "FDA (or EMA) approved for a T1D indication."]]
        .map(function (r) { return "<tr><td><b>" + r[0] + "</b></td><td>" + r[1] + "</td></tr>"; }).join("") + "</tbody></table>" +
      '<p class="small" style="margin-top:8px">Registry phases are graded conservatively. A "Phase 1/2" trial counts as Phase 1.</p></section>';
    h += '<section class="card"><h3>Verification flags</h3><p class="small">Every day, the pipeline compares the curated record with live registry data and raises a flag when:</p><ul class="small"><li>a linked trial is terminated, withdrawn, or suspended while the program is marked active</li><li>the registry lists a later-phase active trial than the curated stage</li><li>a registry primary-completion date has passed but the status is still "recruiting" (a stale registry)</li><li>a record hasn\'t been updated in 18+ months</li><li>the curated summary was last verified more than 120 days ago</li><li>a cited source link returns 404</li><li>any item the curator could not verify, which is stated openly rather than guessed</li></ul></section>';
    h += '<section class="card"><h3>Data sources & refresh status</h3><table class="mini-table"><tbody>' +
      names.map(function (k) { return "<tr><td>" + esc(k) + "</td><td>" + (src[k].ok ? '<span class="pos">● ok</span>' : '<span class="neg">● stale</span> <span class="xs muted">' + esc(src[k].detail) + "</span>") + '</td><td class="xs muted num">' + esc((src[k].at || "").slice(0, 16).replace("T", " ")) + "</td></tr>"; }).join("") +
      "<tr><td>Market data (yfinance)</td><td colspan=2>" + okCount(mk) + "</td></tr><tr><td>SEC EDGAR filings</td><td colspan=2>" + okCount(secs) + "</td></tr>" +
      "<tr><td>Source links checked</td><td colspan=2>" + Object.keys(links).length + " checked · " + broken.length + " broken</td></tr></tbody></table>" +
      '<p class="xs muted" style="margin-top:8px">If a source fails, the previous day\'s data is kept and marked stale, so the site never shows blanks. Built ' + esc(meta.built_at) + ".</p></section>";
    h += '<section class="card"><h3>What this site will not do</h3><ul class="small"><li>Invent results, dates, or numbers. Unknowns show as "—", "not disclosed", or a flag.</li><li>Copy article text. News appears as headline links only.</li><li>Give medical or investment advice.</li></ul><h3 style="margin-top:12px">Personal layer</h3><p class="small">Notes in yellow boxes come from the author\'s own file (<code>data/my_notes.yaml</code>) and reflect lived experience with T1D. They are kept separate from sourced data.</p></section>';
    return h + "</div>";
  };

  // ------------------------------------------------------------ router & events
  function parseHash() {
    var raw = location.hash.replace(/^#\/?/, ""), parts = raw.split("?"), q = {};
    (parts[1] || "").split("&").forEach(function (kv) { if (kv) { var a = kv.split("="); q[decodeURIComponent(a[0])] = decodeURIComponent(a[1] || ""); } });
    return { route: parts[0], q: q };
  }
  function render() {
    var r = parseHash(), fn = views[r.route] || views[""], app = document.getElementById("app");
    app.innerHTML = fn(r.q);
    document.querySelectorAll("#tabs a").forEach(function (a) { a.classList.toggle("on", a.getAttribute("href") === "#/" + r.route); });
    if (r.route === "analysis") cureModel();
    if (r.route === "glp1") glpModel();
    if (r.q.p) { var el = document.getElementById("p-" + r.q.p); if (el) { el.scrollIntoView({ block: "start" }); el.style.outline = "2px solid var(--accent)"; } }
    else window.scrollTo(0, 0);
    var titles = { "": "Overview", pipeline: "Cure pipeline", medtech: "Medtech", glp1: "GLP-1s in T1D", catalysts: "Catalysts", companies: "Companies", analysis: "Cure impact model", method: "Methodology" };
    document.title = (r.route ? titles[r.route] + " · " : "") + "Tracking the Cure";
  }
  document.addEventListener("click", function (e) {
    var b = e.target.closest("[data-g]");
    if (b) {
      var g = b.getAttribute("data-g"), v = b.getAttribute("data-v");
      if (g === "pf") { state.pipeFilter = v; history.replaceState(null, "", "#/pipeline"); }
      if (g === "ps") state.pipeStatus = v;
      if (g === "ct") state.catType = v;
      if (g === "fc") state.fdaCode = v;
      var y = window.scrollY; render(); window.scrollTo(0, y); return;
    }
    var s = e.target.closest("[data-sort]");
    if (s) { var k = s.getAttribute("data-sort"); state.compSort = { k: k, d: state.compSort.k === k ? -state.compSort.d : (k === "ticker" || k === "name" || k === "next_earnings" ? 1 : -1) }; var y2 = window.scrollY; render(); window.scrollTo(0, y2); return; }
    if (e.target.closest("#catsort")) { state.catSort = -state.catSort; render(); }
  });
  document.addEventListener("change", function (e) { if (e.target.id === "catpast") { state.catPast = e.target.checked; render(); } });
  document.getElementById("theme").addEventListener("click", function () {
    var root = document.documentElement, cur = root.getAttribute("data-theme");
    var dark = cur ? cur === "dark" : window.matchMedia("(prefers-color-scheme: dark)").matches;
    var next = dark ? "light" : "dark";
    root.setAttribute("data-theme", next);
    try { localStorage.setItem("ttc-theme", next); } catch (err) {}
    render();
  });
  window.addEventListener("hashchange", render);

  var files = ["meta", "programs", "devices", "glp1", "catalysts", "companies", "market", "changes"];
  Promise.all(files.map(function (f) { return fetch("data/" + f + ".json", { cache: "no-cache" }).then(function (r) { if (!r.ok) throw new Error(f); return r.json(); }); }))
    .then(function (res) {
      files.forEach(function (f, i) { D[f] = res[i]; });
      var built = new Date(D.meta.built_at);
      document.getElementById("updated").innerHTML = '<span class="long">Data refreshed </span><b>' + esc(built.toLocaleString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })) + "</b>";
      render();
    })
    .catch(function (err) {
      document.getElementById("app").innerHTML = '<div class="empty">Could not load data (' + esc(err.message) + "). If you opened index.html directly from disk, serve the folder instead: <code>python -m http.server -d site</code></div>";
    });
})();
