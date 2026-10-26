# Tracking the Cure — Phase 0 visual audit and redesign proposal

*Prepared 2026-10-26 on branch `redesign/visual` (cut from `main` at `1c41b87`, no commits). Nothing in this
phase changes production, templates, styles, data, or the model. This document and the screenshots in
`docs/redesign/phase0/screenshots/` are the only new files, and they are uncommitted.*

---

## 0. How the audit was done

| Item | Result |
|---|---|
| Repository state | Clean working tree. `main` fast-forwarded to `origin/main` (one daily-data commit), then `redesign/visual` created. No stash, reset or force. |
| Local vs live | Rendered `_site/` locally from the same commit and data. Home, model, pipeline, a company page, a program page and catalysts are **byte-identical** to `joshlammbo0.github.io/tracking-the-cure/`. Local screenshots therefore are production screenshots. |
| Tests | 32/32 pass (`test_validation` 11, `test_parsing` 6, `test_model` 10, `test_render` 2 + link check). |
| Screenshots | 30 captures: home, model, pipeline, Dexcom, zimislecel × 1440×900 / 768×1024 / 375×812 × light / dark. File names: `{page}-{width}-{theme}.jpg`. |
| Measurements | In-browser scripts measured the first-visualization position, words before it, chrome height, page height, contrast of every text node in both themes, heading order, landmarks, and unlabeled controls on 9 page types. |
| Tooling limits | No Node.js on this machine and Playwright isn't installed (it would download ~150 MB of browsers). I used the app's built-in browser instead. Its captures are **first-viewport only** and **downscaled to fit the pane** (fine for layout review, not pixel review). §9 proposes how to get full-page, full-resolution captures for later phases. |

### Architecture as it actually is

```
data/*.yaml ──► pipeline/build.py (+ ctgov, pubmed, openfda, sec, markets, news) ──► site/data/*.json   [daily Action, committed by bot]
                                                                                        │
data/market.yaml ─► pipeline/model.py (single source of model truth) ───────────────────┤
                                                                                        ▼
                         pipeline/render.py (Jinja2) + pipeline/charts.py (SVG) + pipeline/og.py (PNG)
                                                                                        │
templates/*.html + site/assets/{style.css, app.js, model.js} ───────────────────────────▼
                                                                          _site/  ──► GitHub Pages
```

* **Design system:** one stylesheet (`site/assets/style.css`, ~640 lines): tokens on `:root` with light and dark sets,
  components, page-specific rules, print. Fonts: Source Serif 4 + Inter (Google Fonts). No CSS framework, no JS framework.
* **JS:** `app.js` (theme, sortable tables, filters, chart hover/keyboard layer, responsive chart redraw) and
  `model.js` (browser port of `model.run()` plus all model-page DOM updates; it self-checks against the Python numbers).
* **Charts:** server-rendered SVG from `charts.py` (stacked area, line, sparkline); the same geometry is re-implemented in `app.js` for hover and redraw.
* **Production dependencies:** requests, PyYAML, yfinance, Jinja2, Pillow. Google Fonts is the only third-party runtime request.

---

## 1. Executive assessment

The site is **credible but not yet distinctive**. The data model, sourcing, and analytical honesty are already at
the level the target audience respects. The visual layer is competent, restrained and consistent, but it reads as a
well-made research *document*, not a research *product*. Three things hold it back:

1. **The story is below the fold.** On the homepage at 1440×900, the first chart starts at **1,265 px**. At 375×812 it
   starts at **1,561 px**, after **211 words**. The first viewport is a four-line headline and a paragraph.
2. **The homepage chart is honest in its numbers but not in its proportion.** Its y-axis runs $0–4B, so displacement
   looks explosive. The thing it is measured against, about **$91.0B** of T1D-attributable revenue in 2040 (model
   output), is never drawn. For an investor audience, missing context is the fastest way to lose credibility.
3. **No visual signature.** The neutral grey-black dark mode reads like a code editor. The accent is the same blue as
   data series 1, so links and insulin compete. Every section repeats the same eyebrow, serif heading and grey paragraph.

**Scorecard** (1 = weak, 5 = excellent; current rendered implementation):

