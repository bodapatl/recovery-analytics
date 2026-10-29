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
    "verdict_detail": "The +11% is the Feb\u2192Mar bounce (gold +11.1%). Gold MoM averages 0.0% (Jan\u2192Jul = 0.0%), trend slope +0.02 Cr/month, 95% CI [\u22120.37, +0.42] Cr/mo, p = 0.88 \u2014 no detectable trend at n=7 months. Leave-one-out: every month can be dropped and the verdict holds. (No detectable trend \u2260 proof of no change.)",
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
      "intercept": 18.051428571428573,
      "slope_ci95_cr_mom": [
        -0.373,
        0.418
      ],
      "n_months": 7,
      "power_note": "tiny sample (n=7, df=5): a true monthly trend up to +0.42 Cr/mo could still hide inside this CI \u2014 the claim we reject is the specific '+11% MoM improvement', not every possible slow trend"
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
      1410,
      1262,
      1394,
      1315,
      1487,
      1386,
      1440
    ],
    "wa_replied": [
      1357,
      1292,
      1414,
      1387,
      1406,
      1352,
      1367
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
      99.9,
      95.5,
      99.3,
      96.4,
      109.3,
      97.5,
      95.9
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
    "did_uncertainty": {
      "method": "dispersion of the per-cell DiD across matched cells (df = k-1); cells are the unit of variation, which is conservative vs treating each account as independent",
      "n_cells": 80,
      "se_inr_per_acct": 1059.0,
      "ci95_inr_per_acct": [
        -1224.0,
        3013.0
      ],
      "p_value": 0.398,
      "evidence_class": "exploratory",
      "verdict": "CI straddles zero: no detectable effect at this sample size; treat the design as exploratory until a geo-split or randomized rollout exists"
    },
    "counterfactual_monthly_recovery_cr": 17.84,
    "actual_monthly_recovery_apr_jul_cr": null
  },
  "counterfactual_pretrend": {
    "per_account_inr_by_month": {
      "legacy_only": {
        "2026-01": 6471.7176540807095,
        "2026-02": 5558.2741326067235,
        "2026-03": 6289.5836927468545,
        "2026-04": 5397.543836771771,
        "2026-05": 6201.380874529645,
        "2026-06": 5626.700211496034,
        "2026-07": 6487.45309069677,
        "2026-08": 1351.3077475022712
      },
      "modern_early": {
        "2026-01": 6373.098080730167,
        "2026-02": 5621.718975446715,
        "2026-03": 6263.629526931482,
        "2026-04": 5935.899650340656,
        "2026-05": 5889.491443630282,
        "2026-06": 5936.930584908088,
        "2026-07": 5978.71714616275,
        "2026-08": 1591.332153233064
      },
      "modern_late": {
        "2026-01": 5830.5124408246365,
        "2026-02": 5774.792533723595,
        "2026-03": 6684.041620005092,
        "2026-04": 5892.952996945788,
        "2026-05": 6355.990259608044,
        "2026-06": 6042.247412827687,
        "2026-07": 6232.191767625354,
        "2026-08": 1538.2506261135145
      }
    },
    "pre_period_slope_check": {
      "legacy_only": {
        "slope_inr_per_month": -91.07,
        "p_value": 0.848,
        "months": [
          "2026-01",
          "2026-02",
          "2026-03"
        ]
      },
      "modern_early": {
        "slope_inr_per_month": -54.73,
        "p_value": 0.892,
        "months": [
          "2026-01",
          "2026-02",
          "2026-03"
        ]
      },
      "modern_late": {
        "slope_inr_per_month": 426.76,
        "p_value": 0.126,
        "months": [
          "2026-01",
          "2026-02",
          "2026-03"
        ]
      }
    },
    "note": "pre-period (Jan-Mar) slopes should be broadly similar across arms for the DiD to identify causally"
  },
  "attribution_coverage": {
    "definition": "(amt_rpc14d + amt_contact7d) / recovery_amt, full months Jan-Jul",
    "avg_pct": 12.4,
    "min_pct": 9.3,
    "max_pct": 14.6,
    "by_month": [
      {
        "month": "2026-01",
        "pct": 9.3
      },
      {
        "month": "2026-02",
        "pct": 12.0
      },
      {
        "month": "2026-03",
        "pct": 13.6
      },
      {
        "month": "2026-04",
        "pct": 12.0
      },
      {
        "month": "2026-05",
        "pct": 14.6
      },
      {
        "month": "2026-06",
        "pct": 11.7
      },
      {
        "month": "2026-07",
        "pct": 13.8
      }
    ]
  },
  "driver_matrix": "reports/driver_matrix.md",
  "metric_registry": "reports/metric_definitions.yml",
  "verify_report": "reports/verify_report.md",
  "investment": {
    "recommendation": "whatsapp_digital",
    "framework": "all six options priced on one model: year-1 incremental recovery (conservative/base/upside) vs deployment cost; scenario math, explicitly labeled where data-derived",
    "options": [
      {
        "id": "telephony_infrastructure",
        "name": "Telephony infrastructure upgrade",
        "cost_cr": 2.0,
        "incremental_annual_cr": {
          "conservative": 0.5,
          "base": 1.5,
          "upside": 3.0
        },
        "roi_base": 0.8,
        "breakeven_months_base": 16.0,
        "evidence": "Hypothesis \u2014 vendor connect-rate spread is only ~2.3 pp and no connect-rate\u2192cash elasticity is identified in this data; defer",
        "evidence_data_derived": false,
        "verdict": "defer"
      },
      {
        "id": "agent_capacity",
        "name": "More agents / capacity",
        "cost_cr": 3.5,
        "incremental_annual_cr": {
          "conservative": 1.0,
          "base": 4.0,
          "upside": 8.0
        },
        "roi_base": 1.1,
        "breakeven_months_base": 10.5,
        "evidence": "Correlation \u2014 agent-hour productivity is flat (\u20b916.4\u201317.0k/hr all year); marginal hours have no proven conversion; needs a randomized headcount pilot before committing",
        "evidence_data_derived": false,
        "verdict": "defer"
      },
      {
        "id": "ai_voice_concierge",
        "name": "AI voice concierge",
        "cost_cr": 2.5,
        "incremental_annual_cr": {
          "conservative": 1.0,
          "base": 3.0,
          "upside": 5.0
        },
        "roi_base": 1.2,
        "breakeven_months_base": 10.0,
        "evidence": "Correlation \u2014 promising as an implementation lever inside the WhatsApp/digital build (concierge lifts response), but no isolated voice-bot evidence in this data",
        "evidence_data_derived": false,
        "verdict": "defer (implemented inside option 5)"
      },
      {
        "id": "targeting_data",
        "name": "Better targeting / data",
        "cost_cr": 1.5,
        "incremental_annual_cr": {
          "conservative": 0.0,
          "base": 1.5,
          "upside": 4.0
        },
        "roi_base": 1.0,
        "breakeven_months_base": 12.0,
        "evidence": "Correlation (null) \u2014 the exact-matched DiD found +\u20b9895/acct/mo, 95% CI [\u2212\u20b91,224, +\u20b93,013], p=0.40: no detectable targeting lift",
        "evidence_data_derived": false,
        "verdict": "defer \u2014 run geo-split before spend"
      },
      {
        "id": "whatsapp_digital",
        "name": "WhatsApp / digital engagement",
        "cost_cr": 3.5,
        "incremental_annual_cr": {
          "conservative": 5.9,
          "base": 13.2,
          "upside": 16.5
        },
        "roi_base": 3.8,
        "breakeven_months_base": 3.2,
        "evidence": "Strong \u2014 only channel with a cash-backed upward drift (2.5%\u21923.3% attributed share), unit cost ~3 orders of magnitude below voice (\u20b90.20/msg vs ~\u20b9740/attempt), funnel measured",
        "evidence_data_derived": true,
        "verdict": "INVEST \u20b93.5 Cr now; hold remainder for geo-split test"
      },
      {
        "id": "field_ops",
        "name": "Field-operations expansion",
        "cost_cr": 4.0,
        "incremental_annual_cr": {
          "conservative": 1.0,
          "base": 2.0,
          "upside": 4.0
        },
        "roi_base": 0.5,
        "breakeven_months_base": 24.0,
        "evidence": "Correlation \u2014 3.2% of attributed cash from 25k visits; no cost source in contract (per-visit knob absent) so ROI cannot be sized",
        "evidence_data_derived": false,
        "verdict": "defer"
      }
    ],
    "whatsapp_funnel": {
      "sent_pm": 1398.0,
      "click_to_pay_rate_pct": 99.1,
      "attributed_cash_pm_cr": 0.55,
      "cash_per_sent_message_inr": 3934.19,
      "base_case": "3x sent volume at constant click-to-pay conversion \u2192 +2x attributed WA cash",
      "conservative_case": "click-to-pay halves at scale and only ~55% of scaled cash is truly incremental (not cannibalized voice cash)",
      "upside_case": "3x reach and +25% conversion (concierge + 10-min SLA) \u2192 2.5x",
      "note": "PAYMENT_CLICK events \u2248 sent volume in this dataset (synthetic lifecycle logging), so click-to-pay is at its ceiling; the conservative case already assumes it halves at 3x reach",
      "incremental_annual_cr": {
        "conservative": 5.9,
        "base": 13.2,
        "upside": 16.5
      }
    },
    "timing": {
      "ramp": "linear ramp to 3x reach over the first ~2 months",
      "breakeven_note": "steady-state break-even \u2248 3.2 months; ramp shifts it ~+1 month; costs are ~90% fixed (platform+ops) so cash-positive early"
    },
    "budget_plan": {
      "now_commit_cr": 3.5,
      "held_for_geosplit_test_cr": 6.5,
      "geosplit": "2-month geo-split WA-scale test in ~3 states before releasing the remaining \u20b96 Cr"
    },
    "wa_avg_monthly_cr": 0.55,
    "wa_share_start_pct": 2.47,
    "wa_share_end_pct": 3.34,
    "expected_incremental_annual_cr": 13.2,
    "estimated_cost_cr": 3.5,
    "roi_multiple": 3.8,
    "breakeven_months": 3.2,
    "downside": "conservative case ~\u20b95.9 Cr \u2014 still above break-even once fixed costs absorb most of \u20b93.5 Cr",
    "assumptions": [
      "3x WhatsApp reach with current reply/click-to-pay conversion held (base)",
      "assumed blend provider + concierge cost ~3.5 Cr/year (no cost table in contract)",
      "no cannibalization of voice recovery assumed in base (voice-attributed flat)",
      "options 1,2,3,4,6 sized by documented scenario judgment \u2014 data has no identified elasticity for them"
    ],
    "confidence": "medium-low: attribution coverage is only 12.4% of cash (range 9.3-14.6%); scenario arithmetic, not a causal estimate \u2014 a 2-month geo split test would sharpen it"
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
