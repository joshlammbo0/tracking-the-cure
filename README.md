# Tracking the Cure

An auto-updating, investor-style tracker of progress toward a type 1 diabetes cure, T1D
medtech, and GLP-1 use in T1D. Every program is a structured record with a **stage**
grade, an **evidence** grade, a plain-English reality check, a next catalyst, and cited
primary sources. A daily job pulls ClinicalTrials.gov, PubMed, openFDA, SEC EDGAR, and
market data, and flags anything where the live data disagrees with the curated record.

Built by someone living with T1D. Not medical or investment advice.

## What's on the site

Every page is real static HTML with its own URL, title, description and share image.

| URL | What it shows | Live sources |
|---|---|---|
| `/` | Thesis, headline numbers, Cure Impact Model preview with investment implications, hype map, next catalysts, registry changes | all |
| `/model/` | **Cure Impact Model**: scenario presets, adjustable inputs, chart, year-by-year table, sensitivity grids, company read-across, CSV export, print layout, methodology | market sizes (cited), yfinance revenue |
| `/pipeline/`, `/programs/<id>/` | Every cure and GLP-1 program: grades, reality check, endpoints, trials, timeline, sources, headlines | ClinicalTrials.gov, PubMed, Google News |
| `/glp1/` | GLP-1 label check, tracked programs, every registered GLP-1-class trial in T1D | openFDA labels, ClinicalTrials.gov, PubMed |
| `/medtech/`, `/medtech/<category>/` | CGMs, pumps/AID, software, each with its live FDA decision feed | openFDA (510(k), De Novo, PMA) |
| `/companies/`, `/companies/<ticker>/` | Price chart, metrics, T1D exposure, linked programs and devices, recent SEC filings | yfinance, SEC EDGAR |
| `/catalysts/` + `/catalysts.ics` | Quarter-by-quarter timeline, sortable/filterable table, subscribable calendar | curated + registry + yfinance |
| `/research/` | Research notes generated from the tracked data (analysis, not advice) | all |
| `/methodology/`, `/about/` | Grading rubric, flag rules, source health; who built it and why | — |

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
```

```bash
.venv/bin/python -m pipeline.build --offline
```

```bash
.venv/bin/python -m pipeline.render
```

```bash
python3 -m http.server 8765 -d _site
```

Then open http://localhost:8765. `pipeline.build` refreshes `site/data/*.json`; `pipeline.render`
turns that data into the finished site in `_site/` (git-ignored). Drop `--offline` for a full
refresh from every live source (3–5 minutes, most of it the weekly source-link check). Other flags:

- `--skip news,links,markets`: skip specific sources (`ctgov, pubmed, openfda, sec, markets, news, links`).

Run the tests with `.venv/bin/python -m pytest -q`.

## Deploy (free, GitHub Pages)

1. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. **Settings → Secrets and variables → Actions**, and add:
   - `SEC_USER_AGENT`: `"Your Name your@email.com"`. SEC asks automated clients to identify themselves.
   - `NCBI_API_KEY` (optional): a free key from your NCBI account. It raises PubMed rate limits.
3. **Actions → Daily refresh & deploy** runs every day at 11:17 UTC: it refreshes the data,
   commits `site/data/*.json`, renders the site with `pipeline.render`, and deploys `_site/`.
   Any push that changes `data/`, `pipeline/`, `templates/` or `site/` also redeploys.
4. **Validate curated data** runs on every pull request: the tests, an offline build, and a full render.

## Update it

**Your personal notes** are the only thing you need to edit day to day: `data/my_notes.yaml`.

```yaml
devices:
  dexcom-g7:
    rating: 4
    user_take: "Day-1 readings run low for me; days 3–10 are excellent. Adhesive lasts with an overpatch."
programs:
  vertex-zimislecel:
    commentary: "I wouldn't trade insulin for lifelong immunosuppression, which is the adoption problem."
```

These render in amber callouts labeled *My take · personal perspective*. Keys must match an
`id` in `devices.yaml` or `programs.yaml`; the build fails loudly on a typo. Placeholder text
that starts with `(Placeholder` is hidden.

**Curated data** (when real news breaks):

- `data/programs.yaml`: cure and GLP-1 programs. Update `stage`, `evidence`, `status`, `summary`, `reality_check`, `sources`, and set `verified_on` to today. Any record older than 120 days gets a "re-verify" flag on the site.
- `data/devices.yaml`, `data/companies.yaml`, `data/catalysts.yaml`, `data/market.yaml`.
- `data/market.yaml` also holds the model's scenario presets (`scenarios:`); `data/companies.yaml` holds each company's revenue mix for the read-across (`exposure:`, with a basis and source).
- **About page** text lives in `templates/about.html`.

Rules the data follows: cite a source on every record. Never guess. Put anything you can't
confirm under `unverified:` and it shows as a flag. Leave `diabetes_rev_pct: null` unless a
filing supports it.

**What updates by itself:** trial status, phase, enrollment, and dates; the registry
change log (status changes and date slips); new GLP-1 trials in T1D; new FDA device
decisions; GLP-1 label wording; PubMed papers; headlines; prices, returns, market caps,
revenue, earnings dates; and SEC filings.

## Layout

```
data/              curated YAML (programs, devices, companies, catalysts, market, my_notes)
pipeline/          build.py (data refresh) + ctgov, pubmed, openfda, sec, markets, news
                   model.py (Cure Impact Model), render.py (static pages), charts.py (SVG), og.py (share images)
templates/         Jinja2 page templates; research/ holds the research notes
site/assets/       style.css (the design system), app.js, model.js, favicon, og/ (cached share images)
site/data/         JSON written by the daily job (committed by the bot)
tests/             pytest: validation, parsing, model, full render + link check
.github/workflows/refresh.yml   daily: refresh → commit data → render → deploy to Pages
.github/workflows/validate.yml  PR check: tests, offline build, render
DESIGN_NOTES.md    design critique, plan and decision log for the rebuild
```

**Model numbers** come only from `pipeline/model.py`. `site/assets/model.js` re-implements the
formula for the sliders and checks itself against the Python results on page load. If you change the
formula, change both, then update the pinned values in `tests/test_model.py`.

**Research notes** live in `templates/research/` and pull every number from the data, so they stay
current. Add one by writing a template and registering it in `NOTES` in `pipeline/render.py`.

**Share images** are drawn once into `site/assets/og/` and reused. Delete a PNG to redraw it.

## Data notes

- yfinance is an unofficial Yahoo Finance wrapper. Prices may be delayed, and it can break. When it fails, the site keeps the previous day's numbers and marks the source as stale.
- A registry "primary completion" date is not a results date. Sponsors often slip these, and the change log records every slip.
- News appears as headline links only; no article text is stored or shown.