| # | Dimension | Score | Evidence |
|---|---|:-:|---|
| 1 | First impression / sophistication | 3 | Clean and serious, but text-only first viewport on every key page except company pages |
| 2 | Typography hierarchy | 3 | Good pairing; shallow contrast below H2; grey body text everywhere |
| 3 | Homepage hero | 2 | 4-line H1 takes about 45% of the viewport; no visual; stats below the fold |
| 4 | Whitespace | 3 | Generous but evenly distributed, so nothing feels emphasised |
| 5 | Layout & rhythm | 3 | Consistent, but every section has the same shape |
| 6 | Charts & data viz | 3 | Good mechanics (keyboard, tooltips, tables); missing context; ladder is heavy |
| 7 | Mobile | 3 | No overflow (verified), but long pages: model 11.5k px, GLP-1 13.9k px |
| 8 | Navigation / IA | 3 | Clear labels; hamburger below 1080 px means tablets and small laptops lose the nav |
| 9 | Light/dark consistency | 3 | Both work; dark is neutral black, not designed navy |
| 10 | Interaction & a11y | 4 | Landmarks, labels, focus states all present; one contrast failure; minor heading skips |
| 11 | Distinctiveness | 2 | Nothing a visitor would remember |
| 12 | Credibility for finance/healthcare | 4 | Sourcing, labels and caveats are excellent; presentation undersells them |

---

## 2. Ten biggest design weaknesses (ranked by impact)

Each item: **where** · what is wrong · why it hurts · fix · expected improvement · complexity · risk.

**W1. Homepage first viewport contains no evidence or model visual.** · Home hero
* Measured first-viz top: 1,265 px @1440, 1,328 px @768, 1,561 px @375; 211 words before it. The hero headline is 52 px serif over four lines.
* Analysts decide in seconds whether something is analysis or opinion. Today they see a claim, not a chart.
* Fix: a hero built around one visual and one figure (see §5), headline shortened to two lines on desktop.
* Expected: chart visible in the first viewport at 1440 and 768; the key figure visible at 375.
* Complexity: medium. Risk: low (templates/CSS only, numbers unchanged).

**W2. Displacement chart lacks its denominator.** · Home and model chart
* The stacked area of displaced revenue is auto-scaled ($0–4B). The 2040 T1D-attributable baseline it is a share of (≈$91.0B) and the 2025 market scale ($48.2B) appear only as text.
* A sophisticated reader will ask "relative to what?"; an unsophisticated one will over-read the slope.
* Fix: show displaced revenue against the T1D-attributable baseline on the same axis (same year, same denominator, so a legitimate comparison), with the displaced band highlighted and a "zoom to displaced" toggle on the model page.
* Expected: the chart itself communicates "small share, long fuse", which the copy already says.
* Complexity: medium. Risk: low for numbers (the baseline is an existing `model.py` output, `t1d_baseline_total`), but it **displays a new figure** ($91.0B), so it needs your copy approval (§10).

**W3. Model page puts four equal export buttons and 438 words before the chart.** · Model page
* Chart top 956 px @1440, 1,604 px @375. On phones the first viewport is four stacked full-width buttons.
* Utility actions outrank the answer.
* Fix: one compact "Export ▾" menu (CSV · CSV current inputs · Print · Copy link), a single-sentence lede, and the scenario switcher as a segmented control directly above an "answer row".
* Expected: chart and headline outputs in the first viewport at 1440; scenario plus answer in the first viewport at 375.
* Complexity: medium. Risk: medium. `model.js` updates specific element IDs; the layout must keep those IDs or `model.js` needs a reviewed presentation-only change (§10).

**W4. No visual signature; accent and data compete.** · Global
* Dark mode is neutral `#0e0e0d`. The accent `#184f95` and data series 1 `#2a78d6` are the same hue family. The only brand device is a small chart-line icon.
* Forgettable, and color stops carrying meaning when the link color equals the insulin color.
* Fix: deep-navy dark theme, a teal-blue accent reserved for interaction and emphasis, and a data palette deliberately distinct from the accent (§4). Add one signature device: the **evidence-gap dumbbell** (§7), used in the hero, pipeline, program pages and OG image.
* Expected: a recognisable look; color semantics become unambiguous.
* Complexity: medium (tokens). Risk: low.

