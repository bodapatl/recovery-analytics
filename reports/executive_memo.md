# Executive Memo — Collections Recovery Review

**To:** Leadership · **From:** Data Analyst (assignment deliverable) · **Date:** 2026-10-29
**Question reviewed:** *"Recovery has improved by 11% month-on-month."*
*Detail and tables: [`appendix_investment_and_counterfactual.md`](appendix_investment_and_counterfactual.md) · driver matrix: [`driver_matrix.md`](driver_matrix.md) · metric registry: [`metric_definitions.yml`](metric_definitions.yml)*

---

## 1. What happened?

**The reported improvement is not real — and not even a growth story: it is a
calendar artifact.** Rebuilt from a cleaned, deduplicated, timezone-normalized
"golden" dataset (639k raw rows → audited golden layer). Full months Jan–Jul 2026:

| month | days | golden recovery | **recovery/day** | MoM (calendar) | MoM (per-day) |
|---|---:|---:|---:|---:|---:|
| Jan | 31 | ₹18.72 Cr | ₹0.604 Cr | — | — |
| Feb | 28 | ₹17.01 Cr | ₹0.608 Cr | −9.1% | +0.7% |
| Mar | 31 | ₹18.89 Cr | ₹0.609 Cr | **+11.1%** | **+0.2%** |
| Apr | 30 | ₹17.51 Cr | ₹0.584 Cr | −7.3% | −4.1% |
| May | 31 | ₹18.43 Cr | ₹0.595 Cr | +5.3% | +1.9% |
| Jun | 30 | ₹17.56 Cr | ₹0.585 Cr | −4.7% | −1.7% |
| Jul | 31 | ₹18.72 Cr | ₹0.604 Cr | +6.6% | +3.2% |

The famous **+11% is the 28-day February**: monthly totals give Feb→Mar +11.1%,
but **per-day recovery moves +0.2%**. Per-day recovery runs flat all year
(₹0.584–0.609 ₹Cr/day; OLS slope −0.002 ₹Cr/day per month, p = 0.27).
Reported totals also include ₹157.2 Cr of PENDING/REVERSED "book" and ₹2.59 Cr
of double-posted SUCCESS rows removed by the golden layer (₹126.9 Cr true cash).

**Where cash actually moves:** attributed voice recovery is flat
(₹17.4 → ₹16.9 Cr, noisy); WhatsApp-attributed cash quietly **doubles its share**
(2.5% → 3.3%); agent-hour productivity is flat (₹16.4–17.0k/hr) — no agent story.

## 2. Why does the number look better than reality?

| # | mechanism | evidence | class |
|---|---|---|---|
| 1 | **Duplicate payment posting** — 500 payment ids filed twice; 346 carried double SUCCESS rows | ₹2.59 Cr phantom cash (reconciled exactly by automated tests) | **Fact** |
| 2 | **Broken payment attribution** — "latest touch, unbounded window" drifts onto old touches | stale-touch credit grows ₹0 → **₹10.95 Cr/mo by Jul**; only **12.4%** of cash attributable under a sane window (9.3–14.6%/mo) | **Strong evidence** |
| 3 | **Calendar effects** — nobody normalizes for month length | the +11% headline *is* this table's Feb→Mar cell | **Fact** |
| 4 | **PTP "kept" is not cash** — 4,309 of 4,483 KEPT promises have zero payment behind them | reported kept ≈18–19% vs **≈3.6–3.7%** verified | **Fact** |
| 5 | **Timezone misclassification** — UTC/Kolkata/Dubai naive timestamps mixed | **55.7%** of calls land in wrong business-hour buckets | **Fact** |
| 6 | **Denominator games** — contacted accounts (1.2× the target list) as denominator | golden pool fixed at ₹1,048.9 Cr outstanding, survivorship-proof | **Strong evidence** |
| 7 | Strategy-version campaigns made ops better | DiD (§4): no detectable lift | Correlation, null |

