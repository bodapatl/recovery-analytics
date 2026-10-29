"""Export dashboard/data.js — the single-screen executive dashboard payload."""
from __future__ import annotations

import json

from src import config, db


def main() -> None:
    con = db.connect(readonly=True)
    summary = json.loads((config.REPORTS_DIR / "analysis_summary.json").read_text(encoding="utf-8"))

    mm = con.execute("""
        SELECT month, n_targeted, n_contacted, n_rpc_accounts, n_ptp_accounts,
               n_ptp_kept_verified, n_ptp_status_kept, recovery_accounts,
               agent_hours, n_agents_active, pool_outstanding, n_pool_accounts
        FROM gold_monthly_metrics ORDER BY month
    """).fetchdf()
    mm["month"] = mm["month"].astype(str).str[:7]
    full = mm[mm.month < "2026-08"]

    months = summary["what_happened"]["months"]
    gold = summary["what_happened"]["gold_recovery_cr"]
    raw = summary["what_happened"]["raw_success_cr"]

    funnel_def = {
        "months": months,
        "targeted": [int(v) for v in full.n_targeted],
        "contacted_all": [int(v) for v in full.n_contacted],
        "rpc": [int(v) for v in full.n_rpc_accounts],
        "ptp": [int(v) for v in full.n_ptp_accounts],
        "ptp_kept_verified": [int(v) for v in full.n_ptp_kept_verified],
        "paid": [int(v) for v in full.recovery_accounts],
    }

    channel = con.execute("""
        SELECT strftime(month, '%Y-%m') AS m, round(amt_voice/1e7, 2) AS voice,
               round(amt_whatsapp/1e7, 2) AS wa, round(amt_sms/1e7, 2) AS sms,
               round(amt_field/1e7, 2) AS field
        FROM month_channel WHERE month < '2026-08-01' ORDER BY 1
    """).fetchdf()

    payload = {
        "meta": {
            "generated_at": "2026-10-28",
            "data_window": "2026-01-01 .. 2026-08-08 (Aug partial, excluded from trend)",
            "business_tz": "Asia/Kolkata",
            "portfolio_outstanding_cr": summary["what_happened"]["pool_outstanding_cr"],
        },
        "headline": {
            "reported_claim": "+11% MoM recovery improvement",
            "verdict": "NOT REAL",
            "verdict_detail": (
                "The +11% is the Feb→Mar jump in MONTHLY totals — a calendar "
                "artifact of the 28-day February. Per-day recovery moves +0.2% "
                "Feb→Mar and runs flat all year (₹0.584–0.609 ₹Cr/day, per-day "
                "slope −0.002, p = 0.27). Monthly gold slope +0.02 Cr/month, "
                "95% CI [−0.37, +0.42] Cr/mo, p = 0.88 — no detectable trend at "
                "n=7; leave-one-out stable. (No detectable trend ≠ proof of no change.)"
            ),
            "gold_recovery_per_day_cr": summary["what_happened"]["gold_recovery_per_day_cr"],
            "days_in_month": summary["what_happened"]["days_in_month"],
            "gold_recovery_cr": gold,
            "raw_recovery_cr": raw,
            "months": months,
            "gold_mom_pct": summary["claim_test"]["gold_mom_pct"],
            "trend": summary["trend_test"]["gold"],
            "total_gold_cr": summary["what_happened"]["total_gold_cr"],
            "total_raw_cr": summary["what_happened"]["total_raw_success_cr"],
            "tilting_errors": {
                "duplicate_double_payments_cr": 2.59,
                "stale_touch_attribution_jul_cr": summary["attribution_probe"]["stale_touch_credit_cr"][-1],
                "ptp_reported_kept_rate_pct": summary["ptp_probe"]["reported_kept_rate_pct"][0],
                "ptp_verified_kept_rate_pct": summary["ptp_probe"]["verified_kept_rate_pct"][0],
                "tz_misclassified_calls_pct": 55.7,
            },
        },
        "funnel": funnel_def,
        "channel": {
            "months": channel.m.tolist(),
            "voice": channel.voice.tolist(),
            "whatsapp": channel.wa.tolist(),
            "sms": channel.sms.tolist(),
            "field": channel.field.tolist(),
        },
        "digital": summary["digital_funnel"],
        "ptp_probe": summary["ptp_probe"],
        "attribution": summary["attribution_probe"],
        "denominator": summary["denominator_probe"],
        "decomposition": summary["decomposition_jan_to_jul"],
        "counterfactual": summary["counterfactual"],
        "counterfactual_pretrend": summary["counterfactual_pretrend"],
        "attribution_coverage": summary["attribution_coverage"],
        "attribution_window_sensitivity": summary["attribution_window_sensitivity"],
        "per_day_view": {k: summary["what_happened"][k] for k in
                         ["months", "days_in_month", "gold_recovery_per_day_cr",
                          "gold_per_day_mom_pct"]},
        "appendix": "reports/appendix_investment_and_counterfactual.md",
        "driver_matrix": "reports/driver_matrix.md",
        "metric_registry": "reports/metric_definitions.yml",
        "verify_report": "reports/verify_report.md",
        "investment": summary["investment"],
        "dq_flags": [
            {"flag": "Duplicate payment rows", "impact": "₹2.59 Cr phantom cash", "severity": "high", "fixed": True},
            {"flag": "Stale-touch attribution drift", "impact": "₹0 → ₹11.0 Cr cross-month credit churn", "severity": "high", "fixed": True},
            {"flag": "PTP KEPT status without cash", "impact": "4,309 promises marked KEPT with zero cash (reported kept ≈18%, verified ≈3.6%)", "severity": "critical", "fixed": True},
            {"flag": "Timezone misclassification", "impact": "55.7% of calls in wrong hour bucket", "severity": "high", "fixed": True},
            {"flag": "Agent master conflict", "impact": "30 rows per agent, 255 shared employee codes", "severity": "medium", "fixed": True},
            {"flag": "Borrower triple-writing", "impact": "30,600 → 11,015 canonical borrowers", "severity": "medium", "fixed": True},
            {"flag": "Disposition code churn", "impact": "PROMISE_TO_PAY vs PTP split 3,926 rows", "severity": "medium", "fixed": True},
            {"flag": "Contact denominator noise", "impact": "contacts > targeted (112% of list)", "severity": "high", "fixed": False},
            {"flag": "Payment reference re-use", "impact": "1,782 refs shared across payments/accounts", "severity": "medium", "fixed": False},
        ],
    }

    js = "window.DASH = " + json.dumps(payload, indent=2, default=str) + ";\n"
    (config.DASHBOARD_DIR / "data.js").write_text(js, encoding="utf-8")
    print(f"dashboard/data.js written ({len(js)/1024:.1f} KB)")
    con.close()


if __name__ == "__main__":
    main()
