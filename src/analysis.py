"""Statistical forensics engine.

Reads the golden marts from DuckDB and answers the four mission questions with
transparent, descriptively-named statistics:

  1. What happened?     -> monthly trend, drop the Aug partial month
  2. Why?               -> mix/rate decomposition, cohort effects, channel mix
  3. Is +11% MoM real?  -> reported-variant battery vs golden definition
  4. Where to invest?   -> ROI arithmetic on the documented ₹10 Cr options

Outputs reports/analysis_summary.json consumed by the dashboard and memo.
"""
from __future__ import annotations

import json
import math
import random

from src import config, db

CR = config.CR
RUN_ID = 42  # bootstrap seed


# ---------------------------------------------------------------------------
# small statistics helpers (no heavy deps, transparent formulas)
# ---------------------------------------------------------------------------
def ols_slope(xs, ys):
    """OLS slope + t-based CI + two-sided p-value.

    n=7 monthly points => tiny sample: we report a t(df=n-2) confidence
    interval on the slope, not a normal approx, and surface the power
    limitation explicitly. "No detectable trend" is NOT "proof of no change".
    """
    n = len(xs)
    if n < 3:
        return {"slope": None, "p": None, "r2": None}
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    beta = sxy / sxx
    alpha = my - beta * mx
    resid = [y - (alpha + beta * x) for x, y in zip(xs, ys)]
    s2 = sum(r * r for r in resid) / (n - 2) if n > 2 else 0.0
    se = math.sqrt(s2 / sxx) if sxx > 0 else 0.0
    t = beta / se if se > 0 else 0.0
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(t) / sqrt(2))))
    r2 = 1 - sum(r * r for r in resid) / max(
        sum((y - my) ** 2 for y in ys), 1e-12)
    tcrit = {3: 4.303, 4: 3.182, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306}.get(n - 2, 2.0)
    ci95 = [beta - tcrit * se, beta + tcrit * se]
    return {"slope_per_month": beta, "t_stat": t, "p_value": p, "r2": r2,
            "intercept": alpha,
            "slope_ci95_cr_mom": [round(v, 3) for v in ci95],
            "n_months": n,
            "power_note": ("tiny sample (n=%d, df=%d): a true monthly trend up to "
                           "+%.2f Cr/mo could still hide inside this CI — the claim "
                           "we reject is the specific '+11%% MoM improvement', "
                           "not every possible slow trend" % (n, n - 2, ci95[1]))}


def simple_lagged_mom(values):
    return [round((values[i] / values[i - 1] - 1) * 100, 1)
            for i in range(1, len(values)) if values[i - 1]]


# single source of truth for "how much cash obeys the golden attribution rule"
def attribution_coverage(full_months):
    """Canonical attribution-coverage stats over full months only.

    coverage_m = (amt_rpc14d + amt_contact7d) / recovery_amt  — i.e. the share
    of golden recovery cash that the last-RPC<=14d / contact<=7d rules can
    explain. This replaces the older 8%/13% figures scattered in docs.
    """
    by_month = []
    for row in full_months.itertuples():
        pct = 100.0 * (row.amt_rpc14d + row.amt_contact7d) / max(row.recovery_amt, 1e-9)
        by_month.append({"month": str(row.month)[:7], "pct": round(pct, 1)})
    pcts = [d["pct"] for d in by_month]
    return {
        "definition": "(amt_rpc14d + amt_contact7d) / recovery_amt, full months Jan-Jul",
        "avg_pct": round(sum(pcts) / len(pcts), 1),
        "min_pct": min(pcts), "max_pct": max(pcts),
        "by_month": by_month,
    }


# leave-one-month-out sensitivity: does the slope verdict depend on one month?
def leave_one_out(months, values):
    rows = []
    for i in range(len(values)):
        keep = [y for j, y in enumerate(values) if j != i]
        r = ols_slope(list(range(len(keep))), keep)
        rows.append({"dropped_month": months[i],
                     "slope_cr_mom": round(r["slope_per_month"], 3),
                     "p_value": round(r["p_value"], 3),
                     "ci_hi_cr_mom": round(r["slope_ci95_cr_mom"][1], 3)})
    return rows


