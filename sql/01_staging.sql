-- ============================================================================
-- 01_staging.sql  |  RAW -> STAGING
-- ----------------------------------------------------------------------------
-- Read every raw CSV as VARCHAR FIRST (no implicit casts). We do not trust the
-- ingestion layer: mixed types, dirty identifiers and NaNs are common.
-- All business timezone = Asia/Kolkata (UTC+05:30). Dubai offset = +04:00.
-- Every staged view exposes: *_raw (string), and a normalized UTC timestamp
-- derived from the ROW-LEVEL timezone column. Naive local times + a tz column
-- are the raw contract; we never assume the system clock timezone.
-- ============================================================================

CREATE OR REPLACE TABLE stg_load_meta AS
  SELECT '{run_id}' AS run_id,
         CURRENT_TIMESTAMP AS loaded_at;

-- ---------------------------------------------------------------- borrowers --
CREATE OR REPLACE VIEW stg_borrowers_raw AS
SELECT *
FROM read_csv('{raw_dir}/borrowers.csv', header=true, all_varchar=true);

-- normalizer macro for phone strings (digits only)
CREATE OR REPLACE MACRO reg_replace_digits(s) AS
  regexp_replace(COALESCE(s, ''), '[^0-9]', '', 'g');

-- ---------------------------------------------------------------- accounts ---
CREATE OR REPLACE VIEW stg_accounts_raw AS
SELECT *
FROM read_csv('{raw_dir}/accounts.csv', header=true, all_varchar=true);

-- ------------------------------------------------------------------ agents ---
CREATE OR REPLACE VIEW stg_agents_raw AS
SELECT *
FROM read_csv('{raw_dir}/agents.csv', header=true, all_varchar=true);

-- -------------------------------------------------------- agent_sessions -----
CREATE OR REPLACE VIEW stg_agent_sessions_raw AS
SELECT *
FROM read_csv('{raw_dir}/agent_sessions.csv', header=true, all_varchar=true);

-- --------------------------------------------------------------- campaigns ---
CREATE OR REPLACE VIEW stg_campaigns_raw AS
SELECT *
FROM read_csv('{raw_dir}/campaigns.csv', header=true, all_varchar=true);

-- --------------------------------------------------------- daily_targeting ---
CREATE OR REPLACE VIEW stg_daily_targeting_raw AS
SELECT *
FROM read_csv('{raw_dir}/daily_targeting.csv', header=true, all_varchar=true);

-- ------------------------------------------------------------------- calls ---
CREATE OR REPLACE VIEW stg_calls_raw AS
SELECT *
FROM read_csv('{raw_dir}/calls.csv', header=true, all_varchar=true);

-- ------------------------------------------------------------ call_attempts --
CREATE OR REPLACE VIEW stg_call_attempts_raw AS
SELECT *
FROM read_csv('{raw_dir}/call_attempts.csv', header=true, all_varchar=true);

-- ------------------------------------------------------- call_dispositions ---
CREATE OR REPLACE VIEW stg_call_dispositions_raw AS
SELECT *
FROM read_csv('{raw_dir}/call_dispositions.csv', header=true, all_varchar=true);

-- ----------------------------------------------------------- whatsapp_events -
CREATE OR REPLACE VIEW stg_whatsapp_events_raw AS
SELECT *
FROM read_csv('{raw_dir}/whatsapp_events.csv', header=true, all_varchar=true);

-- ---------------------------------------------------------------- sms_events -
CREATE OR REPLACE VIEW stg_sms_events_raw AS
SELECT *
FROM read_csv('{raw_dir}/sms_events.csv', header=true, all_varchar=true);

-- ------------------------------------------------------------- field_visits --
CREATE OR REPLACE VIEW stg_field_visits_raw AS
SELECT *
FROM read_csv('{raw_dir}/field_visits.csv', header=true, all_varchar=true);

-- ---------------------------------------------------------- promises_to_pay --
CREATE OR REPLACE VIEW stg_promises_to_pay_raw AS
SELECT *
FROM read_csv('{raw_dir}/promises_to_pay.csv', header=true, all_varchar=true);

-- ---------------------------------------------------------------- payments ---
CREATE OR REPLACE VIEW stg_payments_raw AS
SELECT *
FROM read_csv('{raw_dir}/payments.csv', header=true, all_varchar=true);

-- -------------------------------------------------------- vendor_telephony ---
CREATE OR REPLACE VIEW stg_vendor_telephony_raw AS
SELECT *
FROM read_csv('{raw_dir}/vendor_telephony.csv', header=true, all_varchar=true);

