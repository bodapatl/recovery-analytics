# Production Analytics Design — Collections Recovery System

Target state: the golden layer built for this assignment runs daily so
leadership sees yesterday's truth, not last week's story.

```
RAW (17 sources) → STAGING (typed views) → CLEAN (dedup / entity / tz)
   → GOLDEN (marts) → FEATURE / METRICS (monthly + daily) → DASHBOARD + ALERTS
```

## 1. Pipeline layers

| layer | technology | contract | SLA |
|---|---|---|---|
| RAW | SFTP / API / S3 landing per source | append-only, immutable files, `_ingested_at` stamped | by 02:00 IST |
| STAGING | DuckDB / Spark views (this repo's `01_staging.sql`) | everything VARCHAR first, typed + tz-normalized only here | same day |
| CLEAN | SQL transforms (`02_clean.sql`) | deterministic SQL only; every rule has a `dq_*` ledger row | same day |
| GOLDEN | marts (`03_golden.sql`) | idempotent `CREATE OR REPLACE`, full-refresh safe | 04:00 IST |
| METRICS | `month_*` marts + feature views | metric definitions versioned in `metric_definitions.yml` | 04:30 IST |

## 2. Data contracts (source → consumer)

- **Primary keys (declared, enforced, and audited):**
  payments: `payment_id` (UNIQUE enforced — 500 doubles would fail CI),
  dispositions: `disposition_id`, calls: `call_id`, attempts: `attempt_id`,
  accounts: `account_id`, borrowers: `borrower_id`, agents: `agent_id`,
  touchpoints: synthetic `(source_type, source_id)`.
- **NOT keys:** `payment_reference` is re-used upstream (1,782 observed
  collisions) — joins keyed on it are forbidden at the semantic layer.
- Schema drift policy: additive columns auto-accepted; renames break the
  build; a `source_schema_versions` table records each change.
- Freshness: every source exposed via a `source_freshness` view
  (`max(event_at)` per source/day); SLA breach pages the owning team.

## 3. Metric definitions (single source of truth)

`metric_definitions.yml` holds: recovery (deduped SUCCESS, IST month),
recovery_rate (denominator = accounts opened ≤ month end), contact/RPC/PTP
rates (per targeted account), PTP_kept (verified-cash only), recovery per
agent-hour, cost per ₹ recovered (assumption-driven, parameterised).
Dashboard/memo read **only** these definitions — the "reported" legacy variant
is still computed (suffix `_legacy`) to keep the before/after bridge honest.

## 4. Incremental processing, late data, backfills

- Event tables process incrementally by `event_at_utc` watermark + 72h late
  window (late-arriving events were 30,191/60,000 in status history — huge, so
  the watermark must trail generously).
- Payments restate the **full attribution window** on every late arrival
  (model = `dbt incremental` with `incremental_predicates` on month + a 45-day
  reprocess tail).
- Backfills = full refresh by construction (golden layer is idempotent for
  640k rows / day in DuckDB at <4 min today); at production scale, partitioned
  by month with `WHERE month >= :from` partial refresh.

## 5. Data-quality checks (run every cycle, non-blocking vs blocking)

| check | rule | severity |
|---|---|---|
| row_count | ±30% vs 28-day rolling median per source | block |
| uniqueness | PK uniqueness per contract table | block |
| dup-money | duplicate (payment_id) SUCCESS rows == 0 | block |
| attribution | % payments with `latest_touch_gap_days > 30` ≤ 15% | warn |
| tz hygiene | % rows with unknown timezone == 0 | block |
| freshness | `max(event_at)` per source ≥ yesterday | block |
| PTP sanity | share of KEPT-verified ≥ 2% (it was 3.6%) | warn |
| volume mix | targeted/contacted counts within ±25% MoM | warn |

## 6. Monitoring & anomaly detection

- **Metric monitors:** recovery/day (prophet-lite: 28-day median + MAD bands),
  contact rate, RPC rate, funnel step conversions — alerts annotate the
  dashboard, never silently shift definitions.
- **Structural break detectors:** CUSUM on daily recovery + targeted volume;
  any break auto-adds a `metric_context` annotation the dashboard renders.
- **Definition drift alarm:** any change to `metric_definitions.yml` requires a
  PR with re-run of the last 90 days and a published before/after bridge
  (this assignment's §3 exactly).
- **Lineage:** dbt docs DAG from source CSVs → golden marts → dashboard tiles;
  every number on the dashboard is traceable to a SQL file + git SHA stamped
  into each export (`data.js.meta` today).

## 7. Repo map (this assignment → production)

| assignment artifact | production component |
|---|---|
| `sql/01..04` | dbt project `staging/clean/golden/marts` models |
| `src/pipeline.py` | orchestrator (Airflow/cron) + golden export job |
| `src/forensics.py` | `dq_*` suite → Great Expectations suite |
| `src/analysis.py` | scheduled notebook/semantic-layer refresh |
| `dashboard/` | cached static export + alert annotations |
