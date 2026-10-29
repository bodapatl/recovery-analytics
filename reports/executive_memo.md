# Executive Memo — Collections Recovery Review

**To:** Leadership · **From:** Data Analyst (assignment deliverable) · **Date:** 2026-10-28
**Question reviewed:** *"Recovery has improved by 11% month-on-month."*

---

## 1. What happened?

**The reported improvement is not real.** Rebuilt from a cleaned, deduplicated,
timezone-normalized "golden" dataset (639k raw rows → audited golden layer):

| metric (full months, Jan–Jul 2026) | reported view | golden view |
|---|---:|---:|
| Recovery recorded | ₹129.3 Cr (SUCCESS incl. doubles) | **₹126.9 Cr** |
| All positions incl. PENDING+REVERSED | ₹157.2 Cr phantom "book" | excluded — not cash |
| True MoM trend (OLS, n=7) | “+11% MoM” | **+0.023 ₹Cr/month, 95% CI [−0.37, +0.42], p = 0.88 (no detectable trend)** |
| The famous +11% | — | the **Feb→Mar bounce (+11.1%)**, which **reversed to −7.3%** in April |

Performance changed **when** it didn't: there is no trend. Recovery oscillates
between ₹17.0–18.9 Cr/month with 0 cohorts, 0 channel-mix and 0 agent-productivity
trends explaining a genuine lift (mix×rate decomposition ≈ ₹0.0 Cr).

**Where cash actually moves:** attributed voice recovery is flat
(₹17.4 → ₹16.9 Cr, noisy); WhatsApp-attributed cash quietly **doubles its share**
(2.5% → 3.3%; click-to-pay funnel healthy); agent-hour productivity is flat
(₹16.4–17.0k/hr) — no agent story.

## 2. Why does the number look better than reality?

| # | mechanism | evidence | class |
|---|---|---|---|
| 1 | **Duplicate payment posting** — 500 payment ids filed twice; 346 carried double SUCCESS rows | ₹2.59 Cr phantom cash (~4–5%/mo) | **Fact** |
| 2 | **Broken payment attribution** — "latest touch, unbounded window" drifts onto old touches | stale-touch credit grows ₹0 → **₹10.95 Cr/mo by Jul**; only **12.4%** of cash attributable under a sane 14-day window (9.3–14.6%/mo) | **Strong evidence** |
| 3 | **PTP "kept" is not cash** — 4,309 of 4,483 KEPT promises have zero payment behind them | reported kept ≈18–19% vs **≈3.6–3.7%** verified | **Fact** |
| 4 | **Timezone misclassification** — UTC / Kolkata / Dubai naive timestamps mixed | **55.7%** of calls land in wrong business-hour buckets | **Fact** |
| 5 | **Denominator games** — contacted accounts (1.2× the target list) as denominator; accounts never silently dropped | golden pool fixed at ₹1,048.9 Cr outstanding, survivorship-proof | **Strong evidence** |
| 6 | Portfolio mix / cohort change | decomposition ≈ 0; no new-portfolio footprint | Hypothesis **rejected** |
| 7 | Strategy-version campaigns made ops better | DiD (below): no lift over matched controls | Correlation, weak |

## 3. Is the reported 11% real? — No. Actual: **+0.0% MoM (±4%)**

Our independent definitions (recovery = deduped SUCCESS cash in IST month;
denominator = all accounts opened ≤ month end; PTP kept only when verified by
cash within window; attribution = last RPC ≤14d → last contact ≤7d → unattributed)
show a **statistically flat** series: OLS slope **+0.023 Cr/month, 95% CI
[−0.37, +0.42] Cr/mo, p = 0.88, n = 7 months**. Any variant of the "reported"
definition that was checked (SUCCESS-only, +PENDING, +REVERSED, per-contacted
account) produces the same verdict: the +11% is a one-month bounce, not a trend.
Leave-one-out sensitivity: dropping any single month leaves the slope between
−0.09 and +0.16 Cr/mo (all p > 0.4) — the flat verdict is not driven by one
outlier. **Caveat: n = 7 gives low power — "no detectable trend" is not proof
that nothing changed; it is proof that the specific +11%-MoM claim has no
evidence.** A "+11% MoM" sustained claim would need a slope of ≈ +2.1 Cr/mo —
far outside the CI. Attribution coverage of golden cash: **12.4% average
(9.3–14.6% by month)**.

## 4. Counterfactual — what if the mid-year targeting change had not happened?

Design: treatment = accounts first targeted under the modern (v2/v3) strategy
after Mar-2026; control = accounts still targeted only by legacy/v1 strategies;
exact matching on risk_segment × DPD-band × loan_type (80 matched cells);
outcome = ₹ recovery per targeted account per month, pre (Jan–Mar) vs post
(Apr–Jul).

**Result:** treatment +₹22,709 vs control +₹21,967 per account/month after the
change → **DiD = +₹895/account/month (≈ +5.6%), 95% CI [−₹1,224, +₹3,013],
p = 0.40 — no detectable lift** (cell-level dispersion, df = k−1; conservatively
labeled exploratory). **Pre-trend check:** Jan–Mar per-account slopes are similar
across arms (legacy −₹91, modern_early −₹55, modern_late +₹427/mo — the late-arm
slope is not significant at p = 0.13 and is flagged). The counterfactual recovery
without the change ≈ **₹17.8 Cr/month** against ~₹18–19 Cr actual — **the
strategy change did not move cash.** Limitations: strategies run concurrently
(not randomized), exact matching is discrete, no spillover control. A geo-split
rollout would identify this cleanly.

