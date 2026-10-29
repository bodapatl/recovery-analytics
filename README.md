# Collections Recovery Forensics — “Is the reported +11% MoM real?”

Assignment submission: determine what actually happened to collections recovery
over ~12 months of messy, contradictory multi-system data — and decide where ₹10
Cr should go.

**Verdict: the reported improvement is not real.** True trend is
**+0.023 ₹Cr/month (p = 0.88 — statistically flat)**; the quoted +11% is exactly
the Feb→Mar bounce (+11.1%, gold definition), reversed by April (−7.3%). Several
upstream errors manufacture optimism: **₹2.59 Cr** of double-posted payments, a
"KEPT" promise rate reported at ~18–19% but cash-verified at **~3.6%**, 56% of
calls in wrong hour buckets, and attribution logic that drifts **₹0 → ₹10.95
Cr/month** onto stale touches by July.

Full story: [`reports/executive_memo.md`](reports/executive_memo.md) (2 pages) ·
dashboard: [`dashboard/index.html`](dashboard/index.html) ·
data quality: [`reports/data_quality_report.md`](reports/data_quality_report.md) ·
production design: [`reports/production_design.md`](reports/production_design.md).

## What was built

| assignment deliverable | artifact |
|---|---|
| SQL repository (cleaning, transforms, metrics, analytics) | `sql/01_staging.sql` `02_clean.sql` `03_golden.sql` `04_forensics.sql` (DuckDB, pure SQL, deterministic) |
| Golden dataset / pipeline | `data/golden/*` (parquet + CSV exports) built by `src/pipeline.py` from SQL only |
| Analysis notebook (reasoning, not just charts) | `analysis/analysis_notebook.ipynb` (executed) |
| Data quality report with detection + treatment + impact | `reports/data_quality_report.md` (auto-generated from `dq_*`/`fore_*` tables) |
| Executive dashboard (one screen, decision-first) | `dashboard/index.html` (+ `data.js` export current as of last run) |
| Executive memo (≤2 pages) | `reports/executive_memo.md` |
| Architecture diagram | `architecture/architecture_diagram.svg` (+ mermaid in this README) |
| Statistical investigation | `src/analysis.py` → `reports/analysis_summary.json` (mix/rate decomposition, cohort, Simpson-style channel check, survivorship, attribution-window bias, trend test) |
| Counterfactual (targeting change) | exact-matched DiD inside `src/analysis.py` + notebook §3 |

## The data

`data/raw/` holds the 17 published datasets (30k accounts; calls, attempts,
dispositions, WhatsApp/SMS, field visits, PTP, payments, vendors, status
history, complaints, targeting, sessions, agents, borrowers, campaigns — plus
the vendor data dictionary). Known injected hazards: duplicates, missing values,
conflicting timestamps (3 timezones), inconsistent ids, late-arriving events,
schema/disposition-code changes, duplicate payment events, overwritten status
history, agent identity chaos — all handled with documented, quantified rules.

## Key forensic findings (numbers from the golden layer)

1. **Duplicate payments** — 500 `payment_id`s filed twice; 346 ids carry two
   SUCCESS copies → **₹2.59 Cr** phantom cash. Separately, 1,782 payment
   references are *re-used* for different payments — not duplicates, but they
   poison any join keyed on `payment_reference` (flagged, not deleted).
2. **PTP kept is fiction** — 4,309 of 4,483 "KEPT" promises have zero cash
   behind them; verified kept rate ≈ **3.6%**, not ~19%.
3. **Timezone chaos** — 55.7% of calls misclassified into wrong business-hour
   buckets until row-level tz normalization (UTC/Kolkata/Dubai).
4. **Attribution drift** — legacy "latest touch, unbounded window" credits
   **₹10.95 Cr/month** to touches >30 days old by July vs ~₹2.6 Cr under the
   golden 14-day rule; ~87% of payments are un-attributable under a sane window
   at all → campaign league tables are noise.
5. **Identity resolution** — agents master holds ~30 conflicting rows per real
   agent (1,000 canonical agents; 255 employee_codes claimed by ≥2 agents);
   borrowers written 3× (30,600 rows → 11,015 canonical).
6. **No portfolio mix story** — cohort × band mix/rate decomposition ≈ ₹0;
   recovery per origination-cohort is stable. *(Hypothesis rejected.)*
7. **Strategy change didn't move cash** — exact-matched DiD = **+₹895 per
   targeted account/month (≈+5.6%, n.s.)**; counterfactual Jan–Jul without the
   change ≈ ₹17.8 Cr/month vs ~₹18–19 Cr actual.

## Where the ₹10 Cr goes

**WhatsApp / digital engagement scaling** — the only channel with a genuine,
cash-backed upward share trend (2.5% → 3.3%+), at ~50× lower unit cost than
voice. Estimate: **₹13.2 Cr/yr incremental**, **₹3.5–4.0 Cr** cost, **≈3.8×
ROI**, **≈3.2-month break-even**, downside ≈ ₹6 Cr/yr (1.7×) if click-to-pay
halves at scale. Confidence medium-low — a 2-month geo-split test before
scaling past ₹4 Cr is part of the recommendation. Sequencing: fix measurement
first (free), scale digital second, hold the remaining budget until the split
test reads out.

## How to run (reproducible)

```bash
pip install -r requirements.txt
python run_all.py          # raw -> staging -> clean -> golden -> reports -> dashboard data -> notebook
```

Outputs land in `data/golden/`, `reports/`, `dashboard/data.js`, and the
re-executed notebook. The dashboard is a static page — open
`dashboard/index.html` in a browser; no server needed.

### Repo layout

```
recovery-analytics/
├── data/raw/                     # published CSVs (immutable inputs)
├── data/golden/                  # generated golden artifacts (parquet/CSV)
├── sql/                          # the SQL repository (staging→clean→golden→forensics)
├── src/                          # pipeline, forensics, analysis, dashboard export, notebook builder
├── analysis/analysis_notebook.ipynb
├── reports/                      # dq report · exec memo · analysis summary · production design
├── dashboard/                    # single-screen executive dashboard
├── architecture/                 # production architecture diagram
└── run_all.py
```

### Production architecture (summary)

```
RAW (17 sources, append-only + _ingested_at)
  → STAGING (typed views, tz→UTC→IST)          [01_staging.sql]
  → CLEAN   (dedup · entity resolution · tz)   [02_clean.sql]
  → GOLDEN  (marts + attribution + verified PTP) [03_golden.sql]
  → METRICS (month marts, funnel + rates)
  → DASHBOARD / ALERTS (anomaly monitors, DQ gates)
```

Full engineering design: [`reports/production_design.md`].

## Documented assumptions (disclosed, not hidden)

- Business clock = Asia/Kolkata; months are IST months.
- Recovery = deduplicated SUCCESS cash in the month it landed.
- Denominators = every account opened ≤ month end (survivorship-proof).
- `agent_id` is the canonical agent key; masters resolve to it.
- PTP "kept" counts only when verified by cash within the promise window.
- No cost table exists in the source contract — cost params are explicit
  assumption knobs in `src/config.py` (₹110/agent-hr, ₹0.45/attempt, ₹0.20/msg).

## Classification discipline used everywhere

**Fact** (row-level deterministic evidence) / **Strong evidence** (mechanism
verified against control groups) / **Correlation** (no clean identification) /
**Hypothesis** (injected and tested, rejected where noted). The memo maps every
major claim to one of these.
