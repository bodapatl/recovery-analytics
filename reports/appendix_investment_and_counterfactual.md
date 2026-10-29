# Appendix — Counterfactual detail & the six-option investment model

_Supporting detail for the executive memo. Generated from the golden layer;
numbers come from `reports/analysis_summary.json` and reproduce via `run_all.py`._

## A. Counterfactual — full detail

**Design.** Treatment = accounts first targeted under modern (v2/v3) strategies
after Mar-2026; control = accounts targeted only by legacy/v1 strategies;
exact match on risk_segment × DPD-band × loan_type (80 matched cells); outcome
= ₹ recovery per targeted account per month, pre (Jan–Mar) vs post (Apr–Jul).
Identifying assumptions: parallel trends, no spillover, exogenous rollout
timing. All three are fragile with concurrent strategies — hence the labels.

| quantity | value |
|---|---:|
| Treatment pre / post (₹/acct/mo) | +22,709 / matched-cell weighted |
| Control pre / post | 21,967 treatment-post minus run-rate |
| **DiD (main, matched)** | **+₹895/acct/mo (≈ +5.6%)** |
| 95% CI (cell dispersion, df = k−1) | [−₹1,224, +₹3,013], p = 0.40 |
| **Permutation placebo** (2,000 random arm-swaps, seed 42) | **p_placebo = 1.00 — placebo labels produce DiDs this extreme 100% of the time** |
| Variant: unmatched spec (no matching) | +₹378/acct/mo |
| Variant: "mixed" arm (4,809 accts) pooled into control | −₹70/acct/mo |
| Pre-trend check (Jan–Mar slopes by arm) | legacy −₹91, modern_early −₹55, modern_late +₹427 ₹/mo (n.s.) |
| Counterfactual monthly recovery without change | ≈ ₹17.8 Cr/mo vs ~₹18–19 Cr actual |

**Read:** every specification — matched, unmatched, pooled-control, placebo —
lands within a few ₹hundred of zero. The mid-year strategy change produced **no
detectable cash lift**; the label is exploratory, not proven-zero. A geo-split
rollout would identify this cleanly.

## B. Attribution-window sensitivity

% of golden cash with a last-RPC touch within W days (full months, RPC rule):

| window | 7d | 14d | 30d | 60d |
|---|---:|---:|---:|---:|
| coverage | 5.3% | 10.0% | 18.6% | 30.3% |

Coverage moves smoothly with the window (adding the 7-day contact fallback
gives the canonical 12.4% at the 14d rule) — the unattributed-bulk finding
(≈88%) is not an artifact of picking 14 days.

## C. Six-option investment model — full table

One model for every option: year-1 incremental recovery (conservative / base /
upside) vs deployment cost. Net ROI = (base incremental − cost) ÷ cost.

| # | option | cost | incr. ₹Cr/yr C/B/U | gross ROI | **net ROI** | B/E base | call |
|---|---|---:|---|---:|---:|---:|---|
| 1 | Telephony infrastructure upgrade | ₹2.0 Cr | 0.5 / 1.5 / 3.0 | 0.8× | −0.3× | 16 mo | **defer** — vendor connect-rate spread only ~2.3 pp; no elasticity in this data (Hypothesis) |
| 2 | More agents / capacity | ₹3.5 Cr | 1.0 / 4.0 / 8.0 | 1.1× | 0.1× | 10.5 mo | **defer** — productivity flat ₹16.4–17.0k/hr; needs a randomized headcount pilot |
| 3 | AI voice concierge | ₹2.5 Cr | 1.0 / 3.0 / 5.0 | 1.2× | 0.2× | 10 mo | **defer as standalone** — implementation lever *inside* option 5 |
| 4 | Better targeting / data | ₹1.5 Cr | 0.0 / 1.5 / 4.0 | 1.0× | 0.0× | 12 mo | **defer — the DiD above is null**; geo-split first |
| **5** | **WhatsApp / digital engagement** | **₹3.5 Cr** | **5.9 / 13.2 / 16.5** | 3.8× | **2.8×** | **3.2 mo** | **INVEST ₹3.5 Cr now; hold remainder** |
| 6 | Field-operations expansion | ₹4.0 Cr | 1.0 / 2.0 / 4.0 | 0.5× | −0.5× | 24 mo | **defer** — no per-visit cost source; ROI unsizable |

Options 1, 2, 3, 4, 6 are transparent scenario judgments: the contract provides
no cost table and no identified elasticity for them (that absence is itself a
finding). Option 5 is data-derived; its uncertainty is dominated by attribution
coverage (12.4% of cash), not by conversion assumptions.

### Sizing: why ₹3.5 Cr now rather than ₹10 Cr

- **The measured increment scales with messages, not rupees committed.**
  ₹10 Cr at ₹0.20/msg buys ~0.5 billion messages — ~30,000× current annual
  volume. There is no evidence the borrower-base reach exists to absorb it
  (the channel holds 3.3% of attributed cash today).
- Committing all ₹10 Cr to option 5 today: net return = ₹13.2 − 10 = **₹3.2 Cr
  → 0.3× net**. Deploying ₹3.5 Cr buys the **same measured increment**
  (bounded by the 3×-reach scenario) at **2.8× net**.
- The remaining **₹6.5 Cr is not idle**: it is released tier-by-tier only if
  the pre-registered 2-month geo-split test (≈3 states, control preserved)
  proves higher reach converts without cannibalising voice cash. This staged
  plan maximizes expected net return on the full ₹10 Cr, which is the honest
  answer to "where does ₹10 Cr go" — one investment area, risk-gated spend.

### Cash-flow timing

Costs are ~90% fixed (platform + integration + ops seats); variable messaging
cost is negligible at current volume. Assumed linear ramp to 3× reach over the
first ~2 months → steady-state break-even **≈ 3.2 months**, net-cash-positive
roughly month 4–5 under the conservative case.
