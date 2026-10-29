-- ============================================================================
-- 04_forensics.sql  |  Forensic batteries - numbers, not opinions
-- ----------------------------------------------------------------------------
-- A. duplicate payments        D. vendor mapping changes     G. denominators
-- B. attribution errors        E. agent identity problems    H. timezone tests
-- C. timezone problems         F. portfolio mix changes      I. campaign logic
-- ============================================================================

-- A+. DUPLICATE PAYMENTS: monthly retry inflation + how big it is for MoM
--    (comes straight from the dedup ledger on clean_payments)
CREATE OR REPLACE TABLE fore_dup_inflation_monthly AS
SELECT DATE_TRUNC('month', utc_to_ist(event_at_utc)) AS month,
       SUM(amount) AS gold_amt,
       SUM(CASE WHEN had_id_dup THEN amount ELSE 0 END) AS retry_amt,
       SUM(CASE WHEN had_id_dup THEN 1 ELSE 0 END) AS n_retry_rows,
       COUNT(*) AS n_economic_payments
FROM clean_payments
GROUP BY 1 ORDER BY 1;

-- A2. retry share by month (the smoking gun for fake MoM improvement)
CREATE OR REPLACE TABLE fore_dup_monthly AS
WITH dupflags AS (
  SELECT stg_payments.*,
    EXISTS (SELECT 1 FROM clean_payments cp
            WHERE cp.payment_id = stg_payments.payment_id
              AND cp.had_id_dup) AS is_retry
  FROM stg_payments
  WHERE payment_status='SUCCESS'
)
SELECT DATE_TRUNC('month', utc_to_ist(event_at_utc)) AS month,
       COUNT(*) AS n_success,
       SUM(amount) AS total_amt,
       SUM(CASE WHEN is_retry THEN amount ELSE 0 END) AS retry_amt,
       SUM(CASE WHEN is_retry THEN 1 ELSE 0 END) AS n_retry
FROM dupflags
GROUP BY 1 ORDER BY 1;

-- B. ATTRIBUTION ERROR: how much recovery the 'reported' latest-touch logic
--    attributes vs the windowed golden logic
CREATE OR REPLACE TABLE fore_attribution_monthly AS
SELECT pay_month AS month,
       SUM(amount) AS gold_amt,
       SUM(CASE WHEN attribution_tier='RPC_14D' THEN amount ELSE 0 END) AS amt_rpc14d,
       SUM(CASE WHEN attribution_tier='CONTACT_7D' THEN amount ELSE 0 END) AS amt_contact7d,
       SUM(CASE WHEN attribution_tier='UNATTRIBUTED' THEN amount ELSE 0 END) AS amt_unattributed,
       SUM(CASE WHEN latest_touch_gap_days > 30 THEN amount ELSE 0 END) AS amt_attributed_stale
FROM gold_payments_attributed GROUP BY 1 ORDER BY 1;

-- B2. campaign/channel credit distortion: the stale 'latest-touch' window
--     silently sends credit to whatever the borrower touched last, however long
--     ago. We quantify how much recovery lands on touches older than 30 days.
CREATE OR REPLACE TABLE fore_campaign_credit_monthly AS
SELECT pay_month AS month,
       SUM(CASE WHEN attribution_tier = 'RPC_14D' THEN amount ELSE 0 END) AS amt_credits_rpc14d,
       SUM(CASE WHEN attribution_tier IN ('CONTACT_7D','UNATTRIBUTED') THEN amount ELSE 0 END) AS amt_credits_weak,
       SUM(CASE WHEN latest_touch_gap_days > 30 THEN amount ELSE 0 END) AS amt_credits_stale_touch,
       COUNT(*) AS n_payments
FROM gold_payments_attributed
GROUP BY pay_month ORDER BY pay_month;

-- C/H. TIMEZONE: share of events that fall outside business hours ONLY after
--      treating naive timestamps at face value vs tz-normalized
CREATE OR REPLACE TABLE fore_timezone_hourly AS
SELECT
  CASE WHEN tz='UTC' THEN 'UTC' WHEN tz='Asia/Kolkata' THEN 'KOLKATA' ELSE 'DUBAI' END AS tz_bucket,
  CAST(EXTRACT(hour FROM event_at_local) AS INT) AS naive_local_hour,
  CAST(EXTRACT(hour FROM utc_to_ist(tz_to_utc(event_at_local, tz))) AS INT) AS ist_hour,
  COUNT(*) AS n_calls,
  SUM(CASE WHEN call_status='ANSWERED' THEN 1 ELSE 0 END) AS n_answered