**W5. The stage-vs-evidence ladder spends a lot of ink on two numbers.** · Pipeline, home, program pages
* 18 rows × 6 blocks = 108 near-identical rectangles; a 70-word explainer is required before it can be read; on phones it starts at 998 px.
* The site's most original idea is visually the hardest to read.
* Fix: a dumbbell/track chart. A filled dot marks the evidence, a ring marks the stage, and a dashed segment between them is the unproven gap. The gap is then visible without explanation (§7).
* Expected: readable in about 5 seconds; the explainer shrinks to one line.
* Complexity: medium (new `charts.py` renderer). Risk: low (same data fields).

**W6. Chrome is tall and navigation collapses too early.** · Masthead
* Chrome is 95 px at 1440 and 122 px at 768, where the disclaimer wraps to two lines. Below 1080 px all eight links hide behind "Menu".
* Every viewport loses 10–15% to chrome; tablets lose the IA entirely.
* Fix: a one-line disclaimer at every width (wording unchanged; the longer sentence moves to the footer), a 60 px masthead, and a five-item primary nav with a "More" group. The hamburger only below 720 px.
* Expected: chrome ≤ 72 px @1440, ≤ 76 px @768; nav visible on tablets.
* Complexity: low. Risk: low. **Wording of the disclaimer is preserved**; only its layout changes.

**W7. Headline numbers are set too timidly.** · Stat tiles (home, model, company)
* Stat values are 26–34 px. At 768 the five model stats wrap their labels to 3 lines ("Displaced / in / 2035").
* Investment readers scan numbers first. Small numbers with long labels read as a table, not a finding.
* Fix: a numeric display style (serif, tabular lining, 56–72 px for the single hero figure, 36–40 px for tiles), max 4 tiles per row, short labels with the qualifier moved to a footnote line.
* Complexity: low. Risk: low, provided rounding stays identical (enforced by §9).

**W8. Uniform section rhythm and grey-on-grey body text.** · All long pages
* Every section opens with eyebrow, serif H2 and grey paragraph. Body copy is `--ink-2`; most supporting text is `--muted` at 14 px. Page heights: model 7.1k px desktop / 11.5k px mobile; GLP-1 9.6k / 13.9k.
* There is no sense of progression, and the eye has nowhere to land.
* Fix: three section types (Finding, Evidence, Reference) with distinct treatments. Primary ink for body text and muted only for metadata. Long reference tables collapse by default.
* Complexity: medium. Risk: low.

**W9. Sensitivity heatmaps fail contrast and hide scale.** · Model page
* White text on bin-4 blue measured **3.64:1** (fails AA 4.5:1) in both themes, 8 cells. Bins are rank-based, so the same color means very different dollars in the two grids, and there's no legend.
* An accessibility failure on the flagship page, and a chart that can mislead.
* Fix: a value-based sequential ramp per grid with a labelled legend; text color picked per cell by contrast; the current-setting cell marked with an outline plus a "current" label.
* Complexity: low–medium. Risk: low (display only; values unchanged).

**W10. Detail pages lead with metadata, not the verdict.** · Program and company pages
* Program pages open with badges, ladder and modality; the summary starts below the fold at 1440. Company pages show the price chart first and put "T1D exposure", the reason the page exists, below the fold.
* Readers arriving from search don't immediately see why the page matters.
* Fix: a "verdict strip" under the title. Program: stage, evidence, gap and next catalyst in one row, then the reality check. Company: diabetes % of revenue and modelled cure exposure next to the price.
* Complexity: low. Risk: low.

*Smaller issues:* 1–2 heading-level skips per page (sidebar `h4` labels and the footer `h4` after `h2`). Exact values on the price chart need hover (no table equivalent). The scenario chips wrap to four rows on mobile.

---

## 3. Ten highest-impact improvements

| Rank | Improvement | Essential or aesthetic | Addresses |
|---|---|---|---|
| 1 | Homepage hero rebuilt around one visual and one figure (§5) | **Essential** | W1, W2, W7 |
| 2 | Baseline-in-context displacement chart (same year, same denominator) | **Essential** (integrity) | W2 |
| 3 | Model page: answer-first layout, Export menu, segmented scenarios | **Essential** | W3 |
| 4 | Evidence-gap dumbbell replacing the block ladder | **Essential** | W5 |
| 5 | Heatmap fix: value scale, legend, AA contrast | **Essential** (a11y) | W9 |
| 6 | Token refresh: navy dark mode, teal-blue accent, accent ≠ data palette | High impact, mostly aesthetic | W4 |
| 7 | Chrome and navigation: one-line disclaimer, 60 px masthead, 5 + More | High impact | W6 |
| 8 | Numeric display style and 4-tile maximum | Aesthetic, high impact | W7 |
| 9 | Section types (Finding / Evidence / Reference), primary-ink body text | Aesthetic | W8 |
| 10 | Verdict strips on program and company pages | High impact on detail pages | W10 |

