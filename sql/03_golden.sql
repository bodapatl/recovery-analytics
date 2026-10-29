-- ============================================================================
-- 03_golden.sql  |  CLEAN -> GOLDEN + METRIC Marts
-- ----------------------------------------------------------------------------
-- Golden rules:
--   * Business clock = IST. UTC stored; month buckets use IST.
--   * Recovery = SUM of deduplicated SUCCESS payments in cash month.
--   * Attribution = LAST RPC within 14 days (primary), else last contact
--     within 7 days (secondary), else UNATTRIBUTED. The 'reported' logic
--     (latest touch, no window) is ALSO computed for the bias comparison.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- GOLD: ACCOUNT MASTER
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_accounts AS
SELECT a.account_id, a.borrower_id,
       COALESCE(b.name, 'UNKNOWN') AS borrower_name,
       COALESCE(b.phone, 'UNKNOWN') AS borrower_phone,
       b.state AS borrower_state, b.city AS borrower_city,
       a.loan_type, a.principal_amount, a.outstanding_amount, a.dpd,
       a.risk_segment, a.status, a.opened_at,
       CAST(a.dpd AS VARCHAR) AS dpd_band_raw,
       CASE WHEN a.dpd <= 30 THEN '0-30'
            WHEN a.dpd <= 60 THEN '31-60'
            WHEN a.dpd <= 90 THEN '61-90'
            ELSE '90+' END AS dpd_band,
       a.borrower_missing_flag, a.schema_version,
       CAST(YEAR(a.opened_at) AS VARCHAR) || 'Q' || CAST(CEIL(MONTH(a.opened_at)/3.0) AS INT) AS opened_quarter,
       CURRENT_TIMESTAMP AS golden_at
FROM clean_accounts a
LEFT JOIN clean_borrowers b USING (borrower_id);

-- ----------------------------------------------------------------------------
-- GOLD: UNIFIED TOUCHPOINTS (one row per contact attempt on an account)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_touchpoints AS
WITH disp AS (
  SELECT c.event_at_utc AS ts, c.account_id AS account_id,
         'CALL' AS channel_group,
         c.canonical_code AS action_code, c.rpc_flag, c.contact_flag,
         c.call_id, c.agent_id, ca.campaign_id, cp.channel_raw AS campaign_channel
  FROM clean_call_dispositions c
  LEFT JOIN clean_calls     ca USING (call_id)
  LEFT JOIN clean_campaigns cp ON cp.campaign_id = ca.campaign_id
  WHERE c.account_id IS NOT NULL
),
wa AS (
  SELECT event_at_utc AS ts, account_id, 'WHATSAPP' AS channel_group,
         event_type AS action_code, 0 AS rpc_flag,
         CASE WHEN event_type <> 'FAILED' THEN 1 ELSE 0 END AS contact_flag,
         CAST(NULL AS VARCHAR) AS call_id,
         CAST(NULL AS VARCHAR) AS agent_id,
         CAST(NULL AS VARCHAR) AS campaign_id,
         CAST(NULL AS VARCHAR) AS campaign_channel
  FROM clean_whatsapp_events
  WHERE keep_flag AND event_type IN ('SENT','REPLIED') AND account_id IS NOT NULL
),
sms AS (
  SELECT event_at_utc AS ts, account_id, 'SMS' AS channel_group,
         event_type AS action_code, 0 AS rpc_flag,
         CASE WHEN event_type <> 'FAILED' THEN 1 ELSE 0 END AS contact_flag,
         CAST(NULL AS VARCHAR) AS call_id,
         CAST(NULL AS VARCHAR) AS agent_id,
         CAST(NULL AS VARCHAR) AS campaign_id,
         CAST(NULL AS VARCHAR) AS campaign_channel
  FROM clean_sms_events
  WHERE keep_flag AND event_type IN ('SENT') AND account_id IS NOT NULL
),
visits AS (
  SELECT event_at_utc AS ts, account_id, 'FIELD' AS channel_group,
         visit_outcome AS action_code, 1 AS rpc_flag, 1 AS contact_flag,
         CAST(NULL AS VARCHAR) AS call_id, agent_id,
         CAST(NULL AS VARCHAR) AS campaign_id,
         CAST(NULL AS VARCHAR) AS campaign_channel
  FROM clean_field_visits WHERE account_id IS NOT NULL
)
SELECT ts, account_id, channel_group, action_code, rpc_flag, contact_flag,
       call_id, agent_id, campaign_id, campaign_channel