## 5. What should we do — and where does the ₹10 Cr go?

**Recommendation: Option 5 — WhatsApp / digital engagement, as the single
primary investment.** It is the only channel with a genuine, cash-backed upward
drift (2.5% → 3.3% share at constant click-to-pay conversion) and a ~10³-lower
unit cost than voice. The **AI voice concierge is an implementation lever
inside option 5** (it raises response rates), not a separate investment. All six
options below are priced on one consistent model; the runner-ups are deferments,
not rejections — each gets a named test before spend.

**Measured WhatsApp funnel:** ~1,400 msgs/mo → ~94% pay-click (synthetic
lifecycle ceiling; conservative case assumes it halves) → **₹0.55 Cr attributed
cash/mo ≈ ₹3,930 per sent message**.

| # | option | cost | incr. ₹Cr/yr (cons/base/upside) | ROI base | B/E base | call |
|---|---|---:|---|---:|---:|---|
| 1 | Telephony infrastructure upgrade | ₹2.0 Cr | 0.5 / 1.5 / 3.0 | 0.8× | 16 mo | **defer** — vendor connect-rate spread only ~2.3 pp, no elasticity in data (Hypothesis) |
| 2 | More agents / capacity | ₹3.5 Cr | 1.0 / 4.0 / 8.0 | 1.1× | 10.5 mo | **defer** — agent-hour productivity flat ₹16.4–17.0k/hr; ramp-up needs a randomized headcount pilot |
| 4 | Better targeting / data | ₹1.5 Cr | 0.0 / 1.5 / 4.0 | 1.0× | 12 mo | **defer — the DiD above is null** (+₹895, CI straddles 0); run geo-split first |
| 3 | AI voice concierge | ₹2.5 Cr | 1.0 / 3.0 / 5.0 | 1.2× | 10 mo | **defer as standalone — folded into option 5's build** |
| **5** | **WhatsApp / digital engagement** | **₹3.5 Cr** | **5.9 / 13.2 / 16.5** | **3.8×** | **3.2 mo** | **INVEST ₹3.5 Cr now; hold remainder for geo-split** |
| 6 | Field-operations expansion | ₹4.0 Cr | 1.0 / 2.0 / 4.0 | 0.5× | 24 mo | **defer** — no per-visit cost source in contract; ROI unsizable |

Options 1, 2, 3, 4, 6 are transparent scenario judgments — the contract data
contains no cost table and no identified elasticity for them (that *is* the
finding); option 5's numbers are data-derived. Cash timing: base-case
break-even ≈ **3.2 months** steady-state (≈ 3.2–4 with the 2-month ramp; costs
are ~90% fixed, so cash-positive early). Downside: conservative case ≈ ₹5.9 Cr
— still break-even-positive once most of the ₹3.5 Cr is fixed cost.

| item | estimate |
|---|---:|
| Expected incremental recovery (yr 1, base) | **₹13.2 Cr** (3× reach at constant click-to-pay; conservative ₹5.9 Cr, upside ₹16.5 Cr) |
| Cost to deploy | **₹3.5–4.0 Cr** (provider, AI voice-to-WA concierge, ops) |
| Expected ROI | **≈ 3.8×** (conservative ≈ 1.7×) |
| Break-even | **≈ 3.2 months** (+~1 mo for ramp) |
| Key assumptions | conversion holds at 3× reach; no cannibalisation of voice cash; SPL templates + 10-min response SLA |
| Confidence | **medium-low** — attribution coverage is only **12.4% of cash (9.3–14.6%/mo)**; run a 2-month geo-split test before scaling beyond ₹4 Cr |

**Sequencing:** 1) fix measurement (dedup at ingestion, IST normalization,
14-day attribution rule, PTP=verified-cash only) — free, immediate; 2) ₹3.5 Cr
WhatsApp scale + AI concierge; 3) hold the remaining ₹6.5 Cr until the geo-split
test reads out.

**Expected financial impact of fixing measurement alone:** reported recovery
would drop ~2% (doubles removed) but forecast accuracy and per-channel
deployment decisions improve materially; ₹10.95 Cr/month of mis-credited
recovery currently makes campaign league tables random noise.

## 6. How confident are we?

- Facts (duplicates, PTP-without-cash, tz): built from deterministic row-level
  evidence — **high confidence**. Every headline number now reconciles against
  16 automated tests (`src/verify.py` → `reports/verify_report.md`), including a
  clean-rebuild-from-scratch determinism check: **raw SUCCESS − golden = ₹2.5902
  Cr == the double-posted amount, exactly, all-time; the full-month ₹2.4468 Cr
  gap is the same rule minus the excluded August partial month.**
- Flat-trend verdict: OLS on 7 monthly points, slope +0.023 Cr/mo, 95% CI
  [−0.37, +0.42], p = 0.88, robust to leave-one-out — **high confidence in the
  specific rejection of "+11% MoM"**, and honest again: n = 7 buys limited
  power, so we claim "no detectable trend", not "proved nothing improved".
- Strategy-change effect (DiD): CI straddles zero — **exploratory; treat as
  null pending a geo-split**.
- Investment sizing: **medium-low** — honest interval ₹6–13 Cr incremental;
  the two-month split test is the cheapest way to buy certainty.

*Deliverables: golden dataset + pipeline (data/golden), SQL repository (sql/),
forensics notebook (analysis/), data-quality report (reports/),
metric-definition registry (reports/metric_definitions.yml), driver matrix
(reports/driver_matrix.md), reproducibility report (reports/verify_report.md),
single-screen dashboard (dashboard/index.html), production design
(reports/production_design.md), architecture diagram (architecture/).*
