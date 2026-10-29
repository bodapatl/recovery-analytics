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
| True MoM trend (OLS) | “+11% MoM” | **+0.023 ₹Cr/month, p = 0.88 (flat)** |
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
| 2 | **Broken payment attribution** — "latest touch, unbounded window" drifts onto old touches | stale-touch credit grows ₹0 → **₹10.95 Cr/mo by Jul**; ~87% of cash un-attributable under a sane 14-day window | **Strong evidence** |
| 3 | **PTP "kept" is not cash** — 4,309 of 4,483 KEPT promises have zero payment behind them | reported kept ≈18–19% vs **≈3.6–3.7%** verified | **Fact** |
| 4 | **Timezone misclassification** — UTC / Kolkata / Dubai naive timestamps mixed | **55.7%** of calls land in wrong business-hour buckets | **Fact** |
| 5 | **Denominator games** — contacted accounts (1.2× the target list) as denominator; accounts never silently dropped | golden pool fixed at ₹1,048.9 Cr outstanding, survivorship-proof | **Strong evidence** |
| 6 | Portfolio mix / cohort change | decomposition ≈ 0; no new-portfolio footprint | Hypothesis **rejected** |
| 7 | Strategy-version campaigns made ops better | DiD (below): no lift over matched controls | Correlation, weak |

## 3. Is the reported 11% real? — No. Actual: **+0.0% MoM (±4%)**

Our independent definitions (recovery = deduped SUCCESS cash in IST month;
denominator = all accounts opened ≤ month end; PTP kept only when verified by
cash within window; attribution = last RPC ≤14d → last contact ≤7d → unattributed)
show a **statistically flat** series (p = 0.88). Any variant of the "reported"
definition that was checked (SUCCESS-only, +PENDING, +REVERSED, per-contacted
account) produces the same verdict: the +11% is a one-month bounce, not a trend.

## 4. Counterfactual — what if the mid-year targeting change had not happened?

Design: treatment = accounts first targeted under the modern (v2/v3) strategy
after Mar-2026; control = accounts still targeted only by legacy/v1 strategies;
exact matching on risk_segment × DPD-band × loan_type (80 matched cells);
outcome = ₹ recovery per targeted account per month, pre (Jan–Mar) vs post
(Apr–Jul).

**Result:** treatment +₹22,709 vs control +₹21,967 per account/month after the
change → **DiD = +₹895/account/month (≈ +5.6%, not significant at these cell
sizes).** The counterfactual recovery without the change ≈ **₹17.8 Cr/month**
against ~₹18–19 Cr actual — **the strategy change did not move cash.**
Limitations: strategies run concurrently (not randomized), exact matching is
discrete, no spillover control. A geo-split rollout would identify this cleanly.

## 5. What should we do — and where does the ₹10 Cr go?

**Recommendation: WhatsApp / AI-digital engagement (options 3+5 blended).**
It is the only channel with a genuine, cash-backed upward drift
(2.5% → 3.3% share at constant click-to-pay conversion), it costs ~50× less per
contact than voice, and it scales without agent hiring.

| item | estimate |
|---|---:|
| Expected incremental recovery (yr 1) | **₹13.2 Cr** (2× current WA-attributed cash) |
| Cost to deploy | **₹3.5–4.0 Cr** (provider, AI voice-to-WA concierge, ops) |
| Expected ROI | **≈ 3.8×** (downside if click-to-pay halves: ≈ 1.7×) |
| Break-even | **≈ 3.2 months** |
| Key assumptions | conversion holds at 3× reach; no cannibalisation of voice cash; SPL templates + 10-min response SLA |
| Downside scenario | reach saturates (borrowers without WA) → ~+₹6 Cr, still profitable |
| Confidence | **medium-low** — golden attribution covers only ~13% of cash; run a 2-month geo-split test before scaling beyond ₹4 Cr |

**Sequencing:** 1) fix measurement (dedup at ingestion, IST normalization,
14-day attribution rule, PTP=verified-cash only) — free, immediate; 2) ₹4 Cr
WhatsApp scale + AI concierge; 3) hold the remaining ₹6 Cr until the geo-split
test reads out.

**Expected financial impact of fixing measurement alone:** reported recovery
would drop ~2% (doubles removed) but forecast accuracy and per-channel
deployment decisions improve materially; ₹10.95 Cr/month of mis-credited
recovery currently makes campaign league tables random noise.

## 6. How confident are we?

- Facts (duplicates, PTP-without-cash, tz): built from deterministic row-level
  evidence — **high confidence**.
- Flat-trend verdict: OLS on 7 monthly points, p = 0.88 — **high confidence**
  that there is no improvement to explain.
- Investment sizing: **medium-low** — honest interval ₹6–13 Cr incremental;
  the two-month split test is the cheapest way to buy certainty.

*Deliverables: golden dataset + pipeline (data/golden), SQL repository (sql/),
forensics notebook (analysis/), data-quality report (reports/),
single-screen dashboard (dashboard/index.html), production design
(reports/production_design.md), architecture diagram (architecture/).*