FROM disp
UNION ALL SELECT * FROM wa
UNION ALL SELECT * FROM sms
UNION ALL SELECT * FROM visits;

-- ----------------------------------------------------------------------------
-- GOLD: PAYMENTS WITH ATTRIBUTION
--   primary  : last RPC <= 14 days before payment
--   secondary: last any CONTACT <= 7 days before payment
--   reported : latest touch, unbounded window  (the 'free' attribution used
--              by legacy reporting - computed for the bias comparison)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_payments_attributed AS
SELECT
  p.payment_id, p.account_id, p.borrower_id, p.event_at_utc,
  utc_to_ist(p.event_at_utc) AS event_at_ist,
  CAST(utc_to_ist(p.event_at_utc) AS DATE) AS pay_date,
  DATE_TRUNC('month', utc_to_ist(p.event_at_utc)) AS pay_month,
  p.payment_reference, p.amount, p.payment_method, p.provider_id,
  p.ref_reuse_flag, p.had_id_dup,
  (utc_to_ist(p.event_at_utc) >= DATE '2026-08-01') AS is_partial_month,
  r_agent.agent_id  AS rpc_agent_id,
  r_camp.campaign_id AS rpc_campaign_id,
  r_camp.channel_raw AS rpc_campaign_channel,
  r_camp.strategy_version AS rpc_strategy_version,
  r_ts.ts AS rpc_ts,
  DATE_DIFF('day', r_ts.ts, p.event_at_utc) AS rpc_gap_days,
  s_ts.ts AS contact_ts,
  lt.agent_id AS latest_touch_agent_id,
  lt.channel_group AS latest_touch_channel,
  lt.ts AS latest_touch_ts,
  DATE_DIFF('day', lt.ts, p.event_at_utc) AS latest_touch_gap_days,
  CASE WHEN r_agent.agent_id IS NOT NULL THEN 'RPC_14D'
       WHEN s_ts.ts IS NOT NULL THEN 'CONTACT_7D'
       ELSE 'UNATTRIBUTED' END AS attribution_tier
FROM clean_payments p
LEFT JOIN LATERAL (
  SELECT t.ts, t.agent_id, t.call_id
  FROM gold_touchpoints t
  WHERE t.account_id = p.account_id
    AND t.rpc_flag = 1 AND t.ts <= p.event_at_utc
    AND p.event_at_utc - t.ts <= INTERVAL 14 DAY
  ORDER BY t.ts DESC LIMIT 1
) r_ts ON TRUE
LEFT JOIN LATERAL (
  SELECT t.ts, t.agent_id
  FROM gold_touchpoints t
  WHERE t.account_id = p.account_id
    AND t.contact_flag = 1 AND t.ts <= p.event_at_utc
    AND p.event_at_utc - t.ts <= INTERVAL 7 DAY
  ORDER BY t.ts DESC LIMIT 1
) s_ts ON TRUE
LEFT JOIN LATERAL (
  SELECT t.ts, t.agent_id, t.channel_group
  FROM gold_touchpoints t
  WHERE t.account_id = p.account_id
    AND t.ts <= p.event_at_utc
  ORDER BY t.ts DESC LIMIT 1
) lt ON TRUE
LEFT JOIN clean_calls c_call ON c_call.call_id = (SELECT t.call_id FROM gold_touchpoints t WHERE t.account_id = p.account_id AND t.rpc_flag = 1 AND t.ts <= p.event_at_utc AND p.event_at_utc - t.ts <= INTERVAL 14 DAY ORDER BY t.ts DESC LIMIT 1)
LEFT JOIN clean_campaigns r_camp ON r_camp.campaign_id = c_call.campaign_id
LEFT JOIN clean_agents r_agent ON r_agent.agent_id = r_ts.agent_id
WHERE p.keep_flag;