---

## 4. Proposed design tokens and type scale

All values are proposals to validate in Phase 1. Every text pair must pass AA. The data palette is validated
for color-vision deficiency with a Python port of the dataviz validator (no Node needed). Hex values below are
starting points and may be re-stepped by the validator.

### Color

| Token | Light | Dark (navy) | Role |
|---|---|---|---|
| `--bg` | `#F7F5F0` warm paper | `#0B1322` deep navy | Page |
| `--surface` | `#FCFBF8` | `#111B2E` | Charts, cards, tables |
| `--surface-2` | `#EFECE5` | `#18243A` | Bands, hover, code |
| `--ink` | `#121417` | `#E9EDF3` | Headlines, body text |
| `--ink-2` | `#3A3F47` | `#C4CCD8` | Secondary text |
| `--muted` | `#5F6670` | `#97A3B6` | Metadata only |
| `--rule` | `#E2DED5` | `#22304A` | Hairlines |
| `--rule-strong` | `#C9C3B6` | `#33435F` | Table heads, emphasis rule |
| `--accent` | `#0B6A86` teal-blue | `#5CC3DE` | Links, focus, key figure, selected state |
| `--accent-soft` | `#E1F0F4` | `#123247` | Selected backgrounds |
| `--s-insulin` | `#3B5BA9` indigo | `#7E9BE6` | Data series 1 |
| `--s-cgm` | `#D0773A` amber | `#E59A5E` | Data series 2 |
| `--s-pump` | `#2E9B78` green | `#4FC197` | Data series 3 |
| `--s-baseline` | `#C9C3B6` (ghost) | `#33435F` | Context bands (baseline revenue) |
| `--good` / `--bad` | `#11663A` / `#A82A2A` | `#5BD18B` / `#F08080` | Returns (always with a sign) |

*Why teal-blue for the accent and indigo/amber/green for data:* the accent stays reserved for interaction and for the
single hero figure, so a color never means both "clickable" and "insulin".

### Typography

| Style | Family | Size / line-height (desktop → 375) | Weight | Use |
|---|---|---|---|---|
| Display figure | Source Serif 4, tabular lining | 72/1.0 → 52/1.0 | 600 | One hero number per page |
| H1 | Source Serif 4 | 44/1.1 → 32/1.15 | 600 | Page titles (≤ 2 lines desktop) |
| H2 | Source Serif 4 | 30/1.2 → 24/1.25 | 600 | Section titles |
| H3 | Inter | 18/1.35 | 600 | Sub-sections, card titles |
| Lede | Source Serif 4 | 20/1.5 → 18/1.5 | 400 | One per page, ≤ 2 lines desktop |
| Body | Inter | 16/1.6 | 400 | Prose (primary ink) |
| UI | Inter | 15/1.4 | 500 | Nav, buttons, controls |
| Table | Inter, tabular | 14/1.45 | 400–600 | Data tables |
| Caption | Inter | 13/1.45 | 400 | Figure sources, footnotes |
| Micro | Inter, small caps | 12/1.3 | 600 | Labels, eyebrows (floor for UI text) |
| Axis | Inter, tabular | 11–12 | 400 | Chart axes only |

### Space, grid, shape

* Space scale (px): 4, 8, 12, 16, 24, 32, 48, 64, 96, 128. Section padding 96 desktop / 56 mobile.
* Grid: 12 columns, 24 px gutters, 1200 px text width, 1320 px "wide" for data figures.
* Radius: 4 px (controls), 2 px (badges); no pills except the segmented control's outer track.
* Lines: 1 px hairline by default; a 2 px ink rule marks the start of a Finding.
* Elevation: none, except one 1-layer shadow for popovers and tooltips.
* Motion: 120 ms color and opacity transitions only; none under `prefers-reduced-motion`.

---

## 5. Homepage redesign — two concepts

