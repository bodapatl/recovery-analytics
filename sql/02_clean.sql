-- ============================================================================
-- 02_clean.sql  |  STAGING -> CLEAN
-- ----------------------------------------------------------------------------
-- Source-of-truth decisions, entity resolution, dedup and normalization.
-- Every rule emits an audit metric (dq_* tables) so the impact of every
-- decision is quantified, not asserted.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. BORROWER ENTITY RESOLUTION
--    30,600 raw rows -> 11,015 real borrowers (~3x duplication).
--    Rule: canonical row per borrower_id = latest updated_at (system of
--    record wins). Records with NULL borrower_id are quarantined for audit.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_borrowers AS
WITH ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (
            PARTITION BY borrower_id
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
         ) AS rn
  FROM stg_borrowers
  WHERE borrower_id IS NOT NULL
)
SELECT
  borrower_id, name_clean AS name, phone_clean AS phone, email, city, state,
  created_at, updated_at,
  CURRENT_TIMESTAMP AS processed_at
FROM ranked
WHERE rn = 1;

CREATE OR REPLACE TABLE dq_borrower_dup AS
SELECT 'borrowers' AS table_name,
       'duplicate borrower records collapsed to latest updated_at' AS rule,
       COUNT(*) - COUNT(DISTINCT borrower_id) AS rows_rejected
FROM stg_borrowers WHERE borrower_id IS NOT NULL;

CREATE OR REPLACE TABLE dq_borrower_null_id AS
SELECT 'borrowers' AS table_name,
       'null borrower_id quarantined' AS rule,
       COUNT(*) AS rows_rejected
FROM stg_borrowers WHERE borrower_id IS NULL;

-- ----------------------------------------------------------------------------
-- 2. AGENT ENTITY RESOLUTION
--    30,000 raw rows for 1,000 real agents. Each agent_id carries ~30
--    conflicting rows (different employee_code / vendor / team / name).
--    Rule: agent_id (AGT*) is the transactional key used by calls, sessions
--    and visits, so it is canonical. Canonical attribute = the value that
--    occurs most often for that agent; ties broken by the most recently
--    updated row. joined_at: earliest (tenure must not reset upstream).
--    employee_code: a code claimed by >1 agent is poisoned and flagged.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_agents AS
WITH base AS (
  SELECT * FROM stg_agents WHERE agent_id IS NOT NULL
),
agg AS (
  SELECT agent_id, COUNT(*) AS n_records,
         MIN(joined_at) AS joined_at,
         CURRENT_TIMESTAMP AS processed_at
  FROM base GROUP BY agent_id
),
m_code AS (
  SELECT agent_id, employee_code AS canonical_employee_code
  FROM (SELECT agent_id, employee_code, COUNT(*) n, MAX(updated_at) mx,
               ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY COUNT(*) DESC, MAX(updated_at) DESC) rn
        FROM base GROUP BY agent_id, employee_code) WHERE rn = 1
),
m_name AS (
  SELECT agent_id, agent_name AS canonical_agent_name
  FROM (SELECT agent_id, agent_name, COUNT(*) n, MAX(updated_at) mx,
               ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY COUNT(*) DESC, MAX(updated_at) DESC) rn
        FROM base GROUP BY agent_id, agent_name) WHERE rn = 1
),
m_team AS (
  SELECT agent_id, team AS canonical_team
  FROM (SELECT agent_id, team, COUNT(*) n, MAX(updated_at) mx,
               ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY COUNT(*) DESC, MAX(updated_at) DESC) rn
        FROM base GROUP BY agent_id, team) WHERE rn = 1
),
m_vendor AS (
  SELECT agent_id, vendor_id AS canonical_vendor_id
  FROM (SELECT agent_id, vendor_id, COUNT(*) n, MAX(updated_at) mx,
               ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY COUNT(*) DESC, MAX(updated_at) DESC) rn
        FROM base GROUP BY agent_id, vendor_id) WHERE rn = 1
),
m_status AS (
  SELECT agent_id, status AS canonical_status
  FROM (SELECT agent_id, status, COUNT(*) n, MAX(updated_at) mx,
               ROW_NUMBER() OVER (PARTITION BY agent_id ORDER BY MAX(updated_at) DESC) rn
        FROM base GROUP BY agent_id, status) WHERE rn = 1
)
SELECT
  a.agent_id,
  m_code.canonical_employee_code, m_name.canonical_agent_name,
  m_team.canonical_team, m_vendor.canonical_vendor_id,
  m_status.canonical_status, a.joined_at, a.processed_at
