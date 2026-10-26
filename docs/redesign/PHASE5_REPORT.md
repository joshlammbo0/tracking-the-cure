# Phase 5 report — remaining pages, share images, documentation

*Branch `redesign/visual`. Autonomous phase (owner instruction of 2026-10-26). Compared against the frozen snapshot.*

## What changed
| Area | Change |
|---|---|
| Company pages | **Verdict strip** under the price: Market cap · Diabetes % of revenue · Cure exposure, 2040 (base case · % of current revenue · model output). The existing Key metrics and T1D exposure sections are unchanged below. |
| Tables (site-wide) | Column headers may wrap and numbers stay on one line, with tighter cell padding below 1100 px. The **preset-scenarios table** moved to a full-width block under the model (content identical). |
| Share images | All 55 redrawn in the navy theme. **Program images now draw that program's actual evidence-gap track** (from its own grades); other pages carry no track, so no image implies data it doesn't have. |
| Favicon | SVG and ICO in the teal-blue accent. |
| README | New "Design checks" section (numbers guard, screenshots/metrics, palette validator, render flags, styleguide); layout section updated. |
| Other pages | Catalysts, GLP-1, medtech, research, methodology and About inherit the new tokens, type and chrome; checked visually with no page-specific changes needed. |

## Horizontal scrolling inside tables (measured on all 56 pages)
| Width | Before Phase 5 | After |
|---|---|---|
| 1440 | 1 page (model: 2 tables) | **0** |
| 1024 | 1 page (model: 3 tables) | **0** |
| 768 | 19 pages | 6 pages (dense registry tables: 8–88 px inside their own scroll containers; the page itself never scrolls sideways) |

## Verification (frozen data)
* Numbers: model values changed **0**, CSV unchanged, **0 removals**. Additions are the company verdict strip only (labels approved on the Companies page; values repeated from the same page). Recorded in `approved_changes.yaml`.
* 72 page/size/theme configurations: **0** contrast failures, **0** heading skips, **0** overflow; `TTC.modelCheck` ok.
* `pytest`: 40 passed. Protected files: unchanged.

## Decisions made without review
1. Company verdict strip wording: "base case · % of current revenue · model output".
2. Share images: real per-program tracks on program pages only; the generic track was removed from all others.
3. Not done on purpose: merging the homepage's two charts (hero context chart + section 01 composition chart). Merging would remove displayed figures; left for your call.