Both concepts keep every existing claim and caveat. Neither puts the $48.2B (2025, all patients) and the $3.2B
(2040, displaced) in one pie or bar: they have different years and denominators.

### Concept A — "Two questions" (split hero)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ How close is a cure for type 1 diabetes, and what would it displace?         │  ← H1, 2 lines
├───────────────────────────────────────┬──────────────────────────────────────┤
│ THE SCIENCE                           │ THE ECONOMICS                        │
│ 15 active programs                    │ $3.2B   displaced in 2040            │
│ ●──○  zimislecel   Ph2 → Ph3          │         base case · 3.5% of 2040     │
│ ●──○  baricitinib  Ph2 → Ph3          │         T1D-attributable revenue     │
│ ●─────○ frexalimab Pre → Ph2          │ [mini displacement chart 2025-40]    │
│ ●  teplizumab      approved           │ Model output, not a forecast.        │
│ → All programs                        │ → Open the model                     │
└───────────────────────────────────────┴──────────────────────────────────────┘
```
*Strength:* both questions get equal billing, which suits audience 2 (scientists).
*Weakness:* two half-width visuals are each too small to be persuasive; it reads as a dashboard.

### Concept B — "The long fuse" (recommended)

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ A cure would rewrite a $48B market. The model says the revenue                │  ← H1 (proposed copy, needs approval)
│ shifts slowly, and the strategic exposure starts long before.                 │
├──────────────────────────────────────────────────────────────────────────────┤
│  $3.2B                                     ┌─ T1D-attributable revenue ─────┐ │
│  displaced in 2040, base case              │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │ │ ← ghost band: baseline
│  3.5% of 2040 T1D-attributable revenue     │ ░░░░░░░░░░░░░░░░░░░░░░▓▓▓▓▓▓▓  │ │ ← highlighted: displaced
│                                            │ 2025    approval 2031     2040  │ │
│  Model output under labelled               └────────────────────────────────┘ │
│  assumptions, not a forecast.                                                 │
├──────────────────────────────────────────────────────────────────────────────┤
│ EVIDENCE TODAY  ●──○ 15 active programs · 2 approved · 0 GLP-1 T1D labels → │  ← one-line science strip
└──────────────────────────────────────────────────────────────────────────────┘
```
* **Left:** the display figure ($3.2B) with its exact existing qualifier ("3.5% of T1D-attributable revenue") and the "not a forecast" caveat. The H1 carries the $48B present-scale fact as words, not as a bar.
* **Right:** the T1D-attributable baseline drawn as a ghost area, with the displaced revenue as a highlighted band inside it, on one axis. Both series are the same year and the same denominator, so the proportion is honest. A vertical marker shows the base-case approval year.
* **Below:** a one-line evidence strip using the dumbbell glyph, linking to the pipeline.
* **Mobile (375):** H1 (3 lines) → $3.2B figure and qualifier → chart (full width) → evidence strip. The figure sits within the first 812 px (target y ≤ 600).
* *Why B:* it makes the site's actual thesis (limited direct displacement, long-duration strategic exposure) visible in a single chart that an analyst can verify. It gives audience 1 the investment framing first while keeping audience 2's evidence one line below.
* **Approvals needed for B:** (a) new H1 wording (current H1 kept as the fallback); (b) displaying the T1D-attributable baseline in the chart, about $17.9B (2025) → $91.0B (2040). These are existing `model.py` outputs, already in the CSV, but not printed on the site today.

The remaining homepage sections, kept and reordered: Investment implications (band) → Hype map preview (dumbbell, top 8) → Next catalysts + registry watch → About strip.

---

## 6. Cure Impact Model redesign concept