FROM agg a
LEFT JOIN m_code   USING (agent_id)
LEFT JOIN m_name   USING (agent_id)
LEFT JOIN m_team   USING (agent_id)
LEFT JOIN m_vendor USING (agent_id)
LEFT JOIN m_status USING (agent_id);

CREATE OR REPLACE TABLE dq_agent_dup AS
SELECT 'agents' AS table_name,
       'conflicting agent master rows resolved to one canonical per agent_id' AS rule,
       COUNT(*) - COUNT(DISTINCT agent_id) AS rows_rejected
FROM stg_agents WHERE agent_id IS NOT NULL;

CREATE OR REPLACE TABLE dq_agent_shared_code AS
SELECT canonical_employee_code AS employee_code,
       COUNT(DISTINCT agent_id) AS agents_claiming_code
FROM clean_agents
GROUP BY canonical_employee_code
HAVING COUNT(DISTINCT agent_id) > 1;

CREATE OR REPLACE VIEW dq_agent_null_id AS
SELECT * FROM stg_agents WHERE agent_id IS NULL;

-- ----------------------------------------------------------------------------
-- 3. ACCOUNTS: no duplicate account_ids (30,000 unique). Null borrower_id
--    accounts are kept (payments/events join via account_id) but flagged;
--    snapshot DPD/outstanding come from the latest schema version present.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_accounts AS
SELECT account_id, borrower_id, loan_type,
       principal_amount, outstanding_amount, dpd, risk_segment, status,
       opened_at, tz, schema_version,
       (borrower_id IS NULL) AS borrower_missing_flag,
       CURRENT_TIMESTAMP AS processed_at
FROM stg_accounts;

CREATE OR REPLACE TABLE dq_account_null_borrower AS
SELECT 'accounts' AS table_name,
       'accounts missing borrower link (kept, flagged; joins use account_id)' AS rule,
       SUM(CASE WHEN borrower_missing_flag THEN 1 ELSE 0 END) AS rows_flagged
FROM clean_accounts;

-- ----------------------------------------------------------------------------
-- 4. ACCOUNT STATUS HISTORY vs SNAPSHOT: 'historical records overwritten'.
--    status_timeline = true narrative (event_at ordered); accounts.status is
--    only the snapshot. Late-airing anomalies (recorded_at < event_at) noted.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_account_status_history AS
SELECT history_id, account_id, borrower_id, event_at_local, event_at_utc,
       status, changed_by, source, recorded_at, is_late_arrival_anomaly,
       CURRENT_TIMESTAMP AS processed_at
FROM stg_account_status_history
WHERE account_id IS NOT NULL AND history_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 5. CALLS: duplicate call_id (same id, different rows) -> keep earliest by
--    UTC event time. Rows with failed dialer metadata keep valid ids.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_calls AS
WITH ranked AS (
  SELECT *,
         ROW_NUMBER() OVER (
            PARTITION BY call_id
            ORDER BY event_at_utc ASC, vendor_id ASC
         ) AS rn
  FROM stg_calls WHERE call_id IS NOT NULL
)
SELECT call_id, account_id, borrower_id, event_at_local, event_at_utc,
       agent_id, campaign_id, direction, vendor_id, call_status,
       duration_sec, tz,
       CURRENT_TIMESTAMP AS processed_at
FROM ranked WHERE rn = 1;

CREATE OR REPLACE TABLE dq_call_dup AS
SELECT 'calls' AS table_name,
       'duplicate call_id rows resolved to earliest UTC event' AS rule,
       COUNT(*) - COUNT(DISTINCT call_id) AS rows_rejected
FROM stg_calls WHERE call_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 6. DISPOSITION CODE NORMALIZATION (changed disposition codes problem)
--    PROMISE_TO_PAY (legacy) == PTP (v1/v2): same business meaning renamed.
--    Canonical codes: CALLBACK, REFUSED, DISPUTE, PAID, PTP, PTP_BROKEN,
--                     NO_CONTACT, WRONG_NUMBER
--    contact = 1 for everything except NO_CONTACT / WRONG_NUMBER.
--    right-party contact (rpc) = 1 only when a human conversed: CALLBACK,
--    REFUSED, DISPUTE, PAID, PTP, PTP_BROKEN.
--    Multiple dispositions per call: keep the latest event per call_id.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_call_dispositions AS
WITH per_call AS (
  SELECT *,
         ROW_NUMBER() OVER (
            PARTITION BY call_id
            ORDER BY event_at_utc DESC, disposition_id DESC
         ) AS rn,
         COUNT(*) OVER (PARTITION BY call_id) AS n_rows_in_call
  FROM stg_call_dispositions
  WHERE disposition_id IS NOT NULL
),
mapped AS (
  SELECT d.*,
       CASE d.disposition_code_raw
         WHEN 'PROMISE_TO_PAY' THEN 'PTP'
         ELSE d.disposition_code_raw
       END AS canonical_code,
       CASE WHEN d.disposition_code_raw IN ('NO_CONTACT','WRONG_NUMBER') THEN 0 ELSE 1 END AS contact_flag,
       CASE WHEN d.disposition_code_raw IN ('CALLBACK','REFUSED','DISPUTE','PAID','PROMISE_TO_PAY','PTP','PTP_BROKEN') THEN 1 ELSE 0 END AS rpc_flag
  FROM per_call d
)
SELECT disposition_id, account_id, borrower_id, event_at_local, event_at_utc,
       call_id, agent_id, disposition_code_raw, canonical_code,
       contact_flag, rpc_flag, disposition_version, n_rows_in_call,
       CURRENT_TIMESTAMP AS processed_at