## 3. Is the reported 11% real? — No. Actual: **+0.0% MoM (±4%) once months are day-normalized**

Golden trend: OLS **+0.023 ₹Cr/month, 95% CI [−0.37, +0.42] Cr/mo, p = 0.88
(n = 7)**; leave-one-out stable (dropping any month keeps the slope in
−0.09…+0.16 Cr/mo, all p > 0.4). A sustained "+11% MoM" would need ≈ +2.1 Cr/mo —
far outside the CI. Honest caveat: n = 7 means low power — **we fail to detect a
trend; we do not prove nothing changed.** What we *do* prove is that the specific
+11%-MoM claim has no support under any definition checked — least of all
per-day. Attribution coverage of golden cash: **12.4% avg (9.3–14.6%/mo)**.

## 4. Counterfactual — did the mid-year targeting change do anything?

Exact-matched DiD (risk × DPD × loan_type; 80 cells): **+₹895/acct/mo, 95% CI
[−₹1,224, +₹3,013], p = 0.40**. Permutation placebo (2,000 controlled arm-swaps):
**p_placebo = 1.00.** Unmatched and pooled-control variants agree (−₹70…+₹378).
Counterfactual recovery ≈ ₹17.8 Cr/mo vs ~₹18–19 actual — **no detectable cash
effect**; exploratory, pending a geo-split. *(Full design, variants and
pre-trend check: appendix.)*

## 5. Where does the ₹10 Cr go? — **Option 5: WhatsApp / digital engagement (single primary)**

Only channel with cash-backed upward drift (2.5% → 3.3% attributed share) at
~10³-lower unit cost. Funnel caution: raw WhatsApp events (clicks ≈ sends,
lifecycle ~1:1) yield **no usable conversion rate** — the estimate is anchored
on volume × **₹3,930 cash per sent message**, and its error is dominated by
attribution coverage (12.4%), not conversion. **Net ROI (base): (13.2−3.5)/3.5
= 2.8×** (gross 3.8×), break-even ≈ **3.2 months** (ramp-adjusted ~4). Six
options, one consistent model (net ROI): telephony infra −0.3×, more agents
+0.1×, AI voice concierge +0.2×, targeting/data 0.0× (DiD null), field ops
−0.5× — all **defer** with the named test that would unlock each.
**Why not ₹10 Cr now?** The increment scales with *reach* (borrowers), not
rupees; committing ₹10 Cr today nets 0.3× vs 2.8× for ₹3.5 Cr. The AI concierge
is an implementation lever inside option 5.

**Sequencing:** 1) fix measurement (dedup at ingestion, IST normalization,
14-day attribution, PTP = verified cash) — free, immediate; 2) **₹3.5 Cr**
WhatsApp scale + concierge; 3) remaining **₹6.5 Cr released only after the
pre-registered 2-month geo-split test** (≈3 states) reads positive — the
staged plan is the highest-net-return use of the full ₹10 Cr in a single area.

## 6. How confident are we?

- **Facts** (duplicates ₹2.59 Cr reconciled to the gap exactly, PTP-without-cash,
  tz, per-day calendar math): deterministic + 16 passing automated tests
  (`src/verify.py`, incl. clean-rebuild determinism) — **high confidence**.
- **Flat-trend verdict**: CI + leave-one-out + per-day check — **high confidence
  in rejecting the +11% claim**; low power for detecting small trends (stated).
- **DiD**: CI straddles zero + placebo p = 1.00 — exploratory null.
- **Investment sizing**: medium-low (12.4% coverage) — the geo-split test is the
  cheapest way to buy certainty. Window sensitivity (7/14/30/60d → 5/10/19/30%
  coverage) shows the finding is not knife-edge.

*Deliverables: golden pipeline + exports, SQL repository, forensics notebook,
data-quality report, metric registry, driver matrix, reproducibility report,
single-screen dashboard, production design, architecture diagram, appendix.*