```
Cure Impact Model                                        [Export ▾]   ← one line of chrome
How much T1D-driven revenue would a functional cure displace?        ← one-sentence lede

[ Bear | Base | Bull | Immunosuppression required ]   ← segmented control (scroll on mobile)
Base: a no-immunosuppression product is approved early next decade…  ← existing thesis text

ANSWER ROW   $864M 2035 · $3.2B 2040 · 4.1% cured by 2040 · $20.0B peak cure sales   (4 tiles max)
┌──────────────── chart (baseline context + displaced) ───────────────┐ ┌ Key levers ──────┐
│                                                                      │ │ Approval  2031 ▸ │
│                                                                      │ │ Peak share 15% ▸ │
└──────────────────────────────────────────────────────────────────────┘ │ Capacity 40K   ▸ │
 Toggle: [In context | Displaced only]                                   │ Price $500K    ▸ │
                                                                         │ Advanced (8) ▾   │
Tabs / anchored sections:  Outputs · Sensitivity · Company read-across · Methodology
```
* **Answer-first:** scenario, then four headline outputs, then the chart. Inputs sit to the right on desktop (sticky) and below the answer on mobile (as today). The fifth tile (cumulative cure sales) moves into the Outputs table.
* **Export menu** replaces four equal-weight buttons. Same four actions, same files.
* **Company read-across chart** (new), labelled "Modelled displacement in 2040 relative to **current** company revenue, base case; company shares held at today's levels":
  * Pump pure-plays (Insulet, Tandem, Beta Bionics, MiniMed): **one bar**, 20.9%, with the four names listed under it, not four identical bars.
  * CGM pure-plays (Dexcom, Senseonics): one bar, 10.6%.
  * Diversified: Abbott 1.9%, Medtronic 1.8%, Embecta 1.6%, Novo Nordisk 0.3%, Sanofi 0.1%.
  * Not modelled: Lilly (insulin revenue not disclosed in primary sources), listed as text, not plotted.
  * The existing table stays below the chart.
* **Sensitivity:** value-based ramp with a legend, AA text, and the current cell labelled (W9).
* **Methodology** collapses to a short "How it works" section plus the existing sources table.
* **Protected-file impact:** calculations untouched. The new chart and tiles must update live, which means either keeping every element ID that `model.js` writes to (preferred) or a reviewed **presentation-only** change to `model.js`: one `CustomEvent` dispatch after each render, so a new `model-view.js` can draw the new visuals. That change requires your approval (§10).

---

## 7. Pipeline / stage-vs-evidence redesign concept

```
Stage reached vs. results reported                         Sort: [Stage | Gap | Approach]
            Preclin.   Ph 1     Ph 2     Ph 3    Filed   Approved
Lantidra                                                  ●        (approved, no gap)
Zimislecel                     ●- - - - ○                          (+1: Ph 3 reached, Ph 2 results)
Frexalimab  ●- - - - - - - - - ○                                   (+2)
UP421                ●                                              (Ph 1, matched)
SC451       ●                                                       (preclinical, no human results)
VX-264 ✕             ●  (discontinued, grey, struck)
```
* **Encoding:** filled dot = highest stage with reported results; open ring = furthest stage reached; dashed segment = stages reached without reported results. Discontinued programs use grey and strikethrough, with "discontinued" written out (never color alone).
* **Explainer** drops to one line plus an inline key. The accurate wording agreed earlier ("results reported", "stage reached") is kept.
* **Views:** rows grouped by approach (default) or sorted by gap; the stage × evidence matrix from the research note becomes a toggle.
* **Mobile:** stage labels abbreviated in a sticky header; each row is name plus track at full width; no horizontal scroll.
* **Reuse:** the same renderer (new `charts.dumbbell()`) feeds the homepage preview, program pages (single-row version in the verdict strip), and the OG image.

---

## 8. Before → after, page by page

| Page | Before (measured / observed) | After (target) |
|---|---|---|
| Home @1440 | Viewport = headline + paragraph + buttons; chart at 1,265 px | Display figure + baseline-context chart within 900 px; evidence strip visible or one scroll away |
| Home @375 | First 812 px = eyebrow, 5-line H1, lede, 2 buttons | H1 ≤ 3 lines, $3.2B figure + qualifier within the first viewport; chart follows |
| Model @1440 | Lede (4 lines), 4 export buttons, 4 chips, stats; chart at 956 px | Title + lede (1 line) + segmented control + 4 tiles + chart top ≤ 560 px |
| Model @375 | 4 full-width buttons fill the first viewport | Segmented control (horizontal scroll) + answer tiles in the first viewport; Export in a menu |
| Pipeline | 108 blocks; 70-word explainer; viz at 998 px on mobile | Dumbbells; 1-line key; viz within the first viewport at 768 and 1440 |
| Program | Badges, ladder, modality first; summary below fold | Verdict strip (stage · evidence · gap · next catalyst) + reality check above the fold |
| Company | Price chart first; T1D exposure below fold | Price + diabetes % + modelled exposure in the header row; chart second |
| Dark mode | Neutral black `#0e0e0d` | Deep navy system, separately tuned (not inverted) |
| Chrome | 95 px (1440) / 122 px (768) | ≤ 72 / ≤ 76 px; nav visible ≥ 720 px |