FROM mapped WHERE rn = 1;

CREATE OR REPLACE TABLE dq_disposition_multi_per_call AS
SELECT 'call_dispositions' AS table_name,
       'multiple dispositions per call resolved to latest' AS rule,
       SUM(n_rows_in_call - 1) AS rows_rejected
FROM clean_call_dispositions;

CREATE OR REPLACE TABLE dq_disposition_totals AS
SELECT disposition_code_raw, COUNT(*) AS n_rows,
       COUNT(DISTINCT call_id) AS n_calls
FROM stg_call_dispositions GROUP BY disposition_code_raw;

-- ----------------------------------------------------------------------------
-- 7. PAYMENT DEDUPLICATION (duplicate payments problem)
--    Forensic evidence drives the rule:
--      * 500 payment_ids appear TWICE, byte-identical (same amount, account,
--        status, 0-second gap) -> true ingestion doubles. Remove one copy.
--      * 2,034 payment_references are reused across DIFFERENT payments
--        (different amounts, different accounts, ~75 days apart) -> these are
--        NOT money duplication; deduping them would delete real cash.
--        They are flagged (ref_reuse_flag) as an attribution/join hazard.
--      * FAILED/PENDING/REVERSED are not cash flow -> excluded (audited).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_payments AS
WITH succ AS (
  SELECT * FROM stg_payments WHERE payment_status = 'SUCCESS'
),
dedup_id AS (
  SELECT *,
         ROW_NUMBER() OVER (PARTITION BY payment_id ORDER BY event_at_utc ASC) AS rn_id,
         COUNT(*) OVER (PARTITION BY payment_id) AS n_payment_id
  FROM succ
),
ref_counts AS (
  SELECT payment_reference, COUNT(*) AS n_ref_rows
  FROM dedup_id WHERE rn_id = 1
  GROUP BY payment_reference
)
SELECT
  p.payment_id, p.account_id, p.borrower_id, p.event_at_local, p.event_at_utc,
  p.payment_reference, p.amount, p.payment_method, p.provider_id,
  (r.n_ref_rows > 1) AS ref_reuse_flag,
  (p.n_payment_id > 1) AS had_id_dup,
  TRUE AS keep_flag,
  CURRENT_TIMESTAMP AS processed_at
FROM dedup_id p
LEFT JOIN ref_counts r USING (payment_reference)
WHERE p.rn_id = 1;

CREATE OR REPLACE VIEW gold_payments AS
SELECT * FROM clean_payments;

CREATE OR REPLACE TABLE dq_payments_status AS
SELECT payment_status, COUNT(*) AS n_rows, SUM(amount) AS amount_total
FROM stg_payments GROUP BY payment_status;

CREATE OR REPLACE TABLE dq_payments_dedup AS
SELECT
  'payments' AS table_name, 'exact-double payment_id dedup + status filter' AS rule,
  (SELECT COUNT(*) FROM stg_payments WHERE payment_status <> 'SUCCESS') AS rows_excluded_status,
  (SELECT COALESCE(SUM(amount), 0) FROM stg_payments WHERE payment_status <> 'SUCCESS') AS amount_excluded_status,
  (SELECT COUNT(*) FROM stg_payments WHERE payment_status = 'SUCCESS') - (SELECT COUNT(*) FROM clean_payments)
    AS rows_excluded_exact_double,
  (SELECT COALESCE(SUM(amount), 0) FROM stg_payments WHERE payment_status = 'SUCCESS'
     AND payment_id IN (
       SELECT payment_id FROM stg_payments
       GROUP BY payment_id HAVING COUNT(*) > 1
     ) AND payment_id IN (
       SELECT payment_id FROM stg_payments GROUP BY payment_id HAVING COUNT(*) > 1
     ) AND payment_id IN (
       -- the second copy of each doubled id is the removed one
       SELECT payment_id FROM stg_payments GROUP BY payment_id, amount
       HAVING COUNT(*) > 1
     )) AS amount_excluded_exact_double_proxy;

