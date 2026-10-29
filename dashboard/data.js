window.DASH = {
  "meta": {
    "generated_at": "2026-10-28",
    "data_window": "2026-01-01 .. 2026-08-08 (Aug partial, excluded from trend)",
    "business_tz": "Asia/Kolkata",
    "portfolio_outstanding_cr": 1048.9
  },
  "headline": {
    "reported_claim": "+11% MoM recovery improvement",
    "verdict": "NOT REAL",
    "verdict_detail": "The +11% is the Feb\u2192Mar bounce (gold +11.1%). Gold MoM averages 0.0% (Jan\u2192Jul = 0.0%), trend slope +0.02 Cr/month, p = 0.88 \u2014 statistically indistinguishable from flat.",
    "gold_recovery_cr": [
      18.72,
      17.01,
      18.89,
      17.51,
      18.43,
      17.56,
      18.72
    ],
    "raw_recovery_cr": [
      19.11,
      17.41,
      19.32,
      17.84,
      18.7,
      17.87,
      19.03
    ],
    "months": [
      "2026-01",
      "2026-02",
      "2026-03",
      "2026-04",
      "2026-05",
      "2026-06",
      "2026-07"
    ],
    "gold_mom_pct": [
      -9.1,
      11.1,
      -7.3,
      5.3,
      -4.7,
      6.6
    ],
    "trend": {
      "slope_per_month": 0.022857142857142625,
      "t_stat": 0.1486036775523216,
      "p_value": 0.8818663709677381,
      "r2": 0.004397189920816724,
      "intercept": 18.051428571428573
    },
    "total_gold_cr": 126.85,
    "total_raw_cr": 129.29,
    "tilting_errors": {
      "duplicate_double_payments_cr": 2.59,
      "stale_touch_attribution_jul_cr": 10.95,
      "ptp_reported_kept_rate_pct": 19.2,
      "ptp_verified_kept_rate_pct": 3.7,
      "tz_misclassified_calls_pct": 55.7
    }
  },
  "funnel": {
    "months": [
      "2026-01",
      "2026-02",
      "2026-03",
      "2026-04",
      "2026-05",
      "2026-06",
      "2026-07"
    ],
    "targeted": [
      5732,
      5160,
      5666,
      5585,
      5800,
      5535,
      5666
    ],
    "contacted_all": [
      9400,
      8769,
      9784,
      9602,
      10039,
      9890,
      10410
    ],
    "rpc": [
      5549,
      5125,
      5828,
      5797,
      6122,
      6048,
      6366
    ],
    "ptp": [
      3166,
      2810,
      3187,
      3165,
      3266,
      3254,
      3404
    ],
    "ptp_kept_verified": [
      118,
      100,
      119,
      114,
      160,
      144,
      122
    ],
    "paid": [
      2374,
      2173,
      2419,
      2304,
      2344,
      2286,
      2335
    ]
  },
  "channel": {
    "months": [
      "2026-01",
      "2026-02",
      "2026-03",
      "2026-04",
      "2026-05",
      "2026-06",
      "2026-07"
    ],
    "voice": [
      17.43,
      15.59,
      16.89,
      16.04,
      16.41,
      16.1,
      16.9
    ],
    "whatsapp": [
      0.46,
      0.5,
      0.61,
      0.48,
      0.64,
      0.54,
      0.62
    ],
    "sms": [
      0.25,
      0.33,
      0.48,
      0.32,
      0.53,
      0.32,
      0.4
    ],
    "field": [
      0.49,
      0.48,
      0.75,
      0.58,
      0.6,
      0.5,
      0.65
    ]
  },
  "digital": {
    "months": [
      "2026-01",
      "2026-02",
      "2026-03",
      "2026-04",
      "2026-05",
      "2026-06",
      "2026-07"
    ],
    "wa_sent": [
      1412,
      1321,
      1404,
      1364,
      1361,
      1422,
      1502
    ],
    "wa_click": [
      2767,
      2554,
      2808,
      2702,
      2893,
      2738,
      2807
    ],
    "sms_sent": [
      1590,
      1447,
      1650,
      1483,
      1643,
      1473,
      1657
    ],
    "wa_click_rate_pct": [
      196.0,
      193.3,
      200.0,
      198.1,
      212.6,
      192.5,
      186.9
    ]
  },
  "ptp_probe": {
    "n_ptp_events": [
      3166,
      2810,
      3187,
      3165,
      3266,
      3254,
      3404
    ],
    "reported_kept_rate_pct": [
      19.2,
      20.1,
      19.4,
      19.8,
      19.4,
      18.5,
      18.9
    ],
    "verified_kept_rate_pct": [
      3.7,
      3.6,
      3.7,
      3.6,
      4.9,
      4.4,
      3.6
    ],
    "kept_status_without_cash": [
      585,
      539,
      594,
      605,
      603,
      569,
      629
    ]
  },
  "attribution": {
    "unattributed_share_pct": [
      90.7,
      88.0,
      86.4,
      88.0,
      85.4,
      88.3,
      86.2
    ],
    "stale_touch_credit_cr": [
      0.0,
      1.68,
      5.09,
      7.1,
      8.51,
      9.57,
      10.95
    ],
    "rpc14d_credit_cr": [
      1.31,
      1.58,
      1.93,
      1.79,
      2.07,
      1.61,
      1.98
    ],
    "contact7d_credit_cr": [
      0.43,
      0.46,
      0.63,
      0.31,
      0.61,
      0.44,
      0.61
    ],
    "verdict": "payments have no trustworthy 'last-touch' anchor: any campaign league table built on latest-touch is noise"
  },
  "denominator": {
    "recovery_per_contacted_acct_cr": [
      19917.99,
      19402.72,
      19308.3,
      18239.75,
      18353.45,
      17751.24,
      17986.77
    ],
    "n_targeted": [
      5732,
      5160,
      5666,
      5585,
      5800,
      5535,
      5666
    ],
    "n_contacted_all_channels": [
      9400,
      8769,
      9784,
      9602,
      10039,
      9890,
      10410
    ],
    "contactable_over_targeted_pct": [
      164.0,
      169.9,
      172.7,
      171.9,
      173.1,
      178.7,
      183.7
    ],
    "explanation": "contact denominator includes untargeted accounts -> contact metrics not comparable"
  },
  "decomposition": {
    "total_change_cr": 0.0,
    "mix_effect_cr": -0.01,
    "rate_effect_cr": 0.01,
    "top_mix_bands": [
      {
        "opened_quarter": "2024Q3",
        "dpd_band": "0-30",
        "risk_segment": "HIGH",
        "loan_type": "AUTO",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2024Q2",
        "dpd_band": "0-30",
        "risk_segment": "LOW",
        "loan_type": "BNPL",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2024Q2",
        "dpd_band": "0-30",
        "risk_segment": "HIGH",
        "loan_type": "AUTO",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2024Q3",
        "dpd_band": "31-60",
        "risk_segment": "HIGH",
        "loan_type": "AUTO",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2025Q1",
        "dpd_band": "0-30",
        "risk_segment": "HIGH",
        "loan_type": "AUTO",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2025Q4",
        "dpd_band": "0-30",
        "risk_segment": "NPA",
        "loan_type": "CONSUMER",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2024Q4",
        "dpd_band": "0-30",
        "risk_segment": "HIGH",
        "loan_type": "CREDIT_CARD",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      },
      {
        "opened_quarter": "2025Q3",
        "dpd_band": "0-30",
        "risk_segment": "HIGH",
        "loan_type": "CREDIT_CARD",
        "mix_effect": -0.0,
        "rate_effect": -0.0
      }
    ]
  },
  "counterfactual": {
    "design": {
      "treatment": "accounts first targeted under modern (v2/v3) strategies AFTER Mar-2026",
      "control": "accounts targeted only by legacy/v1 strategies through Jul-2026",
      "matching": "exact match on risk_segment x dpd_band x loan_type",
      "outcome": "recovery amount per targeted account per month (pre Jan-Mar vs post Apr-Jul)",
      "identified_cells": 80,
      "assumptions": [
        "parallel trends between strategy arms within a matched cell",
        "no spillover between arms",
        "rollout timing exogenous to account quality"
      ],
      "limitations": [
        "strategies run concurrently (selection not randomized)",
        "matching is exact within discrete cells only"
      ]
    },
    "recovery_per_targeted_account_inr": {
      "treatment_pre": 15916.0,
      "treatment_post": 22709.0,
      "control_pre": 16068.0,
      "control_post": 21967.0
    },
    "did_inr_per_account": 895.0,
    "did_pct_of_treatment_pre": 5.6,
    "counterfactual_monthly_recovery_cr": 17.84,
    "actual_monthly_recovery_apr_jul_cr": null
  },
  "investment": {
    "recommendation": "whatsapp_digital",
    "wa_avg_monthly_cr": 0.55,
    "wa_share_start_pct": 2.47,
    "wa_share_end_pct": 3.34,
    "expected_incremental_annual_cr": 13.2,
    "estimated_cost_cr": 3.5,
    "roi_multiple": 3.8,
    "breakeven_months": 3.2,
    "assumptions": [
      "3x WhatsApp reach with current click-to-pay conversion held",
      "assumed blend provider + concierge cost ~3.5 Cr/year",
      "no cannibalization of voice recovery assumed (voice-attributed flat)"
    ],
    "downside": "if click-to-pay halves at scale, incremental ~1x (+6 Cr) and ROI ~1.7x",
    "confidence": "medium-low: attribution is only 8% of cash; a 2-month geo split test would sharpen the estimate"
  },
  "dq_flags": [
    {
      "flag": "Duplicate payment rows",
      "impact": "\u20b92.59 Cr phantom cash",
      "severity": "high",
      "fixed": true
    },
    {
      "flag": "Stale-touch attribution drift",
      "impact": "\u20b90 \u2192 \u20b911.0 Cr cross-month credit churn",
      "severity": "high",
      "fixed": true
    },
    {
      "flag": "PTP KEPT status without cash",
      "impact": "4,309 promises marked KEPT with zero cash (reported kept \u224818%, verified \u22483.6%)",
      "severity": "critical",
      "fixed": true
    },
    {
      "flag": "Timezone misclassification",
      "impact": "55.7% of calls in wrong hour bucket",
      "severity": "high",
      "fixed": true
    },
    {
      "flag": "Agent master conflict",
      "impact": "30 rows per agent, 255 shared employee codes",
      "severity": "medium",
      "fixed": true
    },
    {
      "flag": "Borrower triple-writing",
      "impact": "30,600 \u2192 11,015 canonical borrowers",
      "severity": "medium",
      "fixed": true
    },
    {
      "flag": "Disposition code churn",
      "impact": "PROMISE_TO_PAY vs PTP split 3,926 rows",
      "severity": "medium",
      "fixed": true
    },
    {
      "flag": "Contact denominator noise",
      "impact": "contacts > targeted (112% of list)",
      "severity": "high",
      "fixed": false
    },
    {
      "flag": "Payment reference re-use",
      "impact": "1,782 refs shared across payments/accounts",
      "severity": "medium",
      "fixed": false
    }
  ]
};