FROM clean_calls
GROUP BY 1,2,3;

CREATE OR REPLACE TABLE fore_tz_wrong_bucket AS
SELECT
  SUM(CASE WHEN EXTRACT(hour FROM event_at_local) BETWEEN 9 AND 21
            AND EXTRACT(hour FROM utc_to_ist(tz_to_utc(event_at_local, tz))) BETWEEN 9 AND 21
           THEN 0 ELSE 1 END) AS calls_misclassified_biz_hours,
  COUNT(*) AS total_calls
FROM clean_calls;

-- D. VENDOR MAPPING: disposition_version mix by vendor by month
CREATE OR REPLACE TABLE fore_vendor_version_monthly AS
SELECT DATE_TRUNC('month', CAST(utc_to_ist(ca.event_at_utc) AS DATE)) AS month,
       vt.vendor_name,
       cd.disposition_version,
       COUNT(*) AS n
FROM clean_call_attempts ca
JOIN clean_vendor_telephony vt USING (vendor_id)
LEFT JOIN clean_calls c ON c.call_id = ca.call_id
LEFT JOIN clean_call_dispositions cd ON cd.call_id = c.call_id
GROUP BY 1,2,3 ORDER BY 1,2,3;

-- E. AGENT IDENTITY: sessions/calls/visits referencing agents missing in registry
CREATE OR REPLACE TABLE fore_agent_orphans AS
SELECT 'calls' AS evt, COUNT(*) AS orphan_rows
FROM clean_calls c LEFT JOIN clean_agents a USING (agent_id)
WHERE c.agent_id IS NOT NULL AND a.agent_id IS NULL
UNION ALL
SELECT 'sessions', COUNT(*)
FROM clean_agent_sessions s LEFT JOIN clean_agents a USING (agent_id)
WHERE s.agent_id IS NOT NULL AND a.agent_id IS NULL
UNION ALL
SELECT 'visits', COUNT(*)
FROM clean_field_visits v LEFT JOIN clean_agents a USING (agent_id)
WHERE v.agent_id IS NOT NULL AND a.agent_id IS NULL;

-- F. PORTFOLIO MIX: cohort cross sections (opened_quarter x dpd_band x month)
CREATE OR REPLACE TABLE gold_cohort_monthly AS
WITH months AS (SELECT DISTINCT pay_month AS month FROM gold_payments_attributed),
cohorts AS (
  SELECT DISTINCT a.opened_quarter, a.dpd_band, a.risk_segment, a.loan_type, a.account_id, a.outstanding_amount
  FROM gold_accounts a
),
 memb AS (
  SELECT m.month, c.opened_quarter, c.dpd_band, c.risk_segment, c.loan_type,
         SUM(1) AS n_accounts, SUM(c.outstanding_amount) AS outstanding
  FROM months m JOIN cohorts c ON TRUE
  WHERE EXISTS (SELECT 1 FROM gold_accounts a2
               WHERE a2.account_id = c.account_id
                 AND a2.opened_at <= m.month + INTERVAL 1 MONTH)
  GROUP BY ALL
),
pay AS (
  SELECT pay_month AS month, a.opened_quarter, a.dpd_band, a.risk_segment, a.loan_type,
         SUM(p.amount) AS recovery_amt, COUNT(*) AS n_payments
  FROM gold_payments_attributed p
  JOIN gold_accounts a USING (account_id)
  GROUP BY ALL
),
ctact AS (
  SELECT DATE_TRUNC('month', CAST(utc_to_ist(t.ts) AS DATE)) AS month, a.opened_quarter, a.dpd_band, a.risk_segment, a.loan_type,
         SUM(CASE WHEN t.contact_flag = 1 THEN 1 ELSE 0 END) AS n_contacts,
         SUM(CASE WHEN t.rpc_flag = 1 THEN 1 ELSE 0 END) AS n_rpcs,
         COUNT(DISTINCT CASE WHEN t.rpc_flag = 1 THEN t.account_id END) AS n_rpc_accounts
  FROM gold_touchpoints t JOIN gold_accounts a USING (account_id)
  GROUP BY ALL
)
SELECT m.month, m.opened_quarter, m.dpd_band, m.risk_segment, m.loan_type,
       m.n_accounts, m.outstanding,
       COALESCE(p.recovery_amt, 0) AS recovery_amt,
       COALESCE(p.n_payments, 0) AS n_payments,
       c.n_contacts, c.n_rpcs, c.n_rpc_accounts