-- -------------------------------------------------------- account_status_hist -
CREATE OR REPLACE VIEW stg_account_status_history_raw AS
SELECT *
FROM read_csv('{raw_dir}/account_status_history.csv', header=true, all_varchar=true);

-- --------------------------------------------------------------- complaints --
CREATE OR REPLACE VIEW stg_complaints_raw AS
SELECT *
FROM read_csv('{raw_dir}/complaints.csv', header=true, all_varchar=true);

-- ============================================================================
-- TYPING LAYER: one canonical typed model per raw table.
-- naive event_at + a row-level timezone column -> UTC naive timestamp.
-- ============================================================================
CREATE OR REPLACE MACRO tz_to_utc(naive_ts, tz) AS
  CASE
    WHEN tz = 'Asia/Kolkata' THEN naive_ts - INTERVAL 5 HOUR - INTERVAL 30 MINUTE
    WHEN tz = 'Asia/Dubai'   THEN naive_ts - INTERVAL 4 HOUR
    WHEN tz = 'UTC'          THEN naive_ts
    ELSE naive_ts  -- unknown tz -> passthrough (flagged downstream for audit)
  END;

CREATE OR REPLACE MACRO utc_to_ist(ts_utc) AS
  ts_utc + INTERVAL 5 HOUR + INTERVAL 30 MINUTE;

CREATE OR REPLACE VIEW stg_borrowers AS
SELECT borrower_id_raw  AS borrower_id,
       NULLIF(TRIM(name_raw), '') AS name_clean,
       phone_raw AS phone_raw,
       CASE WHEN length(reg_replace_digits(phone_raw)) BETWEEN 10 AND 14
                 THEN reg_replace_digits(phone_raw)
            ELSE NULL END AS phone_clean,
       email_raw AS email,
       city_raw AS city, state_raw AS state,
       TRY_CAST(created_at_raw AS TIMESTAMP) AS created_at,
       TRY_CAST(updated_at_raw AS TIMESTAMP) AS updated_at
FROM (
  SELECT "borrower_id" AS borrower_id_raw, "name" AS name_raw, "phone" AS phone_raw,
         "email" AS email_raw, "city" AS city_raw, "state" AS state_raw,
         "created_at" AS created_at_raw, "updated_at" AS updated_at_raw
  FROM stg_borrowers_raw
);

CREATE OR REPLACE MACRO reg_replace_digits(s) AS regexp_replace(s, '[^0-9]', '', 'g');

CREATE OR REPLACE VIEW stg_accounts AS
SELECT account_id AS account_id,
       borrower_id AS borrower_id,
       NULLIF(TRIM(loan_type), '') AS loan_type,
       TRY_CAST(principal_amount AS DOUBLE) AS principal_amount,
       TRY_CAST(outstanding_amount AS DOUBLE) AS outstanding_amount,
       TRY_CAST(dpd AS INTEGER) AS dpd,
       risk_segment AS risk_segment,
       UPPER(status) AS status,
       TRY_CAST(opened_at AS TIMESTAMP) AS opened_at,
       timezone AS tz,
       schema_version
FROM stg_accounts_raw;

CREATE OR REPLACE VIEW stg_agents AS
SELECT agent_id AS agent_id,
       employee_code AS employee_code,
       agent_name AS agent_name,
       vendor_id AS vendor_id,
       team AS team,
       UPPER(status) AS status,
       TRY_CAST(joined_at AS TIMESTAMP) AS joined_at,
       TRY_CAST(updated_at AS TIMESTAMP) AS updated_at
FROM stg_agents_raw;

CREATE OR REPLACE VIEW stg_agent_sessions AS
SELECT session_id AS session_id,
       agent_id AS agent_id,
       TRY_CAST(login_at AS TIMESTAMP) AS login_at_local,
       TRY_CAST(logout_at AS TIMESTAMP) AS logout_at_local,
       timezone AS tz,
       channel AS session_channel,
       device_id
FROM stg_agent_sessions_raw;

CREATE OR REPLACE VIEW stg_campaigns AS
SELECT campaign_id AS campaign_id,
       UPPER(TRIM(campaign_name)) AS campaign_name,
       UPPER(channel) AS channel_raw,
       strategy_version,
       TRY_CAST(start_at AS TIMESTAMP) AS start_at_local,
       TRY_CAST(end_at AS TIMESTAMP) AS end_at_local,
       UPPER(TRIM(target_definition)) AS target_definition
FROM stg_campaigns_raw;

CREATE OR REPLACE VIEW stg_daily_targeting AS
SELECT target_id AS target_id,
       account_id AS account_id,
       campaign_id AS campaign_id,
       CAST(target_date AS DATE) AS target_date,
       TRY_CAST(priority AS INTEGER) AS priority,
       UPPER(recommended_channel) AS recommended_channel,
       UPPER(status) AS target_status