-- ----------------------------------------------------------------------------
-- GOLD: VERIFIED PTP ("kept" must be verified against cash, not trusted)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_ptp AS
WITH ptp_src AS (
  SELECT 'SYSTEM' AS src_type, ptp_id AS event_key, account_id, agent_id AS ptp_agent_id,
         event_at_utc, promised_amount, promised_date, ptp_status, source AS src_channel
  FROM clean_promises_to_pay
),
ptp_disp AS (
  SELECT 'DISPOSITION' AS src_type, call_id AS event_key, account_id, d.agent_id AS ptp_agent_id,
         d.event_at_utc, CAST(NULL AS DOUBLE) AS promised_amount, CAST(NULL AS DATE) AS promised_date,
         'OPEN' AS ptp_status, 'CALL' AS src_channel
  FROM clean_call_dispositions d
  WHERE d.canonical_code = 'PTP' AND d.account_id IS NOT NULL
),
allptp AS (
  SELECT * FROM ptp_src
  UNION ALL
  SELECT * FROM ptp_disp
),
dedup AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY account_id, CAST(event_at_utc AS DATE)
           ORDER BY CASE src_type WHEN 'SYSTEM' THEN 0 ELSE 1 END, event_key
         ) AS rn
  FROM allptp
),
verified AS (
  SELECT d.*,
         (SELECT MAX(p.amount) FROM gold_payments p
          WHERE p.account_id = d.account_id
            AND p.event_at_utc >= d.event_at_utc
            AND p.event_at_utc <= COALESCE(CAST(d.promised_date AS TIMESTAMP), d.event_at_utc + INTERVAL 14 DAY)
            AND p.event_at_utc <= d.event_at_utc + INTERVAL 45 DAY
         ) AS verified_paid_amount,
         (SELECT MAX(t.agent_id) FROM gold_touchpoints t
          WHERE t.account_id = d.account_id AND t.rpc_flag = 1
            AND t.ts <= d.event_at_utc AND d.event_at_utc - t.ts <= INTERVAL 14 DAY
         ) AS attributed_rpc_agent_id
  FROM dedup d WHERE d.rn = 1
)
SELECT event_key, src_type, account_id, ptp_agent_id, event_at_utc,
       utc_to_ist(event_at_utc) AS event_at_ist, promised_amount, promised_date,
       ptp_status, src_channel,
       DATE_TRUNC('month', utc_to_ist(event_at_utc)) AS ptp_month,
       (verified_paid_amount IS NOT NULL AND verified_paid_amount > 0) AS kept_verified_flag,
       verified_paid_amount,
       (ptp_status = 'KEPT') AS status_says_kept_flag,
       (ptp_status = 'KEPT' AND NOT (verified_paid_amount IS NOT NULL AND verified_paid_amount > 0))
         AS kept_status_without_cash_flag,
       attributed_rpc_agent_id,
       CURRENT_TIMESTAMP AS golden_at
FROM verified;

-- ----------------------------------------------------------------------------
-- GOLD: DAILY AGENT HOURS (IST)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE gold_agent_hours AS
SELECT s.agent_id,
       CAST(utc_to_ist(s.login_at_utc) AS DATE) AS work_date,
       DATE_TRUNC('month', CAST(utc_to_ist(s.login_at_utc) AS DATE)) AS work_month,
       s.session_channel, s.session_hours_capped, s.logout_before_login_flag,
       s.login_at_utc, s.logout_at_utc
