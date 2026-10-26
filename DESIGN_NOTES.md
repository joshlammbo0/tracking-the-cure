# Design notes — Tracking the Cure rebuild

Running log of the review, the plan, and every decision made during the rebuild.
Newest decisions are appended at the bottom of the log.

## 1. Critique of the current site (reviewed 2026-10-24 at desktop width, light mode)

**What's strong**

- The data model is genuinely good: every program has a stage grade *and* an evidence
  grade, a reality check, a next catalyst and primary-source links. The flag system
  (registry vs. curated disagreement, stale verification, unverified claims) is the
  kind of rigor a reviewer will respect.
- The pipeline is robust: each source fails soft, previous data is kept, health is
  recorded per source.
- The Cure Impact Model already has sensible mechanics (S-curve adoption, capacity
  cap, T1D share per market, residual CGM use) and cites its market sizes.

**What's weak**

1. *Looks like a SaaS admin template, not research.* Rounded white cards on a grey
   page, system font, pill chips, emoji-like theme toggle. Everything is a box, and
   many boxes contain boxes (KPI cards inside sections inside cards).
2. *No hierarchy.* Hero, KPIs, hype map and catalysts all compete at the same weight.
   The thesis ("separating clinical progress from hype") is a label, not an argument.
3. *The best idea is buried.* The Cure Impact Model is tab 7 of 8. A recruiter never
   sees it. Its outputs are four tiles of raw numbers with no "so what".
4. *One URL.* Everything is a hash route rendered client-side from JSON: no per-page
   titles in the HTML, no meta descriptions, no OG images, nothing to link to a
   specific program or company, poor SEO, blank page without JS.
5. *Tables are wide and dense* (Companies overflows horizontally at desktop width with
   notes text in a numeric table).
6. *No narrative.* There is no written analysis that turns the data into a view,
   which is what an investment-banking reader is screening for.
7. *Repo hygiene.* Stray duplicates of the YAML and workflow files at the repo root
   from the first manual upload; `validate.yml` sits at the root so the PR check never
   runs; a broken `.github/workflows/refresh/.yml`; no tests.

## 2. Plan

Architecture
- Keep `pipeline/build.py` exactly as the data step (writes `site/data/*.json`).
- Add `pipeline/model.py`: the Cure Impact Model in Python — the single source of truth
  for every number printed in HTML (homepage preview, flagship page tables, sensitivity
  grids, company read-across, research notes, CSV). The browser re-implements the same
  formula only for the interactive sliders, and QA checks the two agree.
- Add `pipeline/render.py` (Jinja2): reads curated YAML + `site/data/*.json`, renders
  real pages into `_site/` (git-ignored build output) along with assets, data, CSV,
  `.ics`, `sitemap.xml`, `robots.txt`, and an OG share image (SVG→PNG-free: a
  hand-built PNG via Pillow so no browser is needed in CI).
- Workflow: refresh → commit `site/data` → render → upload `_site` → deploy. PR
  validation runs the offline build, the render, and `pytest`.

Information architecture (real URLs)
- `/` Home · `/model/` Cure Impact Model · `/pipeline/` cure programs ·
  `/programs/<id>/` · `/glp1/` · `/medtech/` + `/medtech/<category>/` ·
  `/companies/` + `/companies/<ticker>/` · `/catalysts/` (+ `catalysts.ics`) ·
  `/research/` + 3 notes · `/methodology/` · `/about/`.

Design direction
- "Sell-side initiation meets fintech dashboard": serif display face for headlines
  (Source Serif 4), clean grotesk for UI (Inter), tabular figures everywhere numbers
  appear. Warm off-white paper in light mode, deep ink-navy in dark. One accent (deep
  teal-blue) plus a restrained 3-colour data palette. Hairline rules instead of boxes;
  cards only where an object is genuinely a card.

## 3. Decision log

- **Project location.** The session started in an empty scratch folder; the real repo is
  `~/Documents/GitHub/tracking-the-cure` (the GitHub Desktop clone). All work happens there.
- **No branch / no commits.** Per instructions, changes are left uncommitted in the working
  tree for review in GitHub Desktop.
- **Local Python is 3.9** (Action uses 3.12). All new code stays 3.9-compatible.
- **Company exposure data** (new `exposure` fields in `data/companies.yaml`): Novo insulin 17.2% (FY2025 6-K),
  Sanofi Lantus+Toujeo 7.1% floor (Q4 2025 6-K), Abbott Diabetes Care 18% (FY2025 release). Lilly's insulin revenue
  isn't broken out in its 10-K or Q4 release, so it's shown as *unknown*, not estimated. MDT is derived live from MMED/MDT revenue.
- **Scenario presets** moved from JS into `data/market.yaml` (`scenarios:`), so Python and JS share them.
- **Pump-CAGR slider bug**: the old slider's step (0.01) silently rounded the sourced 12.7% to 13%. The new sliders use step 0.001.
- **OG images** are drawn with Pillow and cached in `site/assets/og/`. They carry no live numbers, so they don't go stale.
- **Build output** goes to `_site/` (git-ignored). The data bot still commits only `site/data`.

