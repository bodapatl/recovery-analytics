"""Stage runner: raw -> staging -> clean -> golden, with artifact export."""
from __future__ import annotations

import json

import duckdb
import pandas as pd

from . import config, db


def _fmt_cr(v):
    try:
        return round(float(v) / config.CR, 2)
    except (TypeError, ValueError):
        return None


def run(verbose: bool = True) -> dict:
    con = db.connect()
    steps = db.run_pipeline(con)
    if verbose:
        for name, status in steps:
            print(f"[pipeline] {name}: {status}")

    config.GOLD_DIR.mkdir(exist_ok=True, parents=True)

    gold_money = con.execute("""
        SELECT month,
               gold_amt / 1e7 AS recovery_cr,
               retry_amt / 1e7 AS retry_cr
        FROM fore_dup_inflation_monthly ORDER BY month
    """).fetchdf()
    gold_money["month"] = gold_money["month"].astype(str).str[:7]
    gold_money.to_csv(config.GOLD_DIR / "monthly_recovery_gold.csv", index=False)

    metrics = con.execute("SELECT * FROM gold_monthly_metrics ORDER BY month").fetchdf()
    metrics["month"] = metrics["month"].astype(str).str[:7]
    metrics.to_csv(config.GOLD_DIR / "gold_monthly_metrics.csv", index=False)

    cohort = con.execute("SELECT * FROM gold_cohort_monthly ORDER BY month").fetchdf()
    cohort["month"] = cohort["month"].astype(str).str[:7]
    cohort.to_parquet(config.GOLD_DIR / "gold_cohort_monthly.parquet", index=False)

    # golden dataset convenience exports
    con.execute(
        "COPY (SELECT * FROM gold_payments_attributed) TO "
        f"'{config.GOLD_DIR.as_posix()}/gold_payments_attributed.parquet' (FORMAT parquet)"
    )
    con.execute(
        "COPY (SELECT payment_id, account_id, borrower_id, pay_month AS month, amount, "
        "attribution_tier, rpc_agent_id, rpc_campaign_channel, ref_reuse_flag FROM gold_payments_attributed) "
        f"TO '{config.GOLD_DIR.as_posix()}/gold_payments_sample.csv' (HEADER, DELIMITER ',')"
    )
    con.execute(
        "COPY (SELECT * FROM gold_monthly_metrics) "
        f"TO '{config.GOLD_DIR.as_posix()}/gold_monthly_metrics.parquet' (FORMAT parquet)"
    )
    con.execute(
        "COPY (SELECT agent_id, canonical_employee_code, canonical_agent_name, canonical_team, "
        "canonical_vendor_id, canonical_status, joined_at FROM clean_agents) "
        f"TO '{config.GOLD_DIR.as_posix()}/gold_agent_registry.csv' (HEADER)"
    )

    # --- row count summary ---------------------------------------------------
    summary = _row_summary(con)

    if verbose:
        print(json.dumps(summary, indent=2))
    con.close()
    return summary


def _row_summary(con: duckdb.DuckDBPyConnection) -> dict:
    summary: dict = {}
    raw = con.execute("""
        SELECT
          (SELECT COUNT(*) FROM stg_borrowers_raw) + (SELECT COUNT(*) FROM stg_accounts_raw)
        + (SELECT COUNT(*) FROM stg_agents_raw) + (SELECT COUNT(*) FROM stg_calls_raw)
        + (SELECT COUNT(*) FROM stg_call_attempts_raw) + (SELECT COUNT(*) FROM stg_call_dispositions_raw)
        + (SELECT COUNT(*) FROM stg_whatsapp_events_raw) + (SELECT COUNT(*) FROM stg_sms_events_raw)
        + (SELECT COUNT(*) FROM stg_field_visits_raw) + (SELECT COUNT(*) FROM stg_promises_to_pay_raw)
        + (SELECT COUNT(*) FROM stg_payments_raw) + (SELECT COUNT(*) FROM stg_daily_targeting_raw)
        + (SELECT COUNT(*) FROM stg_complaints_raw) + (SELECT COUNT(*) FROM stg_account_status_history_raw)
        + (SELECT COUNT(*) FROM stg_agent_sessions_raw)
    """).fetchone()[0]
    summary["raw_rows_staged"] = raw

    for table, label in [
        ("clean_borrowers", "clean_borrowers"),
        ("clean_agents", "clean_agents"),
        ("clean_accounts", "clean_accounts"),
        ("clean_calls", "clean_calls"),
        ("clean_call_dispositions", "clean_call_dispositions"),
        ("clean_payments", "clean_payments"),
        ("gold_payments_attributed", "gold_payments_attributed"),
        ("gold_touchpoints", "gold_touchpoints"),
        ("gold_monthly_metrics", "gold_monthly_metrics"),
        ("gold_cohort_monthly", "gold_cohort_monthly"),
        ("gold_ptp", "gold_ptp"),
    ]:
        summary[label] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]

    d2 = con.execute("SELECT * FROM dq_payments_double_amount").fetchdf()
    summary["payments_excluded_retries_amount"] = (
        float(d2["inflated_amount_by_doubles"].iloc[0]) if len(d2) else None
    )
    summary["doubled_payment_ids"] = (
        int(d2["doubled_success_ids"].iloc[0]) if len(d2) else None
    )
    summary["inflated_amount_by_doubles"] = (
        float(d2["inflated_amount_by_doubles"].iloc[0]) if len(d2) else None
    )
    return summary