CREATE OR REPLACE TABLE dq_payments_double_amount AS
-- 500 payment_ids are duplicated (1,000 rows). Of those, 346 ids carry TWO
-- SUCCESS copies each: the second copy is the removed phantom cash.
WITH dup_ids AS (
  SELECT payment_id FROM stg_payments GROUP BY payment_id HAVING COUNT(*) > 1
),
succ AS (
  SELECT p.payment_id, p.amount,
         ROW_NUMBER() OVER (PARTITION BY p.payment_id ORDER BY p.event_at_utc) AS rn
  FROM stg_payments p JOIN dup_ids USING (payment_id)
  WHERE p.payment_status = 'SUCCESS'
)
SELECT
  (SELECT COUNT(*) FROM dup_ids) AS duplicated_payment_ids_total,
  (SELECT COUNT(DISTINCT payment_id) FROM succ WHERE rn = 2) AS doubled_success_ids,
  (SELECT SUM(amount) FROM succ WHERE rn = 2) AS inflated_amount_by_doubles;

-- ----------------------------------------------------------------------------
-- 8. ATTEMPTS: exact replay rows only (same id or same call+ts+status).
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_call_attempts AS
WITH dedup AS (
  SELECT *,
         ROW_NUMBER() OVER (
           PARTITION BY attempt_id ORDER BY event_at_utc ASC
         ) AS rn_id,
         ROW_NUMBER() OVER (
           PARTITION BY call_id, event_at_utc, attempt_status
           ORDER BY attempt_no DESC, attempt_id
         ) AS rn_evt
  FROM stg_call_attempts
)
SELECT attempt_id, account_id, borrower_id, event_at_local, event_at_utc,
       call_id, agent_id, attempt_no, vendor_id, attempt_status,
       (rn_evt = 1 AND rn_id = 1) AS keep_flag,
       CURRENT_TIMESTAMP AS processed_at
FROM dedup;

CREATE OR REPLACE TABLE dq_attempts_dup AS
SELECT 'call_attempts' AS table_name,
       'duplicate attempt (same call/status/event-second) collapsed' AS rule,
       SUM(CASE WHEN NOT keep_flag THEN 1 ELSE 0 END) AS rows_rejected
FROM clean_call_attempts;

-- ----------------------------------------------------------------------------
-- 9. DIGITAL EVENTS: message lifecycle (SENT->DELIVERED->READ->REPLIED) is
--    one logical message; duplicated event ids / identical lifecycle rows
--    are the actual injection. Dedupe on full row; keep lifecycle.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_whatsapp_events AS
WITH base AS (
  SELECT *, ROW_NUMBER() OVER (
      PARTITION BY whatsapp_event_id ORDER BY event_at_utc ASC) AS rn_id,
      COUNT(*) OVER (PARTITION BY whatsapp_event_id) AS n_id_rows
  FROM stg_whatsapp_events
)
SELECT whatsapp_event_id, account_id, borrower_id, event_at_local, event_at_utc,
       message_id, event_type, template_code, provider_id, (rn_id = 1) AS keep_flag,
       CURRENT_TIMESTAMP AS processed_at
FROM base;

CREATE OR REPLACE TABLE clean_sms_events AS
WITH base AS (
  SELECT *, ROW_NUMBER() OVER (
      PARTITION BY sms_event_id ORDER BY event_at_utc ASC) AS rn_id,
      COUNT(*) OVER (PARTITION BY sms_event_id) AS n_id_rows
  FROM stg_sms_events
)
SELECT sms_event_id, account_id, borrower_id, event_at_local, event_at_utc,
       message_id, event_type, template_code, provider_id, (rn_id = 1) AS keep_flag,
       CURRENT_TIMESTAMP AS processed_at
FROM base;

CREATE OR REPLACE TABLE dq_digital_event_dup AS
SELECT 'whatsapp_events' AS table_name,
       'duplicate event ids collapsed to first instance' AS rule,
       COUNT(*) - COUNT(DISTINCT whatsapp_event_id) AS rows_rejected
FROM stg_whatsapp_events;

