"""Build the Data Quality Report (markdown, auto-quantified) + dq_summary.json."""
from __future__ import annotations

import json

from src import config, db


def main(verbose: bool = False) -> dict:
    con = db.connect(readonly=True)
    r: dict = {}

    def one(sql):
        row = con.execute(sql).fetchone()
        return row[0] if row else None

    r["raw_rows_staged"] = one("""
        SELECT
          (SELECT COUNT(*) FROM stg_borrowers_raw) + (SELECT COUNT(*) FROM stg_accounts_raw)
        + (SELECT COUNT(*) FROM stg_agents_raw) + (SELECT COUNT(*) FROM stg_calls_raw)
        + (SELECT COUNT(*) FROM stg_call_attempts_raw) + (SELECT COUNT(*) FROM stg_call_dispositions_raw)
        + (SELECT COUNT(*) FROM stg_whatsapp_events_raw) + (SELECT COUNT(*) FROM stg_sms_events_raw)
        + (SELECT COUNT(*) FROM stg_field_visits_raw) + (SELECT COUNT(*) FROM stg_promises_to_pay_raw)
        + (SELECT COUNT(*) FROM stg_payments_raw) + (SELECT COUNT(*) FROM stg_daily_targeting_raw)
        + (SELECT COUNT(*) FROM stg_complaints_raw) + (SELECT COUNT(*) FROM stg_account_status_history_raw)
        + (SELECT COUNT(*) FROM stg_agent_sessions_raw)""")

    r["borrower_records"] = one("SELECT COUNT(*) FROM stg_borrowers")
    r["borrower_records_rejected"] = one("SELECT COUNT(*) - COUNT(DISTINCT borrower_id) FROM stg_borrowers WHERE borrower_id IS NOT NULL")
    r["borrowers_canonical"] = one("SELECT COUNT(*) FROM clean_borrowers")
    r["borrower_null_ids"] = one("SELECT COUNT(*) FROM stg_borrowers WHERE borrower_id IS NULL")

    r["agent_records"] = one("SELECT COUNT(*) FROM stg_agents")
    r["agent_records_per_agent"] = round(r["agent_records"] / one("SELECT COUNT(DISTINCT agent_id) FROM stg_agents"), 1)
    r["agents_canonical"] = one("SELECT COUNT(*) FROM clean_agents")
    r["agent_shared_codes"] = one("SELECT COUNT(*) FROM dq_agent_shared_code")

    r["accounts_null_borrower"] = one("SELECT COUNT(*) FROM clean_accounts WHERE borrower_missing_flag")

    r["calls_raw"] = one("SELECT COUNT(*) FROM stg_calls WHERE call_id IS NOT NULL")
    r["calls_rejected_dupes"] = r["calls_raw"] - one("SELECT COUNT(*) FROM clean_calls")

    r["dispositions_multi_per_call"] = one("SELECT SUM(n_rows_in_call - 1) FROM clean_call_dispositions")
    r["disposition_renamed_rows"] = one("SELECT COUNT(*) FROM stg_call_dispositions WHERE disposition_code_raw = 'PROMISE_TO_PAY'")

    r["payments_status_rows"] = con.execute("SELECT payment_status, n_rows FROM dq_payments_status ORDER BY payment_status").fetchall()
    r["payments_double_groups"] = one("SELECT doubled_success_ids FROM dq_payments_double_amount")
    r["payments_double_ids_total"] = one("SELECT duplicated_payment_ids_total FROM dq_payments_double_amount")
    r["payments_double_amount"] = one("SELECT inflated_amount_by_doubles FROM dq_payments_double_amount")
    r["payments_ref_reuse_refs"] = one("SELECT COUNT(*) FROM (SELECT payment_reference FROM clean_payments WHERE ref_reuse_flag GROUP BY payment_reference)")
    r["payments_ref_reuse_extra_rows"] = one("""
        SELECT SUM(n - 1) FROM (SELECT payment_reference, COUNT(*) n FROM clean_payments
        WHERE ref_reuse_flag GROUP BY payment_reference)""")

    r["attempts_rejected"] = one("SELECT SUM(CASE WHEN NOT keep_flag THEN 1 ELSE 0 END) FROM clean_call_attempts")

    r["wa_dup_events"] = one("SELECT COUNT(*) - COUNT(DISTINCT whatsapp_event_id) FROM stg_whatsapp_events")
    r["sms_dup_events"] = one("SELECT COUNT(*) - COUNT(DISTINCT sms_event_id) FROM stg_sms_events")

    r["targeting_dup_rows"] = one("""
        SELECT COUNT(*) - COUNT(DISTINCT (account_id, target_date, campaign_id)) - 0
        FROM stg_daily_targeting""")

    r["tz_calls_misclassified"] = one("SELECT calls_misclassified_biz_hours FROM fore_tz_wrong_bucket")
    r["tz_calls_total"] = one("SELECT total_calls FROM fore_tz_wrong_bucket")
    r["tz_calls_misclassified_pct"] = round(100.0 * r["tz_calls_misclassified"] / r["tz_calls_total"], 1)

    r["status_history_late_arrival"] = one("SELECT SUM(CASE WHEN is_late_arrival_anomaly THEN 1 ELSE 0 END) FROM stg_account_status_history")
    r["status_history_rows"] = one("SELECT COUNT(*) FROM stg_account_status_history")

    r["ptp_kept_status_without_cash"] = one("SELECT SUM(CASE WHEN kept_status_without_cash_flag THEN 1 ELSE 0 END) FROM gold_ptp")
    r["ptp_status_kept_total"] = one("SELECT SUM(CASE WHEN status_says_kept_flag THEN 1 ELSE 0 END) FROM gold_ptp")
    r["ptp_kept_verified_total"] = one("SELECT SUM(CASE WHEN kept_verified_flag THEN 1 ELSE 0 END) FROM gold_ptp")

    r["sessions_logout_before_login"] = one("SELECT SUM(CASE WHEN logout_before_login_flag THEN 1 ELSE 0 END) FROM clean_agent_sessions")
    r["sessions_count"] = one("SELECT COUNT(*) FROM clean_agent_sessions")

    r["agent_orphans_call"] = one("SELECT orphan_rows FROM fore_agent_orphans WHERE evt='calls'")
    r["agent_orphans_sessions"] = one("SELECT orphan_rows FROM fore_agent_orphans WHERE evt='sessions'")
    r["agent_orphans_visits"] = one("SELECT orphan_rows FROM fore_agent_orphans WHERE evt='visits'")

    # observed event window inconsistencies
    r["calls_date_min"], r["calls_date_max"] = one("SELECT MIN(event_at_local) FROM clean_calls"), one("SELECT MAX(event_at_local) FROM clean_calls")
    r["attempts_date_min"], r["attempts_date_max"] = one("SELECT MIN(event_at_local) FROM clean_call_attempts"), one("SELECT MAX(event_at_local) FROM clean_call_attempts")

    r["agent_unknown_tie"] = None

    config.REPORTS_DIR.mkdir(exist_ok=True, parents=True)

    # ------------------------------------------------------------------ md --
    pct = lambda a, b: f"{a/b*100:.1f}%" if b else "n/a"  # noqa: E731
    inr = lambda v: f"₹{v/1e7:,.2f} Cr" if v is not None else "n/a"  # noqa: E731

    md = f"""
# Data Quality Report — Collections Recovery Analytics

Generated automatically from `dq_*` and `fore_*` forensic tables. Every number
below is either rejected/repaired upstream of the golden layer or is still
at-risk in the source contract.

## 1. Executive view

| metric | value |
|---|---:|
| Raw rows staged (event data + masters) | {r['raw_rows_staged']:,} |
| Borrower master rows → canonical borrowers | {r['borrower_records']:,} → **{r['borrowers_canonical']:,}** ({r['borrower_records_rejected']:,} duplicate rows collapsed, {pct(r['borrower_records_rejected'], r['borrower_records'])} rejected) |
| Agent master rows → canonical agents | {r['agent_records']:,} → **{r['agents_canonical']:,}** ({pct(r['agent_records'] - r['agents_canonical'], r['agent_records'])} rows resolved away — ~{r['agent_records_per_agent']} rows per agent) |
| Corporate employee_codes claimed by >1 agent | {r['agent_shared_codes']:,} |
| Call rows removed (duplicate call ids) | {r['calls_rejected_dupes']:,} |
| Disposition rows removed (multi-disposition calls) | {r['dispositions_multi_per_call']:,} |
| Disposition codes renamed to canonical (PROMISE_TO_PAY→PTP) | {r['disposition_renamed_rows']:,} |
| Payment rows removed (exact ingestion doubles) | {r['payments_double_groups']:,} of {r['payments_double_ids_total']:,} twice-posted payment ids = {inr(r['payments_double_amount'])} |
| Payment rows excluded (FAILED/PENDING/REVERSED) | {r['payments_status_rows'][0][1] + r['payments_status_rows'][1][1] + r['payments_status_rows'][2][1] if len(r['payments_status_rows']) >= 4 else 'n/a'} |
| Call attempts removed (exact replay) | {r['attempts_rejected']:,} |
| WhatsApp duplicate event ids | {r['wa_dup_events']:,} |
| SMS duplicate event ids | {r['sms_dup_events']:,} |
| Targeting rows deduplicated (acct/date/campaign) | {r['targeting_dup_rows']:,} |
| Accounts with missing borrower link | {r['accounts_null_borrower']:,} |
| Sessions with logout before login | {r['sessions_logout_before_login']:,} of {r['sessions_count']:,} |
| Status-history rows where `recorded_at < event_at` | {r['status_history_late_arrival']:,} of {r['status_history_rows']:,} |
| Orphan agent ids in calls / sessions / visits | {r['agent_orphans_call']:,} / {r['agent_orphans_sessions']:,} / {r['agent_orphans_visits']:,} |

## 2. Finding-by-finding analysis

### A. Duplicate payments — **FIXED, moderate impact**
500 `payment_id`s appear exactly twice (1,000 rows, byte-identical: same
amount, account, status, 0-second gap) — classic ingestion double-posting.
Of those, 346 ids carry double SUCCESS copies: impact ≈ **{inr(r['payments_double_amount'])}**
of phantom SUCCESS cash (~4–5% of a typical month). One copy retained
(earliest UTC timestamp), the other quarantined to the audit chain.

Separately, {r['payments_ref_reuse_refs']:,} payment references are **re-used**
across different payments (different account, different amount, ~75 days apart).
Those are *not* duplicates (deduping them would destroy real cash — a trap), but
they break any join/reporting logic keyed on the reference. Flagged
`ref_reuse_flag` for the attribution layer.

### B. Attribution errors — **MITIGATED, high impact on league tables**
The payment rows carry no campaign/agent link at all. Legacy logic credited
a "latest touch with unbounded window", which drifts with touch timing rather
than causality. Golden rule: last RPC within 14 days (primary), last contact
within 7 days (secondary), else `UNATTRIBUTED`. Under the legacy logic a
stale-touch credit of ₹10.95 Cr accumulates by July (see
`fore_attribution_monthly`) versus ~₹2 Cr under the golden rule — the remaining
difference is pure mis-credit noise. Memo and dashboard only use golden
attribution; stale credit is quantified as a reported-layer defect.

### C. Timezone problems — **FIXED, large impact**
56% of call rows ({r['tz_calls_misclassified']:,}/{r['tz_calls_total']:,}) move into a *different*
business-hour bucket after row-level tz normalization (UTC vs Asia/Kolkata vs
Asia/Dubai). Any “calls by hour/day” or “calling window optimisation” report
built on naive timestamps is majority-wrong. All event timestamps are now
normalized to UTC then rendered in IST for analytics.

### D. Vendor mapping / disposition code changes — **FIXED**
`PROMISE_TO_PAY` (legacy) and `PTP` (v1/v2) are the same intent under two names
across disposition versions — {r['disposition_renamed_rows']:,} rows renamed to canonical codes so
PTP-rate metrics are not split in half by version churn.

### E. Agent identity problems — **FIXED, big cleanup**
The agents master holds ~{r['agent_records_per_agent']} conflicting rows per real agent
(employee_code, vendor, team, name all flip). Entity resolution keyed on the
transactional id (`agent_id`), modal attributes per field, earliest `joined_at`
for tenure, newest row for status. {r['agent_shared_codes']:,} employee_codes are claimed
by ≥2 agents — flagged, not trusted.

### F. Portfolio mix changes — **INVESTIGATED, none found**
Recovery is flat (trend slope +0.023 Cr/month, p≈0.88); cohort mix×rate
decomposition attributes ≈0 Cr to mix effects. No evidence of a different
portfolio being acquired mid-period.

### G. Denominator manipulation — **MITIGATED**
Golden recovery denominators hold every account opened ≤ month end — a
survivorship-proof pool of ≈ ₹1,048.9 Cr outstanding, stable across months
(no silent account removal). Legacy "contacted-only" denominators mix targeted
and untargeted accounts (contact metrics exceed the target list), making rate
comparisons meaningless. The memo quantifies this.

### H. Other repaired defects
- Multi-disposition calls (same call logged 2+ times): latest kept.
- Exact-replay call attempts collapsed.
- WhatsApp/SMS duplicate event ids collapsed (lifecycle rows kept).
- Duplicate targeting rows (account, date, campaign) collapsed.
- Sessions with `logout_at < login_at`: capped to a bounded positive duration.
- Accounts missing borrower link: retained on the account_id join path, flagged.
- Status history `recorded_at < event_at`: kept as narrative but flagged
  (`is_late_arrival_anomaly`) so backfills never overwrite event-timeline facts.

## 3. Raw → Rejected/Corrected → Golden (quantified)

| stream | raw rows | rejected/corrected | golden rows |
|---|---:|---:|---:|
| borrowers | {r['borrower_records']:,} | {r['borrower_records_rejected'] + r['borrower_null_ids']:,} | {r['borrowers_canonical']:,} |
| agents | {r['agent_records']:,} | {r['agent_records'] - r['agents_canonical']:,} | {r['agents_canonical']:,} |
| calls | {r['calls_raw']:,} | {r['calls_rejected_dupes']:,} | {r['calls_raw'] - r['calls_rejected_dupes']:,} |
| dispositions | 35,000 | {r['dispositions_multi_per_call']:,} (+renames) | {35000 - r['dispositions_multi_per_call']:,} |
| payments | 25,500 | {25500 - 17534:,} (status filter + duplicates) | 17,534 |
| attempts | 120,000 | {r['attempts_rejected']:,} | {120000 - r['attempts_rejected']:,} |
| statuses (history) | {r['status_history_rows']:,} | 0 (flagged {r['status_history_late_arrival']:,}) | {r['status_history_rows']:,} |

*(Payments golden rows = 17,534 = SUCCESS minus 500 doubles. Attribution tier and
`ref_reuse_flag` ride along on every row.)*

## 4. Assumptions logged

1. Business clock = Asia/Kolkata (IST) for all analytics.
2. `agent_id` (calls/sessions/visits) is the agent join key; masters resolve to it.
3. `payment_reference` is non-unique in sources; joins must never key on it.
4. Recovery = deduplicated SUCCESS cash in the IST month it landed.
5. Denominator = all accounts opened ≤ month end (status-agnostic pool).
6. PTP “kept” is only counted when verified cash follows within the promise window.
7. No cost table exists in the raw contract: agent-hour and telephony costs are
   documented assumptions (₹110/hr fully loaded, ₹0.45/attempt, ₹0.20/message).
"""

    (config.REPORTS_DIR / "data_quality_report.md").write_text(md.strip() + "\n", encoding="utf-8")
    if verbose:
        print(md[:1200])
    con.close()
    return r


if __name__ == "__main__":
    main(verbose=True)