FROM clean_agent_sessions s
WHERE s.agent_id IS NOT NULL;

CREATE OR REPLACE TABLE gold_agent_tenure AS
SELECT agent_id,
       DATE_DIFF('month', CAST(joined_at AS DATE), DATE '2026-01-01') AS tenure_months_at_start,
       CASE WHEN DATE_DIFF('month', CAST(joined_at AS DATE), DATE '2026-01-01') <= 3 THEN '0-3m'
            WHEN DATE_DIFF('month', CAST(joined_at AS DATE), DATE '2026-01-01') <= 9 THEN '4-9m'
            WHEN DATE_DIFF('month', CAST(joined_at AS DATE), DATE '2026-01-01') <= 18 THEN '10-18m'
            ELSE '18m+' END AS tenure_band
FROM clean_agents;

-- ----------------------------------------------------------------------------
-- GOLD: MONTHLY METRICS (executive layer, one row per month)
-- Denominator rule (survivorship-proof): every account opened BEFORE the
-- month end is in the pool for that month, regardless of later status.
-- Built as sequential monthly marts (month_*) and joined at the end, so every
-- single aggregate is inspectable and testable on its own.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE months AS
SELECT DISTINCT pay_month AS month FROM gold_payments_attributed;

CREATE OR REPLACE TABLE month_pool AS
WITH pool AS (
  SELECT DISTINCT m.month, a.account_id, a.outstanding_amount
  FROM months m JOIN clean_accounts a
    ON a.opened_at <= m.month + INTERVAL 1 MONTH
)
SELECT month, COUNT(*) AS n_pool_accounts, SUM(outstanding_amount) AS pool_outstanding
FROM pool GROUP BY month ORDER BY month;

CREATE OR REPLACE TABLE month_pay AS
SELECT pay_month AS month,
       SUM(amount) AS recovery_amt,
       COUNT(*) AS recovery_count,
       COUNT(DISTINCT account_id) AS recovery_accounts,
       SUM(CASE WHEN attribution_tier = 'RPC_14D' THEN amount ELSE 0 END) AS amt_rpc14d,
       SUM(CASE WHEN attribution_tier = 'CONTACT_7D' THEN amount ELSE 0 END) AS amt_contact7d,
       SUM(CASE WHEN attribution_tier = 'UNATTRIBUTED' THEN amount ELSE 0 END) AS amt_unattributed,
       SUM(CASE WHEN latest_touch_gap_days > 30 THEN amount ELSE 0 END) AS amt_old_touch_attributed
FROM gold_payments_attributed GROUP BY pay_month ORDER BY pay_month;

CREATE OR REPLACE TABLE month_raw AS
SELECT m.month,
       SUM(CASE WHEN pm.payment_status IN ('SUCCESS','PENDING','REVERSED') THEN pm.amount ELSE 0 END) AS raw_reported_amt_all,
       SUM(CASE WHEN pm.payment_status = 'SUCCESS' THEN pm.amount ELSE 0 END) AS raw_success_amt,
       SUM(CASE WHEN pm.payment_status = 'PENDING' THEN pm.amount ELSE 0 END) AS raw_pending_amt,
       SUM(CASE WHEN pm.payment_status = 'REVERSED' THEN pm.amount ELSE 0 END) AS raw_reversed_amt,
       COUNT(*) AS raw_rows
FROM months m
LEFT JOIN stg_payments pm
  ON DATE_TRUNC('month', utc_to_ist(pm.event_at_utc)) = m.month
GROUP BY m.month ORDER BY m.month;

CREATE OR REPLACE TABLE month_retry AS
SELECT DATE_TRUNC('month', utc_to_ist(cp.event_at_utc)) AS month,
       SUM(CASE WHEN cp.had_id_dup THEN cp.amount ELSE 0 END) AS retry_kept_amt,
       SUM(CASE WHEN cp.had_id_dup THEN 1 ELSE 0 END) AS n_retry_kept