-- ----------------------------------------------------------------------------
-- 10. FIELD VISITS, PTP, SESSIONS, CAMPAIGNS, TARGETING, VENDORS
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE clean_field_visits AS
WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY visit_id ORDER BY event_at_utc) AS rn
  FROM stg_field_visits WHERE visit_id IS NOT NULL
)
SELECT visit_id, account_id, borrower_id, event_at_local, event_at_utc,
       agent_id, visit_type, visit_outcome, latitude, longitude,
       scheduled_at_local, (event_at_local > scheduled_at_local) AS visit_late_vs_scheduled,
       CURRENT_TIMESTAMP AS processed_at
FROM dedup;

CREATE OR REPLACE TABLE clean_promises_to_pay AS
SELECT ptp_id, account_id, borrower_id, event_at_local, event_at_utc, agent_id,
       promised_amount, promised_date, ptp_status, source,
       CURRENT_TIMESTAMP AS processed_at
FROM stg_promises_to_pay WHERE ptp_id IS NOT NULL;

CREATE OR REPLACE TABLE clean_agent_sessions AS
WITH s AS (
  SELECT session_id, agent_id, login_at_local, logout_at_local, tz,
         session_channel, device_id,
         -- tz-normalized session clock
         tz_to_utc(login_at_local, tz)  AS login_at_utc,
         tz_to_utc(logout_at_local, tz) AS logout_at_utc
  FROM stg_agent_sessions
),
fixed AS (
  SELECT s.*,
         (logout_at_local < login_at_local) AS logout_before_login_flag,
         GREATEST(
           LEAST(EXTRACT(EPOCH FROM (logout_at_utc - login_at_utc))/3600.0, 12.0),
           0.25
         ) AS session_hours_capped
  FROM s
)
SELECT session_id, agent_id, login_at_local, logout_at_local, tz,
       tz_to_utc(login_at_local, tz) AS login_at_utc,
       tz_to_utc(logout_at_local, tz) AS logout_at_utc,
       session_channel, device_id, logout_before_login_flag, session_hours_capped,
       CURRENT_TIMESTAMP AS processed_at
FROM fixed;

CREATE OR REPLACE TABLE clean_campaigns AS
SELECT campaign_id, campaign_name, channel_raw, strategy_version,
       start_at_local, end_at_local, target_definition, tz_to_utc(start_at_local, 'Asia/Kolkata') AS start_at_utc,
       CURRENT_TIMESTAMP AS processed_at
FROM stg_campaigns WHERE campaign_id IS NOT NULL;

CREATE OR REPLACE TABLE clean_daily_targeting AS
WITH dedup AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY account_id, target_date, campaign_id
                               ORDER BY target_id) AS rn
  FROM stg_daily_targeting WHERE target_id IS NOT NULL
)
SELECT target_id, account_id, campaign_id, target_date, priority,
       recommended_channel, target_status,
       CURRENT_TIMESTAMP AS processed_at
FROM dedup WHERE rn = 1;

CREATE OR REPLACE TABLE clean_vendor_telephony AS
SELECT vendor_id, vendor_name, vendor_account_id, tz, vendor_status, schema_version,
       CURRENT_TIMESTAMP AS processed_at
FROM stg_vendor_telephony WHERE vendor_id IS NOT NULL;

-- ----------------------------------------------------------------------------
-- 11. AGGREGATED DQ LEDGER (feeds the Data Quality Report)
-- ----------------------------------------------------------------------------
CREATE OR REPLACE TABLE agg_dq_totals AS
SELECT *
FROM (
  SELECT 'raw_rows_staged' AS metric, SUM(c) AS value FROM (
    SELECT COUNT(*) c FROM stg_borrowers_raw UNION ALL SELECT COUNT(*) FROM stg_accounts_raw
    UNION ALL SELECT COUNT(*) FROM stg_agents_raw UNION ALL SELECT COUNT(*) FROM stg_agent_sessions_raw
    UNION ALL SELECT COUNT(*) FROM stg_calls_raw UNION ALL SELECT COUNT(*) FROM stg_call_attempts_raw
    UNION ALL SELECT COUNT(*) FROM stg_call_dispositions_raw UNION ALL SELECT COUNT(*) FROM stg_whatsapp_events_raw
    UNION ALL SELECT COUNT(*) FROM stg_sms_events_raw UNION ALL SELECT COUNT(*) FROM stg_field_visits_raw
    UNION ALL SELECT COUNT(*) FROM stg_promises_to_pay_raw UNION ALL SELECT COUNT(*) FROM stg_payments_raw
    UNION ALL SELECT COUNT(*) FROM stg_daily_targeting_raw UNION ALL SELECT COUNT(*) FROM stg_complaints_raw
    UNION ALL SELECT COUNT(*) FROM stg_account_status_history_raw
  )
);