FROM memb m
LEFT JOIN pay p USING (month, opened_quarter, dpd_band, risk_segment, loan_type)
LEFT JOIN ctact c USING (month, opened_quarter, dpd_band, risk_segment, loan_type)
ORDER BY month, opened_quarter, dpd_band;

-- G. DENOMINATOR MANIPULATION probe: targeted vs contacted vs attempted
CREATE OR REPLACE TABLE fore_denominator_monthly AS
SELECT tg.month,
       tg.n_targeted,
       tg.n_target_status_contacted,
       tg.n_target_status_queued,
       tg.n_target_status_expired,
       tg.n_target_status_skipped,
       ct.n_contacted AS n_contacted_any_channel,
       "at".n_connected AS n_connected_calls,
       (SELECT COUNT(DISTINCT account_id) FROM gold_payments_attributed p
        WHERE p.pay_month = tg.month) AS recovery_accounts
FROM (
  SELECT DATE_TRUNC('month', target_date) AS month,
         COUNT(DISTINCT account_id) AS n_targeted,
         COUNT(DISTINCT CASE WHEN target_status='CONTACTED' THEN account_id END) AS n_target_status_contacted,
         COUNT(DISTINCT CASE WHEN target_status='QUEUED' THEN account_id END) AS n_target_status_queued,
         COUNT(DISTINCT CASE WHEN target_status='EXPIRED' THEN account_id END) AS n_target_status_expired,
         COUNT(DISTINCT CASE WHEN target_status='SKIPPED' THEN account_id END) AS n_target_status_skipped
  FROM clean_daily_targeting GROUP BY 1
) tg
LEFT JOIN (
  SELECT DATE_TRUNC('month', CAST(utc_to_ist(t.ts) AS DATE)) AS month,
         COUNT(DISTINCT t.account_id) AS n_contacted
  FROM gold_touchpoints t WHERE t.contact_flag = 1 GROUP BY 1
) ct ON ct.month = tg.month
LEFT JOIN (
  SELECT DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS month,
         COUNT(DISTINCT account_id) AS n_connected
  FROM clean_call_attempts WHERE attempt_status='CONNECTED' GROUP BY 1
) "at" ON "at".month = tg.month
ORDER BY tg.month;

-- I. CAMPAIGN LOGIC: strategy wave dates (v2 onwards = post-change period)
CREATE OR REPLACE TABLE fore_strategy_wave AS
SELECT strategy_version, COUNT(*) AS n_campaigns,
       MIN(start_at_utc) AS first_start, MAX(start_at_utc) AS last_start,
       SUM(CASE WHEN channel_raw='MIXED' THEN 1 ELSE 0 END) AS n_mixed_channel,
       SUM(CASE WHEN channel_raw='FIELD' THEN 1 ELSE 0 END) AS n_field_channel,
       SUM(CASE WHEN channel_raw='VOICE' THEN 1 ELSE 0 END) AS n_voice_channel,
       SUM(CASE WHEN channel_raw='WHATSAPP' THEN 1 ELSE 0 END) AS n_whatsapp_channel,
       SUM(CASE WHEN channel_raw='SMS' THEN 1 ELSE 0 END) AS n_sms_channel,
       AVG(DATE_DIFF('day', start_at_utc, end_at_local)) AS avg_campaign_days
FROM clean_campaigns GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE fore_campaign_monthly AS
SELECT DATE_TRUNC('month', dt.target_date) AS month, cp.strategy_version,
       COUNT(DISTINCT dt.account_id) AS n_accounts
FROM clean_daily_targeting dt JOIN clean_campaigns cp USING (campaign_id)
GROUP BY 1,2 ORDER BY 1,2;

-- Agent productivity monthly (gold): recovery per agent-hour
CREATE OR REPLACE TABLE fore_agent_monthly AS
WITH hrs AS (
  SELECT work_month AS month, SUM(session_hours_capped) AS agent_hours,
         COUNT(DISTINCT agent_id) AS n_agents
  FROM gold_agent_hours GROUP BY 1
),
rec AS (
  SELECT month, SUM(recovery_amt) AS recovery_amt
  FROM gold_monthly_metrics GROUP BY 1
)
SELECT h.month, h.agent_hours, h.n_agents, COALESCE(r.recovery_amt, 0) AS recovery_amt
FROM hrs h LEFT JOIN rec r USING (month) ORDER BY h.month;