FROM clean_payments cp
WHERE cp.keep_flag
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_contact AS
SELECT DATE_TRUNC('month', CAST(utc_to_ist(t.ts) AS DATE)) AS month,
       COUNT(DISTINCT t.account_id) AS n_contacted,
       SUM(CASE WHEN t.contact_flag = 1 THEN 1 ELSE 0 END) AS n_contact_events,
       SUM(CASE WHEN t.rpc_flag = 1 THEN 1 ELSE 0 END) AS n_rpc_events,
       COUNT(DISTINCT CASE WHEN t.rpc_flag = 1 THEN t.account_id END) AS n_rpc_accounts
FROM gold_touchpoints t
GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_target AS
SELECT DATE_TRUNC('month', target_date) AS month,
       COUNT(DISTINCT account_id) AS n_targeted,
       COUNT(*) AS n_target_rows
FROM clean_daily_targeting GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_calls AS
SELECT DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS month,
       COUNT(*) AS n_calls,
       SUM(CASE WHEN call_status = 'ANSWERED' THEN 1 ELSE 0 END) AS n_answered,
       AVG(CASE WHEN call_status = 'ANSWERED' THEN duration_sec END) AS avg_talk_sec
FROM clean_calls GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_attempts AS
SELECT DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS month,
       COUNT(*) AS n_attempts,
       SUM(CASE WHEN attempt_status = 'CONNECTED' THEN 1 ELSE 0 END) AS n_connected
FROM clean_call_attempts GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_ptp AS
SELECT ptp_month AS month,
       COUNT(*) AS n_ptp_events,
       COUNT(DISTINCT account_id) AS n_ptp_accounts,
       SUM(CASE WHEN kept_verified_flag THEN 1 ELSE 0 END) AS n_ptp_kept_verified,
       SUM(CASE WHEN status_says_kept_flag THEN 1 ELSE 0 END) AS n_ptp_status_kept,
       SUM(CASE WHEN kept_status_without_cash_flag THEN 1 ELSE 0 END) AS n_ptp_kept_no_cash
FROM gold_ptp GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_hours AS
SELECT work_month AS month,
       SUM(session_hours_capped) AS agent_hours,
       COUNT(DISTINCT agent_id) AS n_agents_active
FROM gold_agent_hours GROUP BY 1 ORDER BY 1;

CREATE OR REPLACE TABLE month_digital AS
SELECT COALESCE(w.month, s.month) AS month,
       COALESCE(w.wa_sent, 0) AS wa_sent,
       COALESCE(w.wa_click, 0) AS wa_click,
       COALESCE(w.wa_replied, 0) AS wa_replied,
       COALESCE(s.sms_sent, 0) AS sms_sent
FROM (
  SELECT DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS month,
         SUM(CASE WHEN event_type='SENT' THEN 1 ELSE 0 END) AS wa_sent,
         SUM(CASE WHEN event_type='PAYMENT_CLICK' THEN 1 ELSE 0 END) AS wa_click,
         SUM(CASE WHEN event_type='REPLIED' THEN 1 ELSE 0 END) AS wa_replied
  FROM clean_whatsapp_events WHERE keep_flag GROUP BY 1
) w
FULL JOIN (
  SELECT DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS month,
         SUM(CASE WHEN event_type='SENT' THEN 1 ELSE 0 END) AS sms_sent
  FROM clean_sms_events WHERE keep_flag GROUP BY 1
) s USING (month)
ORDER BY month;