---

## 9. Numerical-regression protection (built at the start of Phase 1, before any visual change)

1. **Frozen snapshot.** Copy `site/data/*.json` at `1c41b87` into `docs/redesign/baseline/data/`, and render with a
   fixed date. This needs two small, justified **presentation-only** additions to `pipeline/render.py`:
   `--data-dir` (read JSON from the snapshot instead of `site/data/`) and `--today` (freeze "in N days" and the
   upcoming-catalyst filter). Defaults are unchanged, so the daily Action behaves exactly as now.
2. **Extractor** `tools/extract_numbers.py` (dev-only, not deployed). For every rendered page it records each text
   node containing a digit, `$`, `%`, `×` or a caveat keyword (assumption, estimate, not a forecast, not advice,
   registry, unverified, model output), with its page, nearest heading and DOM path. It also records chart labels and
   annotations from SVG `<text>`, the model JSON (all scenarios, sensitivities, read-across), and a hash of the CSV.
3. **Baseline** saved as `docs/redesign/baseline/numbers.json` from the pre-redesign build.
4. **Compare** `tools/compare_numbers.py`: re-extract after each phase and report added, removed and changed values
   by page and context. Exit non-zero on any change not listed in an approved-changes file. Re-ordering or moving a
   value is reported separately from changing it.
5. Run alongside `pytest` and the in-page JS/Python model self-check (`TTC.modelCheck === "ok"`).

**Screenshots for later phases:** either (a) continue with the built-in browser (first-viewport, downscaled), or
(b) add Playwright as a **dev-only** dependency (`requirements-dev.txt`, ~150 MB browser download, never used in
the Action) for full-page, full-resolution captures of 6 configurations × each representative page. (b) gives far
better before/after evidence. **I recommend (b), pending your approval of the download.**

---

## 10. Technical risks and protected files

| File / system | Status | Planned interaction |
|---|---|---|
| `pipeline/model.py` | **Protected** | None. Read-only use of existing outputs. |
| `site/assets/model.js` | **Protected** | Preferred: none (keep DOM IDs). Fallback needing approval: one presentation-only `CustomEvent` dispatch; no calculation lines touched. |
| `data/*.yaml` | **Protected** | None. |
| `site/data/*.json` | **Protected** | None. Snapshot copied, never edited. |
| `pipeline/build.py` + ingestion modules | **Protected** | None. |
| `.github/workflows/refresh.yml` | **Protected** | None. |
| Model validation tests (`tests/test_model.py`) | **Protected** | None. New tests are added in separate files. |
| `pipeline/render.py` | Presentation; changes need justification | Phase 1: `--data-dir`, `--today` flags (defaults unchanged). Phases 2–4: pass existing model series (`t1d_baseline`) and category groupings to templates; nav config. No calculation. |
| `pipeline/charts.py` | Presentation | New renderers: `context_area` (baseline + displaced), `dumbbell`, `category_bars`. Existing functions kept. |
| `pipeline/og.py` | Presentation; **only after design approval** | Phase 5: new share image using the dumbbell / long-fuse visual. |
| `templates/*`, `site/assets/style.css`, `site/assets/app.js` | Presentation | Main surface of change. |

**Risks**
* *Model page DOM coupling.* `model.js` writes into `#model-stats`, `#market-table`, `#year-table`, `#sens-ap`, `#sens-pc`, `#ra-table` and the chart. Mitigation: keep these IDs and their table structures; add new visuals beside them.
* *Daily data churn.* `main` gets a data commit every day. Keep the branch presentation-only and merge `main` into it before each review; compare numbers only against the frozen snapshot, never across refreshes.
* *Copy creep.* Any wording change (H1, ledes, labels) is listed in each phase report for approval before merge.
* *Font loading.* Larger display figures make layout shift visible: preload the two weights used, with `size-adjust` fallbacks.
* *Branch state in GitHub Desktop.* The working copy is now on `redesign/visual`. To publish anything else to production, switch back to `main` first.

---

## 11. Objective acceptance criteria (every phase)