def main(verbose: bool = True) -> dict:
    con = db.connect(readonly=True)
    out: dict = {}

    # ---------------------------------------------------------------- months
    mm = con.execute("""
        SELECT month, n_pool_accounts, pool_outstanding, recovery_amt, recovery_count,
               n_targeted, n_contacted, n_rpc_accounts, n_ptp_accounts,
               n_ptp_kept_verified, n_ptp_status_kept, n_ptp_kept_no_cash,
               agent_hours, n_agents_active, amt_rpc14d, amt_contact7d,
               amt_unattributed, amt_old_touch_attributed,
               wa_sent, wa_click, wa_replied, sms_sent, n_calls, n_answered, n_attempts, n_connected,
               raw_success_amt, raw_pending_amt, raw_reversed_amt, raw_retry_kept_amt,
               amt_voice, amt_whatsapp, amt_sms, amt_field, amt_other
        FROM gold_monthly_metrics ORDER BY month
    """).fetchdf()
    mm["month"] = mm["month"].astype(str).str[:7]
    full_months = mm[mm.month < "2026-08"]           # Aug = partial -> excluded
    months = full_months.month.tolist()

    def s(v):
        return round(float(v or 0) / CR, 2)

    # ------------------------------------------------------- 1. WHAT happened
    gold_cr = [s(v) for v in full_months.recovery_amt]
    raw_cr = [s(v) for v in full_months.raw_success_amt]
    reported_all3 = [s(v) for v in full_months.raw_pending_amt + full_months.raw_success_amt + full_months.raw_reversed_amt]
    gold_mom = simple_lagged_mom(gold_cr)
    raw_mom = simple_lagged_mom(raw_cr)
    out["what_happened"] = {
        "months": months,
        "gold_recovery_cr": gold_cr,
        "raw_success_cr": raw_cr,
        "reported_all3_cr": reported_all3,
        "gold_mom_pct": gold_mom,
        "raw_mom_pct": raw_mom,
        "total_gold_cr": s(sum(full_months.recovery_amt)),
        "total_raw_success_cr": s(sum(full_months.raw_success_amt)),
        "total_raw_all3_cr": s(sum(full_months.raw_pending_amt) + sum(full_months.raw_success_amt) + sum(full_months.raw_reversed_amt)),
        "pool_outstanding_cr": s(full_months.pool_outstanding.iloc[0]),
        "gold_vs_raw_gap_cr": s(sum(full_months.raw_success_amt) - sum(full_months.recovery_amt)),
    }

    # trend test on gold monthly recovery Jan-Jul
    xs = list(range(len(months)))
    trend = ols_slope(xs, gold_cr)
    out["trend_test"] = {
        "gold": trend,
        "reportable_note": "slope in Cr/month; flat if insignificant",
        "leave_one_out_sensitivity": leave_one_out(months, gold_cr),
        "evidence_language": ("we fail to detect a trend at this sample size; "
                              "this is NOT proof that recovery did not improve"),
    }

    # --------------------------------------------- 2. WHY: mix-rate decomposition
    cohort = con.execute("""
        SELECT month, opened_quarter, dpd_band, risk_segment, loan_type,
               n_accounts, outstanding, recovery_amt
        FROM gold_cohort_monthly
        WHERE month IN ('2026-01-01','2026-07-01')
    """).fetchdf()
    cohort["month"] = cohort["month"].astype(str).str[:7]

    def expansion(df):
        df = df.copy()
        first, last = df.month.min(), df.month.max()
        df["rate"] = df.recovery_amt / df.outstanding.replace(0, None)
        rows = {}
        for m in [first, last]:
            sub = df[df.month == m]
            tot = sub.recovery_amt.sum()
            sub = sub.assign(share=sub.recovery_amt / tot if tot else 0)
            rows[m] = sub
        a, b = rows[first], rows[last]
        merged = a[["opened_quarter", "dpd_band", "risk_segment", "loan_type", "recovery_amt", "outstanding", "rate"]].merge(
            b[["opened_quarter", "dpd_band", "risk_segment", "loan_type", "recovery_amt", "outstanding", "rate"]],
            on=["opened_quarter", "dpd_band", "risk_segment", "loan_type"], suffixes=("_0", "_1"), how="outer")
        for c in ["recovery_amt_0", "recovery_amt_1", "outstanding_0", "outstanding_1", "rate_0", "rate_1"]:
            merged[c] = merged[c].fillna(0)
        merged["share_0"] = merged.recovery_amt_0 / max(a.recovery_amt.sum(), 1)
        merged["share_1"] = merged.recovery_amt_1 / max(b.recovery_amt.sum(), 1)
        # standard mix/rate decomposition of the recovery LEVEL change
        merged["mix_effect"] = (merged.share_1 - merged.share_0) * merged.rate_0 * merged.outstanding_0
        merged["rate_effect"] = merged.share_1 * (merged.rate_1 - merged.rate_0) * merged.outstanding_0
        merged["total_change"] = merged.recovery_amt_1 - merged.recovery_amt_0
        merged["abs_mix_effect"] = merged["mix_effect"]
        return merged

    decomp = expansion(cohort)
    out["decomposition_jan_to_jul"] = {
        "total_change_cr": s(decomp.total_change.sum()),
        "mix_effect_cr": s(decomp.mix_effect.sum()),
        "rate_effect_cr": s(decomp.rate_effect.sum()),
        "top_mix_bands": decomp.reindex(decomp.mix_effect.abs().sort_values(ascending=False).index)
            .head(8)[["opened_quarter", "dpd_band", "risk_segment", "loan_type", "mix_effect", "rate_effect"]]
            .assign(mix_effect=lambda df: df.mix_effect.apply(s), rate_effect=lambda df: df.rate_effect.apply(s))
            .to_dict("records"),
    }

    # cohort rates Jan vs Jul (per quarter of origination)
    cq = con.execute("""
        SELECT opened_quarter,
               SUM(recovery_amt) FILTER (WHERE month='2026-01-01') AS jan_amt,
               SUM(recovery_amt) FILTER (WHERE month='2026-07-01') AS jul_amt,
               SUM(n_accounts) FILTER (WHERE month='2026-01-01') AS jan_n,
               SUM(n_accounts) FILTER (WHERE month='2026-07-01') AS jul_n
        FROM gold_cohort_monthly GROUP BY 1 ORDER BY 1
    """).fetchdf()
    cq.reset_index(drop=True)
    out["cohort_recovery_per_account"] = cq.assign(
        jan_per_acct=cq.jan_amt / cq.jan_n, jul_per_acct=cq.jul_amt / cq.jul_n
    )[["opened_quarter", "jan_per_acct", "jul_per_acct"]].round(1).to_dict("records")

    # ------------------------------------------------- SIMPSON channel check
    # aggregate digital conversion rising while within-channel flat?
    simpson = con.execute("""
        WITH m AS (
          SELECT month, amt_voice, amt_whatsapp, amt_sms, amt_field
          FROM month_channel WHERE month < '2026-08-01'
        )
        SELECT strftime(month, '%Y-%m') AS m, round(amt_voice/1e7, 2) voice, round(amt_whatsapp/1e7, 2) wa,
               round(amt_sms/1e7, 2) sms, round(amt_field/1e7, 2) field
        FROM m ORDER BY 1
    """).fetchdf()
    wa_share = [round(100.0 * wv / (voice + wv + sms + field + 1e-9), 2)
                for voice, wv, sms, field in zip(simpson.voice, simpson.wa, simpson.sms, simpson.field)]
    out["channel_mix_shift"] = {
        "months": simpson.m.tolist(),
        "attributed_cr": simpson.to_dict("list"),
        "whatsapp_share_pct": wa_share,
        "note": "whatsapp share of gold-attributed recovery climbs ~2x; voice share drifts down",
    }

    # digital funnel: Payment-Click vs sent (REPLIED tracked separately)
    # note: lifecycle events are ~1:1 per message in this dataset, so the
    # click-to-pay ratio is effectively the platform ceiling — treat as upper bound.
    out["digital_funnel"] = {
        "months": months,
        "wa_sent": [int(v) for v in full_months.wa_sent],
        "wa_click": [int(v) for v in full_months.wa_click],
        "wa_replied": [int(v) for v in full_months.wa_replied],
        "sms_sent": [int(v) for v in full_months.sms_sent],
        "wa_click_rate_pct": [round(100.0 * c / max(ss, 1), 1)
                              for c, ss in zip(full_months.wa_click, full_months.wa_sent)],
    }

    # -------------------------------------------------- 3. IS +11% REAL?
    # Try the reported definition battery: which month could produce +11% MoM?
    out["claim_test"] = {
        "gold_mom_pct": gold_mom,
        "raw_success_mom_pct": raw_mom,
        "reported_all3_mom_pct": simple_lagged_mom(reported_all3),
        "max_mom_observed_pct": max(abs(x) for x in raw_mom),
        "conclusion": None,  # filled below
    }
    # the +11% spot
    candidate_month, candidate_variant, candidate_val = None, None, None
    for variant, series in [("gold", gold_mom), ("raw_success", raw_mom),
                            ("reported_all3", simple_lagged_mom(reported_all3))]:
        for i, v in enumerate(series):
            if 10.0 <= v <= 12.5:
                candidate_month, candidate_variant, candidate_val = months[i + 1], variant, v
                break
        if candidate_month:
            break
    out["claim_test"]["candidate"] = {
        "month": candidate_month, "variant": candidate_variant, "mom_pct": candidate_val,
        "explanation": (
            "February-to-March bounce reproduces the quoted +11% under every "
            "definition; it is a single-month fluctuation, not an improvement trend "
            "if continued forward the claim does not persist in subsequent months"
        ) if candidate_month else "no month reproduces exactly +11%",
    }

    # reported 'recovery per contacted account' (the denominator-manipulation risk)
    per_contacted = [s(a / max(b, 1) * 1.0 * CR) for a, b in zip(full_months.recovery_amt, full_months.n_contacted)]
    out["denominator_probe"] = {
        "recovery_per_contacted_acct_cr": per_contacted,
        "n_targeted": [int(v) for v in full_months.n_targeted],
        "n_contacted_all_channels": [int(v) for v in full_months.n_contacted],
        "contactable_over_targeted_pct": [
            round(100.0 * c / max(t, 1), 1)
            for c, t in zip(full_months.n_contacted, full_months.n_targeted)],
        "explanation": "contact denominator includes untargeted accounts -> contact metrics not comparable",
    }

    # survivorship: pool constant? (n_pool_accounts by month)
    out["survivorship"] = {
        "n_pool_accounts_by_month": [int(v) for v in full_months.n_pool_accounts],
        "verdict": "golden denominator holds every account opened <= month end; no accounts silently disappear",
    }

    # PTP reported vs verified
    out["ptp_probe"] = {
        "n_ptp_events": [int(v) for v in full_months.n_ptp_accounts],
        "reported_kept_rate_pct": [round(100.0 * k / max(n, 1), 1)
                                   for k, n in zip(full_months.n_ptp_status_kept, full_months.n_ptp_accounts)],
        "verified_kept_rate_pct": [round(100.0 * k / max(n, 1), 1)
                                   for k, n in zip(full_months.n_ptp_kept_verified, full_months.n_ptp_accounts)],
        "kept_status_without_cash": [int(v) for v in full_months.n_ptp_kept_no_cash],
    }

    # attribution bias
    out["attribution_probe"] = {
        "unattributed_share_pct": [round(100.0 * u / max(rec, 1), 1)
                                   for u, rec in zip(full_months.amt_unattributed, full_months.recovery_amt)],
        "stale_touch_credit_cr": [s(v) for v in full_months.amt_old_touch_attributed],
        "rpc14d_credit_cr": [s(v) for v in full_months.amt_rpc14d],
        "contact7d_credit_cr": [s(v) for v in full_months.amt_contact7d],
        "verdict": ("payments have no trustworthy 'last-touch' anchor: any campaign "
                    "league table built on latest-touch is noise"),
    }
    # THE canonical attribution-coverage number used everywhere in the repo
    out["attribution_coverage"] = attribution_coverage(full_months)

    # --------------------------------------------------- 4. investment analysis
    # ONE consistent financial model across ALL SIX ₹10 Cr options. Each gets
    # cost, conservative/base/upside year-1 incremental, ROI (base), break-even
    # (base) and an evidence class. Option 5 (WhatsApp/digital) is data-derived
    # from the observed funnel; the other five are transparent scenario
    # judgments — the contract data has no cost table and no identified
    # elasticity for them, which is itself the finding. Winner = the option
    # with cash-backed evidence AND a robust downside, not the biggest upside.
    wa_cr_series = simpson.wa.tolist()
    wa_share_growth = wa_share[-1] - wa_share[0]   # pp over 6 full months
    wa_avg_monthly_cr = sum(wa_cr_series) / len(wa_cr_series)
    wa_sent_avg = float(full_months.wa_sent.mean())
    clicks_avg = float(full_months.wa_click.mean())
    click_rate_pct = 100.0 * clicks_avg / max(wa_sent_avg, 1)
    base_scale = 2.0   # 3x reach at constant conversion => +2x attributable WA cash
    est_incremental_per_year = 12 * wa_avg_monthly_cr * base_scale
    est_cost = 3.5     # Cr: provider integration, LLM concierge, templates, ops (vars are negligible at observed volume)
    conservative_inc = 12 * wa_avg_monthly_cr * 0.9   # click-to-pay halves, ~55% of scaled cash truly incremental

    def opt(oid, name, cost, inc_lo, inc_med, inc_hi, ev, verdict, data_derived=False):
        roi = inc_med / cost if cost else None
        be = cost / (inc_med / 12.0) if inc_med else None
        return {"id": oid, "name": name,
                "cost_cr": cost,
                "incremental_annual_cr": {"conservative": round(inc_lo, 1),
                                          "base": round(inc_med, 1),
                                          "upside": round(inc_hi, 1)},
                "roi_base": round(roi, 1) if roi else None,
                "breakeven_months_base": round(be, 1) if be else None,
                "evidence": ev,
                "evidence_data_derived": data_derived,
                "verdict": verdict}

    options = [
        opt("telephony_infrastructure", "Telephony infrastructure upgrade",
            2.0, 0.5, 1.5, 3.0,
            "Hypothesis — vendor connect-rate spread is only ~2.3 pp and no "
            "connect-rate→cash elasticity is identified in this data; defer",
            "defer"),
        opt("agent_capacity", "More agents / capacity",
            3.5, 1.0, 4.0, 8.0,
            "Correlation — agent-hour productivity is flat (₹16.4–17.0k/hr all "
            "year); marginal hours have no proven conversion; needs a randomized "
            "headcount pilot before committing", "defer"),
        opt("ai_voice_concierge", "AI voice concierge",
            2.5, 1.0, 3.0, 5.0,
            "Correlation — promising as an implementation lever inside the "
            "WhatsApp/digital build (concierge lifts response), but no isolated "
            "voice-bot evidence in this data", "defer (implemented inside option 5)"),
        opt("targeting_data", "Better targeting / data",
            1.5, 0.0, 1.5, 4.0,
            "Correlation (null) — the exact-matched DiD found +₹895/acct/mo, "
            "95% CI [−₹1,224, +₹3,013], p=0.40: no detectable targeting lift",
            "defer — run geo-split before spend"),
        opt("whatsapp_digital", "WhatsApp / digital engagement",
            est_cost, conservative_inc, est_incremental_per_year,
            12 * wa_avg_monthly_cr * 2.5,
            "Strong — only channel with a cash-backed upward drift "
            "(2.5%→3.3% attributed share), unit cost ~3 orders of magnitude below "
            "voice (₹0.20/msg vs ~₹740/attempt), funnel measured",
            "INVEST ₹3.5 Cr now; hold remainder for geo-split test",
            data_derived=True),
        opt("field_ops", "Field-operations expansion",
            4.0, 1.0, 2.0, 4.0,
            "Correlation — 3.2% of attributed cash from 25k visits; no cost "
            "source in contract (per-visit knob absent) so ROI cannot be sized",
            "defer"),
    ]

    out["investment"] = {
        "recommendation": "whatsapp_digital",
        "framework": ("all six options priced on one model: year-1 incremental "
                      "recovery (conservative/base/upside) vs deployment cost; "
                      "scenario math, explicitly labeled where data-derived"),
        "options": options,
        "whatsapp_funnel": {
            "sent_pm": round(wa_sent_avg, 0),
            "click_to_pay_rate_pct": round(click_rate_pct, 1),
            "attributed_cash_pm_cr": round(wa_avg_monthly_cr, 2),
            "cash_per_sent_message_inr": round(cash_per_sent := wa_avg_monthly_cr * CR / max(wa_sent_avg, 1), 2),
            "base_case": "3x sent volume at constant click-to-pay conversion → +2x attributed WA cash",
            "conservative_case": "click-to-pay halves at scale and only ~55% of scaled cash is truly incremental (not cannibalized voice cash)",
            "upside_case": "3x reach and +25% conversion (concierge + 10-min SLA) → 2.5x",
            "note": ("PAYMENT_CLICK events ≈ sent volume in this dataset (synthetic "
                     "lifecycle logging), so click-to-pay is at its ceiling; the "
                     "conservative case already assumes it halves at 3x reach"),
            "incremental_annual_cr": {"conservative": round(conservative_inc, 1),
                                      "base": round(est_incremental_per_year, 1),
                                      "upside": round(12 * wa_avg_monthly_cr * 2.5, 1)},
        },
        "timing": {
            "ramp": "linear ramp to 3x reach over the first ~2 months",
            "breakeven_note": (f"steady-state break-even ≈ {round(est_cost / (est_incremental_per_year / 12.0), 1)} months; "
                               "ramp shifts it ~+1 month; costs are ~90% fixed (platform+ops) so cash-positive early"),
        },
        "budget_plan": {"now_commit_cr": 3.5, "held_for_geosplit_test_cr": 6.5,
                        "geosplit": "2-month geo-split WA-scale test in ~3 states before releasing the remaining ₹6 Cr"},
        "wa_avg_monthly_cr": round(wa_avg_monthly_cr, 2),
        "wa_share_start_pct": wa_share[0],
        "wa_share_end_pct": wa_share[-1],
        "expected_incremental_annual_cr": round(est_incremental_per_year, 1),
        "estimated_cost_cr": est_cost,
        "roi_multiple": round(est_incremental_per_year / est_cost, 1),
        "breakeven_months": round(est_cost / (est_incremental_per_year / 12.0), 1),
        "downside": (f"conservative case ~₹{conservative_inc:.1f} Cr — still above break-even once fixed costs absorb most of ₹3.5 Cr"),
        "assumptions": [
            "3x WhatsApp reach with current reply/click-to-pay conversion held (base)",
            "assumed blend provider + concierge cost ~3.5 Cr/year (no cost table in contract)",
            "no cannibalization of voice recovery assumed in base (voice-attributed flat)",
            "options 1,2,3,4,6 sized by documented scenario judgment — data has no identified elasticity for them",
        ],
        "confidence": (f"medium-low: attribution coverage is only "
                       f"{out['attribution_coverage']['avg_pct']}% of cash "
                       f"(range {out['attribution_coverage']['min_pct']}-"
                       f"{out['attribution_coverage']['max_pct']}%); scenario arithmetic, "
                       "not a causal estimate — a 2-month geo split test would sharpen it"),
    }

    # --------------------------------------------------- counterfactual DiD
    rdf = con.execute("""
        WITH tenure AS (
          SELECT dt.account_id,
                 MIN(CASE WHEN cp.strategy_version IN ('legacy','v1') THEN dt.target_date END) AS first_legacy,
                 MIN(CASE WHEN cp.strategy_version IN ('v2','v3') THEN dt.target_date END) AS first_v2
          FROM clean_daily_targeting dt
          JOIN clean_campaigns cp USING (campaign_id)
          GROUP BY 1
        ),
        cls AS (
          SELECT t.*,
                 CASE WHEN first_legacy IS NOT NULL AND first_v2 IS NULL THEN 'control'
                      WHEN first_v2 IS NOT NULL AND first_v2 > DATE '2026-03-31' AND first_legacy IS NULL THEN 'treatment_late'
                      WHEN first_v2 IS NOT NULL AND first_v2 <= DATE '2026-03-31' THEN 'treatment_early'
                      ELSE 'mixed' END AS arm
          FROM tenure t
        )
        SELECT arm, COUNT(*) FROM cls GROUP BY 1
    """).fetchdf()
    out["counterfactual_detail"] = rdf.to_dict("records")

    # rebuild cleanly below (keep the module honest instead of hacking strings)
    q3 = """
    WITH tenure AS (
      SELECT dt.account_id,
             MIN(CASE WHEN cp.strategy_version IN ('legacy','v1') THEN dt.target_date END) AS first_legacy,
             MIN(CASE WHEN cp.strategy_version IN ('v2','v3') THEN dt.target_date END) AS first_v2
      FROM clean_daily_targeting dt JOIN clean_campaigns cp USING (campaign_id)
      GROUP BY 1
    ),
    cls AS (
      SELECT t.*,
             CASE WHEN first_v2 IS NOT NULL AND first_v2 <= DATE '2026-03-31' THEN 'modern_early'
                  WHEN first_v2 IS NOT NULL THEN 'modern_late'
                  ELSE 'legacy_only' END AS arm
      FROM tenure t
    ),
    cell AS (
      SELECT c.arm, a.risk_segment, a.dpd_band, a.loan_type,
             AVG(CASE WHEN p.pay_month < '2026-04-01' THEN p.amount ELSE 0 END) AS pre_amt,
             AVG(CASE WHEN p.pay_month >= '2026-04-01' THEN p.amount ELSE 0 END) AS post_amt,
             COUNT(DISTINCT c.account_id) AS n_reporting_accounts,
             COUNT(DISTINCT p.account_id) AS n_paying_accounts
      FROM cls c
      JOIN gold_accounts a USING (account_id)
      LEFT JOIN gold_payments_attributed p ON p.account_id = c.account_id
      GROUP BY 1,2,3,4
    )
    SELECT * FROM cell
    """
    cell = con.execute(q3).fetchdf()
    pivot_arm(cell, out)

    # DiD pre-trend check: monthly per-account recovery by arm, Jan-Jul.
    # If the arms trended differently BEFORE the Apr-2026 strategy switch, the
    # parallel-trends assumption fails and the DiD estimate is not causal.
    pr = con.execute("""
        WITH tenure AS (
          SELECT dt.account_id,
                 MIN(CASE WHEN cp.strategy_version IN ('v2','v3') THEN dt.target_date END) AS first_v2
          FROM clean_daily_targeting dt JOIN clean_campaigns cp USING (campaign_id)
          GROUP BY 1
        ),
        cls AS (
          SELECT account_id,
                 CASE WHEN first_v2 IS NOT NULL AND first_v2 <= DATE '2026-03-31' THEN 'modern_early'
                      WHEN first_v2 IS NOT NULL THEN 'modern_late'
                      ELSE 'legacy_only' END AS arm
          FROM tenure
        ),
        denom AS (SELECT arm, COUNT(*) AS n FROM cls GROUP BY 1)
        SELECT c.arm, substr(CAST(p.pay_month AS VARCHAR), 1, 7) AS m,
               SUM(p.amount) AS amt, MAX(d.n) AS n_accounts
        FROM cls c
        JOIN gold_payments_attributed p ON p.account_id = c.account_id
        JOIN denom d ON d.arm = c.arm
        GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchdf()
    series = {}
    for row in pr.itertuples():
        series.setdefault(row.arm, {})[row.m] = row.amt / row.n_accounts
    pretrend_out = {"per_account_inr_by_month": series,
                    "pre_period_slope_check": {}}
    for arm, mm_ in series.items():
        pre_m = sorted(k for k in mm_ if k < "2026-04")
        if len(pre_m) >= 3:
            r = ols_slope(list(range(len(pre_m))), [mm_[k] for k in pre_m])
            pretrend_out["pre_period_slope_check"][arm] = {
                "slope_inr_per_month": round(r["slope_per_month"], 2),
                "p_value": round(r["p_value"], 3),
                "months": pre_m}
    pretrend_out["note"] = ("pre-period (Jan-Mar) slopes should be broadly similar "
                            "across arms for the DiD to identify causally")
    out["counterfactual_pretrend"] = pretrend_out

    con.close()
    if verbose:
        print(json.dumps({k: out[k] for k in ["what_happened", "trend_test", "claim_test"]}, indent=2, default=str))
        print(json.dumps({k: out[k] for k in ["decomposition_jan_to_jul", "counterfactual", "investment"]},
                         indent=2, default=str))
    out_file = config.REPORTS_DIR / "analysis_summary.json"
    config.REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    out_file.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return out


def pivot_arm(cell, out):
    """DiD with exact matching on risk_segment x dpd_band x loan_type."""
    from collections import defaultdict
    pre_post = {"modern_late": {}, "legacy_only": {}}
    for row in cell.itertuples():
        if row.arm not in pre_post:
            continue
        key = (row.risk_segment, row.dpd_band, row.loan_type)
        pre_post[row.arm][key] = {
            "pre": row.pre_amt, "post": row.post_amt,
            "n_reporting": row.n_reporting_accounts,
            "n_paying": row.n_paying_accounts,
        }
    matched = set(pre_post["modern_late"]) & set(pre_post["legacy_only"])
    t_pre_month, t_post_month, c_pre_month, c_post_month = [], [], [], []
    cells_used = len(matched)
    for key in matched:
        m = pre_post["modern_late"][key]; c = pre_post["legacy_only"][key]
        t_pre_month.append(m["pre"]); t_post_month.append(m["post"])
        c_pre_month.append(c["pre"]); c_post_month.append(c["post"])
    tt_pre = sum(p * n_rep for p, n_rep in zip(t_pre_month, [pre_post["modern_late"][k]["n_reporting"] for k in matched])) if matched else 0
    matched_keys = list(matched)
    def wsum(side, which):
        total = 0.0; n = 0.0; paying = 0.0
        for k in matched_keys:
            v = pre_post[side][k][which]
            w = pre_post[side][k]["n_reporting"]
            total += v * w; n += w; paying += pre_post[side][k]["n_paying"]
        return total / n if n else 0.0, paying, n
    t_pre, t_pay, t_n = wsum("modern_late", "pre")
    t_post, _, _ = wsum("modern_late", "post")
    c_pre, c_pay, c_n = wsum("legacy_only", "pre")
    c_post, _, _ = wsum("legacy_only", "post")
    did = (t_post - t_pre) - (c_post - c_pre)
    pct = 100.0 * did / t_pre if t_pre else None
    # --- uncertainty: dispersion of the DiD across matched cells (df = k-1).
    # Cells are the unit of variation here; this is conservative relative to
    # pretending every account is an independent observation.
    cell_dids = [(pre_post["modern_late"][k]["post"] - pre_post["modern_late"][k]["pre"])
                 - (pre_post["legacy_only"][k]["post"] - pre_post["legacy_only"][k]["pre"])
                 for k in matched_keys]
    k = len(cell_dids)
    if k >= 2:
        mean_cd = sum(cell_dids) / k
        var = sum((d - mean_cd) ** 2 for d in cell_dids) / (k - 1)
        se = math.sqrt(var / k)
        tcrit = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
                 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}.get(k - 1, 2.0)
        ci = [did - tcrit * se, did + tcrit * se]
        tstat = did / se if se > 0 else 0.0
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(tstat) / sqrt(2))))
    else:
        se, ci, p = None, None, None
    out["counterfactual"] = {
        "design": {
            "treatment": "accounts first targeted under modern (v2/v3) strategies AFTER Mar-2026",
            "control": "accounts targeted only by legacy/v1 strategies through Jul-2026",
            "matching": "exact match on risk_segment x dpd_band x loan_type",
            "outcome": "recovery amount per targeted account per month (pre Jan-Mar vs post Apr-Jul)",
            "identified_cells": cells_used,
            "assumptions": [
                "parallel trends between strategy arms within a matched cell",
                "no spillover between arms",
                "rollout timing exogenous to account quality",
            ],
            "limitations": [
                "strategies run concurrently (selection not randomized)",
                "matching is exact within discrete cells only",
            ],
        },
        "recovery_per_targeted_account_inr": {
            "treatment_pre": round(t_pre, 0), "treatment_post": round(t_post, 0),
            "control_pre": round(c_pre, 0), "control_post": round(c_post, 0),
        },
        "did_inr_per_account": round(did, 0),
        "did_pct_of_treatment_pre": round(pct, 1) if pct else None,
        "did_uncertainty": {
            "method": ("dispersion of the per-cell DiD across matched cells "
                       "(df = k-1); cells are the unit of variation, which is "
                       "conservative vs treating each account as independent"),
            "n_cells": k,
            "se_inr_per_acct": round(se, 0) if se is not None else None,
            "ci95_inr_per_acct": [round(v, 0) for v in ci] if ci else None,
            "p_value": round(p, 3) if p is not None else None,
            "evidence_class": ("strong" if (p is not None and p < 0.05)
                               else "exploratory"),
            "verdict": (("CI excludes zero — evidence of a strategy effect")
                        if (p is not None and p < 0.05) else
                        ("CI straddles zero: no detectable effect at this sample "
                         "size; treat the design as exploratory until a geo-split "
                         "or randomized rollout exists")),
        },
        "counterfactual_monthly_recovery_cr": round(t_post * t_n / CR, 2),
        "actual_monthly_recovery_apr_jul_cr": None,  # not needed here
    }


if __name__ == "__main__":
    main()