CREATE OR REPLACE TABLE month_channel AS
WITH attributed AS (
  SELECT p.pay_month, p.amount,
         CASE
           WHEN p.rpc_campaign_channel IS NOT NULL THEN p.rpc_campaign_channel
           WHEN EXISTS (SELECT 1 FROM gold_touchpoints t WHERE t.account_id = p.account_id
                        AND t.ts <= p.event_at_utc AND p.event_at_utc - t.ts <= INTERVAL 7 DAY
                        AND t.channel_group = 'FIELD') THEN 'FIELD'
           WHEN EXISTS (SELECT 1 FROM gold_touchpoints t WHERE t.account_id = p.account_id
                        AND t.ts <= p.event_at_utc AND p.event_at_utc - t.ts <= INTERVAL 7 DAY
                        AND t.channel_group = 'WHATSAPP') THEN 'WHATSAPP'
           WHEN EXISTS (SELECT 1 FROM gold_touchpoints t WHERE t.account_id = p.account_id
                        AND t.ts <= p.event_at_utc AND p.event_at_utc - t.ts <= INTERVAL 7 DAY
                        AND t.channel_group = 'SMS') THEN 'SMS'
           ELSE 'VOICE' END AS channel
  FROM gold_payments_attributed p
)
SELECT pay_month AS month,
       SUM(CASE WHEN channel IN ('VOICE','IVR','DIALER','AGENTIC_VOICE') THEN amount ELSE 0 END) AS amt_voice,
       SUM(CASE WHEN channel = 'WHATSAPP' THEN amount ELSE 0 END) AS amt_whatsapp,
       SUM(CASE WHEN channel = 'SMS' THEN amount ELSE 0 END) AS amt_sms,
       SUM(CASE WHEN channel = 'FIELD' THEN amount ELSE 0 END) AS amt_field,
       SUM(CASE WHEN channel = 'MIXED' OR channel = 'OTHER' THEN amount ELSE 0 END) AS amt_other
FROM attributed
GROUP BY pay_month ORDER BY pay_month;

CREATE OR REPLACE TABLE gold_monthly_metrics AS
SELECT m.month,
  po.n_pool_accounts, po.pool_outstanding,
  pay.recovery_amt, pay.recovery_count, pay.recovery_accounts,
  pay.amt_rpc14d, pay.amt_contact7d, pay.amt_unattributed, pay.amt_old_touch_attributed,
  raw.raw_reported_amt_all, raw.raw_success_amt, rep.retry_kept_amt AS raw_retry_kept_amt,
  raw.raw_pending_amt, raw.raw_reversed_amt, raw.raw_rows,
  ct.n_contacted, ct.n_contact_events, ct.n_rpc_events, ct.n_rpc_accounts,
  tg.n_targeted, tg.n_target_rows,
  ca.n_calls, ca.n_answered, ca.avg_talk_sec,
  att.n_attempts, att.n_connected,
  pt.n_ptp_events, pt.n_ptp_accounts, pt.n_ptp_kept_verified, pt.n_ptp_status_kept,
  pt.n_ptp_kept_no_cash,
  hm.agent_hours, hm.n_agents_active,
  dg.wa_sent, dg.wa_click, dg.wa_replied, dg.sms_sent,
  ch.amt_voice, ch.amt_whatsapp, ch.amt_sms, ch.amt_field, ch.amt_other,
  CURRENT_TIMESTAMP AS golden_at
FROM months m
LEFT JOIN month_pool po ON po.month = m.month
LEFT JOIN month_pay pay ON pay.month = m.month
LEFT JOIN month_raw raw ON raw.month = m.month
LEFT JOIN month_retry rep ON rep.month = m.month
LEFT JOIN month_contact ct ON ct.month = m.month
LEFT JOIN month_target tg ON tg.month = m.month
LEFT JOIN month_calls ca ON ca.month = m.month
LEFT JOIN month_attempts att ON att.month = m.month
LEFT JOIN month_ptp pt ON pt.month = m.month
LEFT JOIN month_hours hm ON hm.month = m.month
LEFT JOIN month_digital dg ON dg.month = m.month
LEFT JOIN month_channel ch ON ch.month = m.month
ORDER BY m.month;
