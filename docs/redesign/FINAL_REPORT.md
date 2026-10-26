# Visual redesign — final completion report

*Branch `redesign/visual` (from `main` at `1c41b87`). Completed 2026-10-26. Not merged, not deployed.*

## Commits
| Commit | Contents |
|---|---|
| `a45e9cc` | Phases 0–4: audit, safety net (numbers guard, screenshots/metrics, palette validator), tokens/type/chrome, homepage Concept B, model page, pipeline dumbbell |
| `4ed8d84` | Phase 5: company verdict strip, table fit, share images, favicon, README |
| *(final commit)* | Final regression audit script (`tools/audit.py`), audit results, this report, design-notes update |

Phases 0–4 share one commit because their changes were interleaved in the same files before the instruction to commit per phase arrived; each phase still has its own report (`docs/redesign/PHASE0_AUDIT.md` … `PHASE5_REPORT.md`).

**Not pushed.** This machine's command line has no GitHub credentials (GitHub Desktop holds them). Publishing steps are at the end of this report.

## What changed, in one page
* **Design system:** warm-paper light theme, deep-navy dark theme, one teal-blue accent kept for interaction, and data colours (indigo / amber / green) validated for AA contrast and colour-blind separation. New type scale with a display figure and tabular numbers; 12 px floor for UI text. 4 px radius, no pills.
* **Chrome:** one-line disclaimer (wording unchanged) and a 48 px masthead: 71 px total, from 95–122 px. Five primary links plus a More menu, visible from 760 px.
* **Homepage (Concept B):** approved headline; **$3.2B** display figure with its existing qualifier and caveat; a chart that draws displaced revenue *inside* the T1D-attributable baseline it's a share of ($17.9B → $91.0B, same year, same denominator); "Evidence today" strip.
* **Model page:** answer-first layout; Export menu; segmented scenarios; By-market / In-context chart views; company read-across bar chart (identical pure-plays drawn once, build fails if they ever differ); sensitivity legends. All new visuals are in display-only `model-view.js`; **`model.js` is untouched.**
* **Pipeline:** evidence-gap tracks (dot = results reported, ring = stage reached, dashed = gap) everywhere the block ladder was. Arrange by approach / stage / gap; matrix view.
* **Program pages:** verdict strip (stage · evidence · ahead of results · next catalyst), large track, reality check first.
* **Company pages:** verdict strip (market cap · diabetes % of revenue · cure exposure 2040).
* **Tables:** none scroll sideways at 1024 px or wider.
* **Share images:** navy theme; program images draw the program's real track.

## Before → after (frozen data; Playwright)
| Measure | Before | After |
|---|---|---|
| Homepage primary chart top @1440×900 | 1,265 px | **431 px** |
| Homepage key figure @375×812 | not in first screen | **397 px** |
| Model chart top @1440×900 | 955 px | **638 px** |
| Model answer tiles @375×812 | 1,577 px (chart) | **610 px** |
| Chrome height (1440 / 768 / 375) | 95 / 122 / 95 | **71 / 71 / 71** |
| Text below WCAG AA (72 representative configurations) | 48 | **0** |
| Heading-level skips | 30 | **0** |
| Tables scrolling sideways @1440 / @1024 | 2 / 3 | **0 / 0** |

## Final regression audit
* **All pages:** 55 pages × 1440/768/375 × light/dark = **330 configurations, 0 issues** (console errors, failed requests, horizontal overflow, AA contrast, heading order). Run on both the frozen snapshot and **fresh live data** (full pipeline run 2026-10-26, all sources refreshed, no failures). Results: `docs/redesign/final/audit.json`.
* **Interactions: 13/13 pass:**
  * theme toggle persists
  * More menu and Escape
  * mobile menu
  * homepage chart keyboard tooltip (2040: $3.2B of $91.0B, 3.5%)
  * model JS = Python for all presets
  * presets update tiles to the Python values
  * sliders keep tiles, context chart, bars and table in sync
  * chart view toggle
  * Export → CSV download
  * print stylesheet
  * pipeline arrange, matrix and regroup
  * companies filter and sort
  * catalysts table open and filter
* **Calculations:** numbers guard **0 model-value changes, CSV byte-identical**, 0 removed figures or caveats; every displayed-text addition is listed in `docs/redesign/approved_changes.yaml`.
* **Tests:** `pytest` **40 passed** (32 original plus guard, presentation and hero-chart tests). Offline build passes. `python -m tools.palette` passes.
* **Protected files:** `pipeline/model.py`, `site/assets/model.js`, `data/`, `site/data/`, `pipeline/build.py` and ingestion modules, `.github/workflows/`, `tests/test_model.py`: **unchanged** across the whole branch.
* **Daily refresh:** the Action's steps are unchanged; render uses only production dependencies (Jinja2, Pillow); new dev tools (`requirements-dev.txt`: pytest, Playwright) are never used by it. The branch doesn't touch `site/data`, so it won't conflict with the bot's daily commits.

## Decisions made without your review (autonomous mode)
1. **Pipeline explainer rewritten** for the new encoding (the old "outline / fill" sentence no longer matched the chart). It keeps the approved "stage reached" vs "results reported" distinction and makes no efficacy claim.
2. **New short labels:** "By approach", "By stage", "By gap", "Tracks", "Matrix", "Gap" (legend key).
3. **Matrix intro sentence** on the pipeline page.
4. **Program verdict strip:** reuses existing labels; the next catalyst moved from the sidebar into it (nothing removed).
5. **Company verdict strip** qualifier: "base case · % of current revenue · model output".
6. **Share images:** program images show that program's own track; all other images show none, so no image implies data it doesn't have.
7. **Not merged on purpose:** the homepage's two charts (hero context chart and section-01 composition chart). Merging them would remove displayed figures.
8. **Commit granularity:** phases 0–4 in one commit (see Commits).

## Remaining issues (none blocking)
* At 768 px, six dense registry tables (GLP-1 trial scan, a few program trial tables, model read-across) still scroll 8–88 px inside their own scroll containers. The page itself never scrolls sideways.
* Heatmap shading is rank-based (logic in protected `model.js`); the new legend states it plainly. Value-based shading would need an approved `model.js` change.
* Pipeline overview starts in the second screen on phones (1,070 px), after the controls and explainer.
* The browser-side read-across (`model-view.js`) is verified by the audit's sync check rather than a unit test against Python.
* The brand mark is still the original line icon (the share images carry the track device).

## How to publish (GitHub Desktop)
1. Open GitHub Desktop: the current branch is **redesign/visual** with these commits. Click **Publish branch**.
2. Click **Create Pull Request** (opens GitHub). The PR runs **Validate curated data** (tests, offline build, render).
3. Review the PR. To deploy, **merge it into `main`**: the existing daily workflow renders and deploys on that push.
4. To preview locally before merging: `.venv/bin/python -m pipeline.render` then `python3 -m http.server 8765 -d _site`.
