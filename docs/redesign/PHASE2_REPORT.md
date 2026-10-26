# Phase 2 report — homepage, Concept B ("The long fuse")

*Branch `redesign/visual`, uncommitted. Compared against the frozen snapshot (`1c41b87`, 2026-10-26).*

## What changed

**Hero** (`templates/index.html`, `site/assets/style.css`)
* Approved H1: "A cure would rewrite a $48B market. The model says the revenue shifts slowly, and the strategic exposure starts long before."
* Left: the display figure **$3.2B** (accent colour) with its existing label "Revenue displaced in 2040, base case", the existing qualifier "3.5% of T1D-driven revenue · CGM, pumps & insulin · model output", the existing caveat "Model output under labelled assumptions, not a forecast.", the existing lede, and the primary action.
* Right: the **baseline-in-context chart**. T1D-attributable revenue in the no-cure baseline is drawn as a grey area ($17.9B in 2025 → $91.0B in 2040). The base-case displaced revenue is a highlighted area inside it ($3.2B in 2040). There's a dashed "Approval 2031 · assumption" marker and direct end labels. Both series are the same year and the same denominator, so the proportion is honest; nothing is placed in a pie or compared across years.
* Below: an **"Evidence today"** strip with the two existing evidence stats (15 active programs; 2 approved therapies) and the pipeline link, followed by the existing market-size source line.
* Phones: figure → qualifier → caveat → action → chart → lede. The order is done in CSS with no duplicated content, so visual order equals keyboard order. Phones get a separate narrow chart drawing, so labels stay legible.
* The rest of the homepage (model composition chart, implications band, hype map, catalysts, About strip) is unchanged.

**Chart** (`pipeline/charts.py`: new `context_area()`; `site/assets/app.js`: tooltip support)
* Hover and keyboard (← → Home End) tooltip for each year: displaced, baseline, **share displaced**. In 2040 it reads 3.5%, the same figure the model reports.

**Data plumbing** (`pipeline/render.py`, presentation only)
* Passes two **existing** `model.run()` base-case series (`t1d_baseline_total`, `displaced_total`) to the template. No calculation added or changed.
* New test `test_hero_chart_plots_model_outputs_unchanged` pins the plotted values to `model.run()` and checks displaced ≤ baseline every year.

## First-viewport results (Playwright, frozen data)

| Measure | Phase 1 | Phase 2 | Target |
|---|---|---|---|
| Home @1440×900: primary chart top | 1,225 px | **431 px** | < 900 (≤ 640) ✓ |
| Home @768×1024: primary chart top | 1,265 px | **772 px** | in first viewport ✓ |
| Home @375×812: hero figure bottom | not in hero | **397 px** | ≤ 812 ✓ |
| Home @375×812: chart top | 1,528 px | **751 px** | (begins in first viewport) ✓ |
| Contrast failures (all 72 configurations) | 0 | 0 | 0 ✓ |
| Heading skips | 0 | 0 | 0 ✓ |
| Horizontal overflow | 0 | 0 | 0 ✓ |
| Model JS = Python | ok | ok | ok ✓ |

Page height grew: +222 px @1440, +668 px @768, +675 px @375. The hero is larger and the homepage now has two charts: the context hero and the existing composition chart in section 01.

## Numerical-integrity comparison

```
Model values changed: 0 · CSV changed: False
```
Homepage text differences, all accounted for:
* **Approved by you:** new H1 (old H1 removed); baseline values $17.9B and $91.0B, axis ticks ($0–$100B; 2025/2030/2035/2040), the approval-2031 marker, and the $3.2B end labels.
* **Existing wording repeated in the hero:** "3.5% of T1D-driven revenue" and "Model output under labelled assumptions, not a forecast." Both already appear lower on the page.
* **Formatting only:** "CGM, pumps & insulin · model output" now follows a bold span, so it extracts as "· CGM, pumps & insulin · model output". The words are unchanged.

**Pending your approval (the guard is blocking on these three new strings):**
1. Chart title: "How much of T1D-driven revenue a cure displaces"
2. Chart subtitle: "Annual, US$, global CGM, pumps and insulin, 2025–2040"
3. Chart caption: "The grey area is revenue attributable to people with T1D if no cure arrives, using the model's labelled T1D-share assumptions; the highlighted area is the part the base-case cure displaces. Model output, not a forecast."

The legend labels "T1D-attributable revenue, no cure" and "Displaced by a cure, base case" contain no digits, so the guard doesn't track them; they're listed here for approval too.

## Tests and protected files
* `pytest`: **40 passed** (adds the hero-chart data test).
* `git diff` on `pipeline/model.py`, `site/assets/model.js`, `data/`, `site/data/`, `pipeline/build.py`, workflows, `tests/test_model.py`: **empty**.

## Screenshots
`docs/redesign/phase2/after/{page}-{1440|768|375}-{light|dark}.jpg` (full page; git-ignored). The "before" set is `docs/redesign/phase1/after/`.

## Known limitations / remaining opportunities
* **Two charts on the homepage.** The hero shows scale; section 01 shows composition by market. They complement each other, but the page is longer. In Phase 5 I'd suggest merging section 01 into a smaller "by market" breakdown under the hero.
* **The displaced band is deliberately thin.** That is the honest proportion. The model page (Phase 3) will add the "Displaced only" zoom proposed in the audit, for readers who want to see the shape.
* The OG share image still shows the old design (Phase 5, after approval).

## Decisions for you
1. Approve the chart title, subtitle, caption and legend labels above?
2. Proceed to Phase 3 (Cure Impact Model page)? Phase 3 may need decision 6 from the audit: one presentation-only event line in `model.js`. I'll ask before touching it.
