# Phase 4 report — Pipeline and the stage-vs-evidence "dumbbell"

*Branch `redesign/visual`. Compared against the frozen snapshot (`1c41b87`, 2026-10-26).*

## What changed
* **Evidence-gap track replaces the block ladder everywhere it appeared** (homepage preview, pipeline overview, program cards, program pages) via the shared `ladder()` macro in `templates/_macros.html`:
  * filled dot = highest stage with reported results
  * open ring = furthest stage reached
  * dashed segment = stages reached without reported results
  * discontinued programs are grey and struck through, with "discontinued" written out

  Shape carries the meaning, not colour; ink colours keep the accent reserved for interaction; forced-colours mode is supported.
* **Pipeline page** (`templates/pipeline.html`, `site/assets/app.js`):
  * Arrange controls: **By approach** (default, grouped), **By stage**, **By gap**. Discontinued programs always sort last.
  * View toggle: **Tracks / Matrix**. The matrix is the stage × evidence grid from the research note, active programs only, as a reusable `stage_matrix` macro.
  * On phones the stage header stays visible while scrolling (sticky).
* **Program pages** (`templates/program.html`): a **verdict strip** under the title (Stage reached · Evidence read out · Ahead of results · Next catalyst), a large single-row track, and the **Reality check moved above the Summary**. The next catalyst moved from the sidebar into the strip; nothing was removed.

## Verification
| Measure | Phase 3 | Phase 4 | Target |
|---|---|---|---|
| Pipeline @1440: viz header top / first track row | 728 | 771 / ≈830 | first row in first viewport (900) ✓ |
| Pipeline @768: viz header top | 722 | 791 | first row in first viewport (1024) ✓ |
| Pipeline @375: viz header top | 972 | 1,070 | (controls added; second screen) |
| Program @1440: reality check | below fold | **above fold** | ✓ |
| Contrast fails / heading skips / overflow (72 configurations) | 0 / 0 / 0 | **0 / 0 / 0** | ✓ |
| Homepage first-viewport metrics | 431 / 772 / 751 | unchanged | ✓ |
| `TTC.modelCheck` | ok | ok | ✓ |
| Arrange/matrix interactions (scripted) | — | gap and stage sorts correct; groups hidden and restored; matrix view toggles | ✓ |

**Numbers:** model values changed 0, CSV unchanged, **0 removals**, 48 moves. The 30 additions all re-display existing data:
* the "Ahead of results" values (+1, +2, 0) on program pages, which already appear in the hype map
* grade labels and program names in the pipeline matrix view, the same content as the research note's matrix

Recorded in `approved_changes.yaml` (autonomous decision, see below).

**Tests:** 40 passed. **Protected files:** unchanged.

## Decisions made without review (autonomous mode, conservative)
1. **New explainer copy** for the new encoding, replacing the earlier "outline / fill" sentence, which no longer described the chart: "Filled dot: the highest stage at which a program has reported results (a dot at Preclinical means no human results yet). Open ring: the furthest stage it has reached. The dashed line, and the number on the right, are the stages reached without reported results." It keeps the earlier approved distinction between "stage reached" and "results reported" and claims nothing about efficacy.
2. Legend labels reused verbatim from the approved legend; one new key item, "Gap".
3. Control labels: "By approach", "By stage", "By gap", "Tracks", "Matrix".
4. Matrix intro sentence: "Active programs only. Shaded diagonal: evidence matches stage. Cells to the right of it are stages reached without reported results; grey cells are impossible."
