# Phase 3 report — Cure Impact Model page

*Branch `redesign/visual`, uncommitted. Compared against the frozen snapshot (`1c41b87`, 2026-10-26).*

## Decision 6 was not needed
`model.js` already exposes its calculation as `TTC.runModel`. The new visuals live in a separate display-only
script, **`site/assets/model-view.js`**, which reads the same inputs, calls `TTC.runModel`, and draws only into new
elements. **`model.js` is unchanged** (protected-file diff is empty), and every element ID it writes to is kept.

## What changed

| Area | Before | After |
|---|---|---|
| Header | 4-line lede, then 4 equal export buttons | Compact header: 2-line lede (same text), meta row with one **Export ▾** menu holding the same four actions |
| Scenarios | 4 pill chips on their own rows | **Segmented control** with the scenario description beside it on wide screens; a 2×2 grid below 1100 px |
| Answer row | 5 tiles inside the narrow outputs column | Same 5 tiles, full width, directly under the scenario (3 columns on tablets, 2 on phones) |
| Inputs | Left column | **Right column** (sticky) on desktop; below the answer on tablets and phones, as before |
| Chart | Displaced-by-market only | Toggle: **By market** (unchanged chart) / **In context** (the approved homepage chart, live-updating with the inputs) |
| Company read-across | Table only | **Bar chart** above the table: "Modelled displacement in 2040 relative to current company revenue", with the scenario named, "company shares held at today's levels", and pure-plays with an identical revenue mix drawn **once** (Pump pure-plays: Insulet, Tandem, Beta Bionics, MiniMed · CGM pure-plays: Dexcom, Senseonics). Lilly is listed as not modelled, not plotted. Table kept below. |
| Sensitivity | No legend | Legend under each grid: lightest → darkest value, "shading by rank within this grid" (the shading rule itself is unchanged; it lives in `model.js`) |
| Labels | Fixed "base case" | Chart legend and bar subtitle name the scenario shown ("bull case", "current inputs", …) |

`pipeline/render.py` (presentation only): builds the bar-chart categories from the existing read-across output and **asserts** that grouped pure-plays have identical results (a build fails rather than silently merging different numbers). It also adds `model-view.js` to the cache-busting list.

## Consistency checks (in-browser, bull preset, then a custom capacity of 60K)
| Check | Result |
|---|---|
| Bars vs read-across table (Insulet, Dexcom, Abbott, Novo) | 94.9% / 58.5% / 10.5% / 1.2%, identical in both |
| "In context" end label vs 2040 tile | $15.6B = $15.6B |
| Legend range vs heatmap cells | $2.5B – $17.0B, matches grid min / max |
| Custom inputs | Bars 38.7% = table 38.7%; context $6.4B = tile $6.4B; labels read "current inputs" |
| `TTC.modelCheck` (JS = Python) | ok |

## First-viewport results (Playwright, frozen data)

| Measure | Phase 2 | Phase 3 | Target |
|---|---|---|---|
| Model @1440×900: chart top | 923 px | **638 px** | ≤ 640 ✓ |
| Model @768×1024: chart top | 1,060 px | **892 px** | in first viewport ✓ |
| Model @375×812: answer tiles top | 1,547 px (chart) | **610 px** (tiles) | scenario + answer in first viewport ✓ |
| Model @375×812: chart top | 1,547 px | 1,264 px | (second screen; inputs follow) |
| Contrast failures / heading skips / overflow (all 72 configurations) | 0 / 0 / 0 | **0 / 0 / 0** | ✓ |
| Homepage metrics | 431 / 772 / 751 | unchanged | ✓ |

Model page height: +217 px @1440, +375 px @768, +622 px @375, from the bar chart, the context view and the legends.

## Numerical-integrity comparison
```
Model values changed: 0 · CSV changed: False
```
New text on the model page:
* **Recorded as approved (no new claims):**
  * The context chart's strings and values, identical to the approved homepage chart.
  * The bar values (20.9%, 10.6%, 1.9%, 1.8%, 1.6%, 0.3%, 0.1%), identical to the read-across table on the same page.
  * The legend values ($1.3B, $4.2B, $25.0B, $1.9T), identical to existing heatmap cells.
* **Pending your approval (the guard is blocking on these two):**
  1. Bar chart title: "Modelled displacement in 2040 relative to current company revenue"
  2. Bar chart caption: "Not modelled: Eli Lilly (revenue split not disclosed in the primary sources reviewed, or revenue outside the modelled markets). Model output, not a forecast of company revenue."
* **Also for approval** (no digits, so the guard doesn't track them):
  * Bar subtitle: "‹scenario› · company shares held at today's levels · companies with an identical modelled revenue mix are shown once"
  * Category labels "Pump pure-plays" and "CGM pure-plays"
  * Legend phrasing "Lightest … darkest · shading by rank within this grid"
  * Control labels "Export", "By market", "In context"
  * Scenario names used in labels ("base case", "bull case", "bear case", "immunosuppression-required case", "current inputs")

## Tests and protected files
* `pytest`: **40 passed**.
* `git diff` on `pipeline/model.py`, **`site/assets/model.js`**, `data/`, `site/data/`, `pipeline/build.py`, workflows, `tests/test_model.py`: **empty**.

## Screenshots
`docs/redesign/phase3/after/` (full page, 6 configurations each; git-ignored). The "before" set is `docs/redesign/phase2/after/`.

## Known limitations / remaining opportunities
* The preset-scenarios and read-across tables still scroll sideways inside their containers at 1440 (as before). A compact column set for those tables belongs in Phase 5.
* Heatmap shading remains rank-based (in protected `model.js`); the new legend makes that explicit. Value-based shading would need an approved `model.js` change.
* No new automated test checks model-view.js against the Python read-across. The in-browser checks above cover it for now; a Playwright test could pin it in Phase 5.

## Decisions for you
1. Approve the new model-page text listed above?
2. Proceed to Phase 4 (pipeline and the stage-vs-evidence dumbbell, reused on program pages)?
