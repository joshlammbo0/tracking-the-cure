# Tracking the Cure

An auto-updating, investor-style tracker of progress toward a type 1 diabetes cure, T1D
medtech, and GLP-1 use in T1D. Every program is a structured record with a **stage**
grade, an **evidence** grade, a plain-English reality check, a next catalyst, and cited
primary sources. A daily job pulls ClinicalTrials.gov, PubMed, openFDA, SEC EDGAR, and
market data, and flags anything where the live data disagrees with the curated record.

Built by someone living with T1D. Not medical or investment advice.

## What's on the site

| Page | What it shows | Live sources |
|---|---|---|
| Overview | KPIs, hype map (stage vs. evidence), next catalysts, registry change log | all |
| Cure pipeline | Cell replacement, gene-edited/immune-evasive, encapsulation, immune therapies | ClinicalTrials.gov, PubMed, news headlines |
| Medtech | CGMs, pumps, AID, with your "user's take" + a live FDA decision feed | openFDA (510(k), De Novo, PMA) |
| GLP-1s in T1D | Add-on trials, beta-cell preservation, safety, label check, market angle | ClinicalTrials.gov scan, PubMed, openFDA drug labels, yfinance |
| Catalysts | Sortable calendar: readouts, launches, conferences, earnings | curated + registry dates + yfinance |
| Companies | Ticker, market cap, returns, TTM revenue, diabetes % of revenue, latest filing | yfinance, SEC EDGAR |
| Cure impact model | Adjustable "what if a functional cure works?" model for CGM / pump / insulin | cited market sizes |
| Methodology | Grading rubric, flag rules, per-source refresh health | — |

## Run it locally

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m pipeline.build
```

```bash
python3 -m http.server 8765 -d site
```

Then open http://localhost:8765. A full refresh takes about 3–5 minutes, most of it the
weekly source-link check. Useful flags:

- `--offline`: no network. Re-renders from the YAML files and the last fetched JSON (fast; use it after editing notes).
- `--skip news,links,markets`: skip specific sources (`ctgov, pubmed, openfda, sec, markets, news, links`).

## Deploy (free, GitHub Pages)

1. Create a GitHub repo and push this folder to `main`.
2. In the repo: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
3. **Settings → Secrets and variables → Actions**, and add:
   - `SEC_USER_AGENT`: `"Your Name your@email.com"`. SEC asks automated clients to identify themselves.
   - `NCBI_API_KEY` (optional): a free key from your NCBI account. It raises PubMed rate limits.
4. **Actions → Daily refresh & deploy → Run workflow** once. After that it runs every day at
   11:17 UTC, commits the refreshed `site/data/*.json`, and redeploys. Any push that changes
   `data/`, `pipeline/` or `site/` also redeploys.

The site is fully static (no build step, no framework), so it also works on Vercel or
Netlify with `site/` as the output directory. Run the pipeline there with a scheduled job,
or keep the GitHub Action and point the host at the repo.

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

These render in yellow boxes labeled *My take · personal perspective*. Keys must match an
`id` in `devices.yaml` or `programs.yaml`; the build fails loudly on a typo. Placeholder text
that starts with `(Placeholder` is hidden.

**Curated data** (when real news breaks):

- `data/programs.yaml`: cure and GLP-1 programs. Update `stage`, `evidence`, `status`, `summary`, `reality_check`, `sources`, and set `verified_on` to today. Any record older than 120 days gets a "re-verify" flag on the site.
- `data/devices.yaml`, `data/companies.yaml`, `data/catalysts.yaml`, `data/market.yaml`.

Rules the data follows: cite a source on every record. Never guess. Put anything you can't
confirm under `unverified:` and it shows as a flag. Leave `diabetes_rev_pct: null` unless a
filing supports it.

**What updates by itself:** trial status, phase, enrollment, and dates; the registry
change log (status changes and date slips); new GLP-1 trials in T1D; new FDA device
decisions; GLP-1 label wording; PubMed papers; headlines; prices, returns, market caps,
revenue, earnings dates; and SEC filings.

## Layout

```
data/            curated YAML (programs, devices, companies, catalysts, market, my_notes)
pipeline/        Python: ctgov, pubmed, openfda, sec, markets, news → build.py
site/            static frontend (index.html, assets/, data/*.json written by the pipeline)
.github/workflows/refresh.yml   daily cron: refresh → commit → deploy to Pages
.github/workflows/validate.yml  PR check: offline build validates YAML + note keys
```

## Data notes

- yfinance is an unofficial Yahoo Finance wrapper. Prices may be delayed, and it can break. When it fails, the site keeps the previous day's numbers and marks the source as stale.
- A registry "primary completion" date is not a results date. Sponsors often slip these, and the change log records every slip.
- News appears as headline links only; no article text is stored or shown.