- **Data correction.** `programs.yaml` called SURPASS-T1D the "first industry-sponsored Phase 3" of a GLP-1-class
  drug in T1D; Novo's liraglutide ADJUNCT ONE/TWO (2013–15) were exactly that. Reworded to "first … since ADJUNCT".
  Worth a final check by the author.
- **Model page form state.** Browsers restore slider positions on reload, which silently showed stale numbers.
  The form is `autocomplete="off"` and model.js resets to the base case before reading the URL.
- **Read-across notes** moved out of the table into a numbered "basis" list; the table stays scannable.
- **Catalyst timeline** collapses earnings into one line per quarter (14 earnings dates otherwise swamp Q4).
- **Calendar UIDs** are hashes of type + title + related record, so a slipped date updates the event instead of
  creating a duplicate.
- **favicon.ico** is generated, because browsers request it even with an SVG icon.
- **`site/data` reverted to HEAD** before handoff, so the working tree doesn't conflict with the bot's daily data commits.
  The new dated price `history` and `exposure` fields appear in the JSON after the first Action run; until then the
  company charts fall back to the 1-year weekly series (labelled "approx.").

## 4. QA results (2026-10-24)

- Fresh live pipeline run: all sources refreshed, no failures. Offline build and render pass on a clean copy of the
  tree (no cached share images).
- 32 pytest tests: validation rules, registry/FDA/SEC parsing, pinned model outputs, full render, and every internal link.
- In the browser: no console errors (after adding favicon.ico); JS model matches Python for all four presets;
  presets, sliders, URL sharing, CSV and the keyboard-operable chart work.
- 375px: no element overflows the viewport on any page type (measured programmatically); mobile menu works.
- Light and dark checked on home, model, program and company pages.

## 5. Placeholders left for the author

- `templates/about.html`: name, school/degree/year, photo, LinkedIn, email, a personal sentence, and a disclosure of
  any positions held in covered securities. All marked `[like this]` and styled as visible placeholders.
- `data/my_notes.yaml`: device takes and program commentary (unchanged; placeholders stay hidden).

## 6. Design revision after external critique (2026-10-25)

The critique's central point held up: density and hierarchy, not palette or fonts. Changes, in the agreed order:

1. **Type and spacing together.** `--fs-sm` 13→14px (navigation, tables, chips, captions); 12px floor for UI text
   (badges, tags, header labels, timeline cards). 11px is allowed only for chart axis labels and the mobile hype-map
   stage scale. Table rows, list rows, chips and buttons got more padding (chips ≥40px tall, buttons ≥44px).
   Charts now redraw at their real pixel width under 600px (`TTC.fitCfg`), so axis labels stay ~11px on phones
   instead of being scaled down to ~5px with the SVG.
2. **Homepage.** 3 hero stats instead of 5. The model block keeps its substance (chart, 2035/2040 totals, a 2040
   per-market breakdown, a one-line assumption summary) but the full assumption list and market table moved to the
   model page. The three implications sit in their own full-width tinted band. The hype map shows the top 8 active programs.
3. **Model page.** Results come before inputs below 960px, with a jump link. The 12 inputs are split into 4 key levers
   plus a collapsed "Advanced assumptions (8)" group, which opens automatically for shared custom links. The preset
   table is labelled "Fixed" and explains that it doesn't move with the inputs.
4. **Companies.** One six-column table with group filters: market cap, 1-year return, revenue, disclosed diabetes
   share, and a separately defined "Cure exposure, 2040" (model output). Both definitions sit above the table. Checked
   at 1024, 768 (no sideways scroll) and 375 (market cap and revenue hidden; they're on each company page).
5. **Hype map wording.** It now says "results reported at this stage" vs. "stage reached, results not yet reported",
   and explains that a Preclinical fill means no human results, so no claim of proven efficacy is implied.
   The gap column is "Ahead of results".
6. **Catalysts / GLP-1.** The timeline covers the next three quarters, with later items summarised. The full table is
   collapsed by default. The GLP-1 label check leads with one data-driven sentence; the per-brand table is collapsed.
7. **Polish.** Shorter disclaimer strip. Research index cards lead with each note's headline figure.
   Asset URLs carry content-hash `?v=` tags so a deploy never serves a stale stylesheet.

Declined from the critique: removing the timeline/table duplication on Catalysts (they serve different jobs) and
cutting navigation destinations (eight is right; the menu now collapses below 1080px).

## 7. Visual redesign (branch `redesign/visual`)

Phase 0 audit: `docs/redesign/PHASE0_AUDIT.md`. Phase 1 report: `docs/redesign/PHASE1_REPORT.md`.
Every phase is checked against a frozen data snapshot with `python -m tools.numbers check` (no displayed number,
unit or caveat may change without approval) and `python -m tools.shots` (full-page screenshots and layout/a11y
metrics), plus `python -m tools.palette` for colour tokens.
Phases 2–5 reports and the final completion report are alongside (`PHASE2_REPORT.md` … `FINAL_REPORT.md`);
`python -m tools.audit` runs the full regression audit (every page × 3 widths × 2 themes, plus interactions).