**Visual**
* Home @1440×900: top of the primary visualization < 900 px (target ≤ 640). Home @375×812: hero figure and its qualifier within 812 px.
* Model @1440: chart top ≤ 640 px. Pipeline @768 and @1440: first dumbbell row within the first viewport.
* Zero elements overflowing the viewport at 375, 768, 1024 and 1440 (scripted scan, as used in this audit).
* No clipped or overlapping labels: scripted check of SVG `<text>` bounding boxes.
* Charts readable without hover: every chart has a visible key and an adjacent table or direct labels.
* Chrome height ≤ 72 px @1440 and ≤ 76 px @768; disclaimer wording identical.

**Accessibility**
* 0 text nodes below WCAG AA in either theme (scripted scan; baseline today: 8 failures, all heatmap cells).
* 0 heading-level skips in `<main>` (baseline: 1–2 per page).
* All controls keyboard-operable with visible focus; segmented control and Export menu follow WAI-ARIA patterns.
* No motion under `prefers-reduced-motion`.

**Engineering and integrity**
* `pytest` passes (32 existing tests, plus new ones).
* `TTC.modelCheck === "ok"` on the model page; `model.py` and `model.js` unchanged (or the approved one-line event only).
* Numbers diff against the frozen baseline: empty, or every change in the approved list.
* Internal link check passes; 56 pages render; offline build passes.
* No new production dependencies; no changes to protected files.

**Per-phase report:** before/after screenshots (6 configurations per representative page), changed-file list,
numbers diff, test output, known limitations, remaining opportunities.

---

## 12. Expected file changes by phase

| Phase | Files | Essential / aesthetic |
|---|---|---|
| 1 — Tokens & components | `style.css` (tokens, type scale, components), `base.html` (chrome, nav), `_macros.html` (stat, badge, section types), `render.py` (`--data-dir`, `--today`; nav config), `tools/extract_numbers.py`, `tools/compare_numbers.py`, `docs/redesign/baseline/*`, new `tests/test_presentation.py` (contrast and heading checks on rendered HTML) | Essential (baseline, a11y, chrome) + aesthetic (palette) |
| 2 — Homepage | `index.html`, `charts.py` (`context_area`), `render.py` (pass baseline series), `style.css`, `app.js` (hover for the new chart) | Essential |
| 3 — Model | `model.html`, `style.css`, `charts.py` (`category_bars`), new `model-view.js`; `model.js` only if the event hook is approved | Essential |
| 4 — Pipeline | `pipeline.html`, `program.html`, `_macros.html`, `charts.py` (`dumbbell`), `style.css`, `app.js` (sort toggle) | Essential |
| 5 — Remaining pages & QA | `companies.html`, `company.html`, `catalysts.html`, `glp1.html`, `medtech.html`, `device_category.html`, `research*.html`, `methodology.html`, `about.html`, `og.py` (after approval), `README.md`, `DESIGN_NOTES.md` | Mostly aesthetic + verdict strips |

---

## 13. Recommended order of work

1. **Phase 1a — Safety net first:** frozen snapshot, extractor and comparer, baseline captured, screenshot tooling decided. No visual change.
2. **Phase 1b — Tokens, type and chrome:** new palette (validated), type scale, masthead and disclaimer, navigation, heatmap contrast fix. Report numbers diff (expected: empty).
3. **Phase 2 — Homepage** (Concept B, pending your choice and copy approval).
4. **Phase 3 — Model page.**
5. **Phase 4 — Pipeline and the dumbbell, reused on program pages.**
6. **Phase 5 — Remaining pages, OG image (after approval), final QA** across 6 configurations, accessibility scan, numbers diff, link check, offline build, fresh pipeline run.

### Decisions I need from you before Phase 1

1. Approve the overall direction and the token proposal (§4)?
2. Homepage: Concept **B** (recommended) or A?
3. May the homepage and model chart display the T1D-attributable baseline (≈$17.9B → $91.0B, existing model output) for context?
4. Proposed H1 for Concept B (or keep the current H1)?
5. Playwright as a dev-only dependency for full-page screenshots (~150 MB download)?
6. If needed in Phase 3: the one-line, presentation-only `CustomEvent` in `model.js`?
7. The two `render.py` flags (`--data-dir`, `--today`) for the frozen numerical baseline?
