"""Quick console view of golden marts (dev diagnostics)."""
from src import db

con = db.connect(readonly=True)


def show(title, sql):
    print(f"=== {title} ===")
    df = con.execute(sql).fetchdf()
    print(df.to_string(index=False))
    print()


show("MONTH_RETRY (dedup cost)", """
SELECT strftime(month, '%Y-%m') AS m, round(retry_kept_amt/1e7, 2) AS retry_cr, n_retry_kept
FROM month_retry ORDER BY 1""")

show("MONTH_PAY (gold recovery, attribution tiers, Cr)", """
SELECT strftime(month, '%Y-%m') AS m, round(recovery_amt/1e7, 2) AS cr, recovery_count AS n,
       round(amt_rpc14d/1e7, 2) AS rpc14d, round(amt_contact7d/1e7, 2) AS c7d,
       round(amt_unattributed/1e7, 2) AS unattr, round(amt_old_touch_attributed/1e7, 2) AS stale
FROM month_pay ORDER BY 1""")

show("MONTH_RAW reported variants (Cr)", """
SELECT strftime(month, '%Y-%m') AS m, round(raw_success_amt/1e7, 2) AS succ,
       round(raw_pending_amt/1e7, 2) AS pend, round(raw_reversed_amt/1e7, 2) AS rev,
       round(raw_reported_amt_all/1e7, 2) AS all3
FROM month_raw ORDER BY 1""")

show("MONTH_METRICS funnel + pool", """
SELECT strftime(month, '%Y-%m') AS m, n_targeted, n_contacted, n_rpc_accounts, n_ptp_accounts,
       n_ptp_kept_verified, recovery_accounts
FROM gold_monthly_metrics ORDER BY 1""")

show("CHANNEL attribution (Cr)", """
SELECT strftime(month, '%Y-%m') AS m, round(amt_voice/1e7,2) voice, round(amt_whatsapp/1e7,2) wa,
       round(amt_sms/1e7,2) sms, round(amt_field/1e7,2) field
FROM month_channel ORDER BY 1""")

show("AGENT hours + productivity", """
SELECT strftime(month, '%Y-%m') AS m, round(agent_hours, 0) AS hrs, n_agents,
       round(recovery_amt / agent_hours, 0) AS rec_per_agent_hr
FROM fore_agent_monthly ORDER BY 1""")

show("TZ misclassification", """SELECT * FROM fore_tz_wrong_bucket""")

show("Strategy waves", """SELECT * FROM fore_strategy_wave""")

show("Campaign strategy mix by month", """
SELECT strftime(month, '%Y-%m') AS m, strategy_version, n_accounts
FROM fore_campaign_monthly ORDER BY 1""")

con.close()