FROM stg_daily_targeting_raw;

CREATE OR REPLACE VIEW stg_calls AS
SELECT call_id AS call_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), timezone) AS event_at_utc,
       agent_id AS agent_id,
       campaign_id AS campaign_id,
       UPPER(direction) AS direction,
       vendor_id AS vendor_id,
       UPPER(call_status) AS call_status,
       TRY_CAST(duration_sec AS INTEGER) AS duration_sec,
       timezone AS tz
FROM stg_calls_raw;

CREATE OR REPLACE VIEW stg_call_attempts AS
SELECT attempt_id AS attempt_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       call_id AS call_id,
       agent_id AS agent_id,
       TRY_CAST(attempt_no AS INTEGER) AS attempt_no,
       vendor_id AS vendor_id,
       UPPER(attempt_status) AS attempt_status
FROM stg_call_attempts_raw;

CREATE OR REPLACE VIEW stg_call_dispositions AS
SELECT disposition_id AS disposition_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       call_id AS call_id,
       agent_id AS agent_id,
       UPPER(disposition_code) AS disposition_code_raw,
       disposition_version
FROM stg_call_dispositions_raw;

CREATE OR REPLACE VIEW stg_whatsapp_events AS
SELECT whatsapp_event_id AS whatsapp_event_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       message_id AS message_id,
       UPPER(event_type) AS event_type,
       UPPER(template_code) AS template_code,
       provider_id AS provider_id
FROM stg_whatsapp_events_raw;

CREATE OR REPLACE VIEW stg_sms_events AS
SELECT sms_event_id AS sms_event_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       message_id AS message_id,
       UPPER(event_type) AS event_type,
       UPPER(template_code) AS template_code,
       provider_id AS provider_id
FROM stg_sms_events_raw;

CREATE OR REPLACE VIEW stg_field_visits AS
SELECT visit_id AS visit_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       agent_id AS agent_id,
       UPPER(visit_type) AS visit_type,
       UPPER(outcome) AS visit_outcome,
       TRY_CAST(latitude AS DOUBLE) AS latitude,
       TRY_CAST(longitude AS DOUBLE) AS longitude,
       TRY_CAST(scheduled_at AS TIMESTAMP) AS scheduled_at_local
FROM stg_field_visits_raw;

CREATE OR REPLACE VIEW stg_promises_to_pay AS
SELECT ptp_id AS ptp_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       agent_id AS agent_id,
       TRY_CAST(promised_amount AS DOUBLE) AS promised_amount,
       CAST(promised_date AS DATE) AS promised_date,
       UPPER(status) AS ptp_status,
       UPPER(source) AS source
FROM stg_promises_to_pay_raw;

CREATE OR REPLACE VIEW stg_payments AS
SELECT payment_id AS payment_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       payment_reference AS payment_reference,
       TRY_CAST(amount AS DOUBLE) AS amount,
       UPPER(payment_status) AS payment_status,
       UPPER(payment_method) AS payment_method,
       provider_id AS provider_id
FROM stg_payments_raw;

CREATE OR REPLACE VIEW stg_vendor_telephony AS
SELECT vendor_id AS vendor_id,
       vendor_name AS vendor_name,
       vendor_account_id AS vendor_account_id,
       timezone AS tz,
       UPPER(status) AS vendor_status,
       schema_version
FROM stg_vendor_telephony_raw;

CREATE OR REPLACE VIEW stg_account_status_history AS
SELECT history_id AS history_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       UPPER(status) AS status,
       changed_by AS changed_by,
       UPPER(source) AS source,
       TRY_CAST(recorded_at AS TIMESTAMP) AS recorded_at,
       (TRY_CAST(recorded_at AS TIMESTAMP) < TRY_CAST(event_at AS TIMESTAMP)) AS is_late_arrival_anomaly
FROM stg_account_status_history_raw;

CREATE OR REPLACE VIEW stg_complaints AS
SELECT complaint_id AS complaint_id,
       account_id AS account_id,
       borrower_id AS borrower_id,
       TRY_CAST(event_at AS TIMESTAMP) AS event_at_local,
       tz_to_utc(TRY_CAST(event_at AS TIMESTAMP), 'Asia/Kolkata') AS event_at_utc,
       UPPER(complaint_type) AS complaint_type,
       UPPER(severity) AS severity,
       UPPER(status) AS complaint_status,
       UPPER(source) AS source,
       TRY_CAST(resolution_at AS TIMESTAMP) AS resolution_at
FROM stg_complaints_raw;
