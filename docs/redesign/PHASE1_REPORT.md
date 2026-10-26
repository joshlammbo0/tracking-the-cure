# Phase 1 report — safety net, tokens, typography, chrome

*Branch `redesign/visual`, uncommitted. Frozen comparison data: `site/data` at `1c41b87`, rendered as of 2026-10-26.*

## What changed

### 1a. Safety net (no visual change)
| Item | Where | Notes |
|---|---|---|
| Frozen data snapshot | `docs/redesign/baseline/data/` | Copy of `site/data/*.json` at `1c41b87`. Never edited. |
| Render flags | `pipeline/render.py` | `--data-dir`, `--today`, `--styleguide`. Defaults unchanged: a plain `python -m pipeline.render` output is byte-identical to before (verified with `diff -r`). |
| Numbers guard | `tools/numbers.py` | `baseline` / `check`. Captures 4,321 displayed numbers and caveats on 56 pages, 1,295 model values (all scenarios, sensitivities, read-across) and the CSV hash. Reports removed / added / moved. |
| Guard tests | `tests/test_numbers_guard.py` | Proves a $1.4B → $1.38B change blocks, a dropped caveat blocks, a pure move doesn't, and a model or CSV change blocks. |
| Screenshots + metrics | `tools/shots.py` | Playwright (dev-only, `requirements-dev.txt`). Full-page captures for 5 pages × 6 configurations, plus metrics for 12 page types × 6 configurations. |
| Palette validator | `tools/palette.py` | Text AA, series 3:1 on surface, OKLab ΔE under protan/deutan/tritan simulation. Runs in the tests. |

### 1b. Design foundations
| Change | Detail |
|---|---|
| Colour tokens | Warm paper light theme; **deep-navy dark theme** (`#0B1322`); teal-blue accent reserved for interaction; data series moved off the accent hue (indigo / amber / green). All pairs validated (§ Validation). |
| Heatmap contrast | Text colour is now a token per step (`--heat-ink-0…5`) chosen to pass AA on that step. Fixes the 8 failing cells. CSS only, so `model.js` is untouched. |
| Type scale | `--fs-cap` 13, `--fs-ui` 15 (nav, buttons, chips), H2 30, lede 20, H3 now Inter 18/600, display figure token 52→72 px (used from Phase 2), stat values 28→38 px fluid with tabular figures. |
| Shape | Radius 6 → 4 px; chips are no longer pills. |
| Chrome | Disclaimer bar is one line at every width (22 px); masthead 48 px. Total chrome 71 px (was 95 / 122). |
| Navigation | Five primary links (Model, Pipeline, Companies, Catalysts, Research) plus a **More** menu (GLP-1s in T1D, Medtech, Methodology, About). Visible from 760 px up; was hidden below 1080 px. Closes on outside click or Escape. Phone menu unchanged. |
| Headings | Sidebar and label headings re-levelled (`h4` → `h3`/`h2` with a `.label-h` style that looks the same). 0 skips in `<main>`. |
| Component reference | `templates/styleguide.html`, rendered only with `--styleguide` (noindex, not linked, not in the sitemap, never built by the Action). |

## Numerical-integrity comparison (frozen data, same date)

```
Model values changed: 0 · CSV changed: False
Text items removed: 112 · added: 112 · moved only: 4 (research index, new screen-reader heading)
```
Every one of the 112 + 112 differences is one of **two presentation-text changes, repeated on all 56 pages**:

| # | Before | After | Why |
|---|---|---|---|
| 1 | Nav label "GLP-1s" | "GLP-1s in T1D" (in the More menu) | Clearer inside a menu |
| 2 | Footer: "News appears as headline links only; …" | Same text, prefixed with the disclaimer bar's second sentence: "Independent research. Data may be incomplete or delayed; every record links to its source." | Phones no longer show that sentence in the bar, so it now also appears in the footer of every page. Nothing removed. |

**Status: blocking until you approve these two.** Once approved I'll add them to `docs/redesign/approved_changes.yaml`, and `python -m tools.numbers check` will pass.

Navigation labels without digits aren't captured by the guard, so they're listed here for approval: desktop nav "Cure Impact Model" → **"Model"**, "Cure pipeline" → **"Pipeline"**. The phone menu keeps the full labels.

## Layout and accessibility metrics (frozen data; full table in `phase1/{before,after}/metrics.json`)

| Measure | Before | After | Target |
|---|---|---|---|
| Text below WCAG AA, 72 page/size/theme configurations | **48** (model heatmap) | **0** | 0 ✓ |
| Heading-level skips in `<main>` | **30** | **0** | 0 ✓ |
| Configurations with horizontal overflow | 0 | 0 | 0 ✓ |
| Chrome height @1440 / @768 / @375 | 95 / 122 / 95 | **71 / 71 / 71** | ≤72 / ≤76 ✓ |
| Nav visible at 768 | No | **Yes** | Yes ✓ |
| `TTC.modelCheck` (JS = Python) | ok | ok | ok ✓ |
| Home first-viz top @1440 | 1,265 | 1,225 | < 900: **Phase 2** |
| Model chart top @1440 | 955 | 923 | ≤ 640: **Phase 3** |

## Validation of the new palette (`python -m tools.palette`)

* Text: every ink / ink-2 / muted / accent / status pair ≥ 4.5:1 on bg, surface and surface-2 in both themes. The lowest pair is muted on surface-2 (light), 4.92:1.
* Series on chart surface ≥ 3:1 (lowest: light green 3.36:1).
* Series separation, all pairs: normal-vision ΔE ≥ 19; worst colour-vision-deficiency ΔE 8.2 (dark CGM vs pumps, protan), minimum 8.

## Tests
`pytest`: **39 passed**. The 32 existing tests plus 5 numbers-guard and 2 presentation tests (palette; heading order, disclaimer and navigation on every rendered page). Offline build passes. The model CSV is unchanged.

## Protected files
`git diff` on `pipeline/model.py`, `site/assets/model.js`, `data/`, `site/data/`, `pipeline/build.py` and the ingestion modules, `.github/workflows/`, and `tests/test_model.py`: **empty**.

## Screenshots
* Before: `docs/redesign/phase1/before/{page}-{1440|768|375}-{light|dark}.jpg` (full page)
* After: `docs/redesign/phase1/after/…` (same names)
* These full-page JPGs (~12 MB per set) are git-ignored so the repository doesn't grow; the `metrics.json` files are kept.

## Known limitations
* Homepage and model layouts are unchanged in structure, so their first-viewport targets belong to Phases 2 and 3.
* Heatmap shading is still rank-based (that logic lives in protected `model.js`); a value-based scale and legend are planned for Phase 3.
* Favicon and share images still use the old blue (Phase 5, after design approval).
* The brand mark is still the original line icon; a signature device (the evidence-gap dumbbell) arrives in Phase 4.

## Decisions for you
1. Approve the two text changes and the two shortened desktop nav labels?
2. Proceed to Phase 2 (homepage, Concept B)?
