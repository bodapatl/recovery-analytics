# Data Quality Report — Collections Recovery Analytics

Generated automatically from `dq_*` and `fore_*` forensic tables. Every number
below is either rejected/repaired upstream of the golden layer or is still
at-risk in the source contract.

## 1. Executive view

| metric | value |
|---|---:|
| Raw rows staged (event data + masters) | 639,050 |
| Borrower master rows → canonical borrowers | 30,600 → **11,015** (19,585 duplicate rows collapsed, 64.0% rejected) |
| Agent master rows → canonical agents | 30,000 → **1,000** (96.7% rows resolved away — ~30.0 rows per agent) |
| Corporate employee_codes claimed by >1 agent | 255 |
| Call rows removed (duplicate call ids) | 1,350 |
| Disposition rows removed (multi-disposition calls) | 6,029 |
| Disposition codes renamed to canonical (PROMISE_TO_PAY→PTP) | 3,926 |
| Payment rows removed (exact ingestion doubles) | 346 of 500 twice-posted payment ids = ₹2.59 Cr |
| Payment rows excluded (FAILED/PENDING/REVERSED) | 7620 |
| Call attempts removed (exact replay) | 0 |
| WhatsApp duplicate event ids | 600 |
| SMS duplicate event ids | 0 |
| Targeting rows deduplicated (acct/date/campaign) | 4 |
| Accounts with missing borrower link | 455 |
| Sessions with logout before login | 0 of 15,000 |
| Status-history rows where `recorded_at < event_at` | 30,191 of 60,000 |
| Orphan agent ids in calls / sessions / visits | 0 / 0 / 0 |

## 2. Finding-by-finding analysis

### A. Duplicate payments — **FIXED, moderate impact**
500 `payment_id`s appear exactly twice (1,000 rows, byte-identical: same
amount, account, status, 0-second gap) — classic ingestion double-posting.
Of those, 346 ids carry double SUCCESS copies: impact ≈ **₹2.59 Cr**
of phantom SUCCESS cash (~4–5% of a typical month). One copy retained
(earliest UTC timestamp), the other quarantined to the audit chain.

Separately, 1,782 payment references are **re-used**
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
56% of call rows (50,119/90,000) move into a *different*
business-hour bucket after row-level tz normalization (UTC vs Asia/Kolkata vs
Asia/Dubai). Any “calls by hour/day” or “calling window optimisation” report
built on naive timestamps is majority-wrong. All event timestamps are now
normalized to UTC then rendered in IST for analytics.

### D. Vendor mapping / disposition code changes — **FIXED**
`PROMISE_TO_PAY` (legacy) and `PTP` (v1/v2) are the same intent under two names
across disposition versions — 3,926 rows renamed to canonical codes so
PTP-rate metrics are not split in half by version churn.

### E. Agent identity problems — **FIXED, big cleanup**
The agents master holds ~30.0 conflicting rows per real agent
(employee_code, vendor, team, name all flip). Entity resolution keyed on the
transactional id (`agent_id`), modal attributes per field, earliest `joined_at`
for tenure, newest row for status. 255 employee_codes are claimed
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
| borrowers | 30,600 | 19,585 | 11,015 |
| agents | 30,000 | 29,000 | 1,000 |
| calls | 91,350 | 1,350 | 90,000 |
| dispositions | 35,000 | 6,029 (+renames) | 28,971 |
| payments | 25,500 | 7,966 (status filter + duplicates) | 17,534 |
| attempts | 120,000 | 0 | 120,000 |
| statuses (history) | 60,000 | 0 (flagged 30,191) | 60,000 |

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
