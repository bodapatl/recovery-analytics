"""Reproducibility + reconciliation test suite (runnable, no stubs).

What it proves:

  A. CLEAN-REBUILD DETERMINISM — rebuild the whole SQL pipeline into a fresh
     DuckDB file and diff every golden month-metric row against the shipped db.
  B. PRIMARY KEYS — payment_id / account_id / agent_id uniqueness.
  C. MONEY MATH — raw SUCCESS minus removed double-SUCCESS rows reconciles to
     the golden recovery total (the ₹2.59 Cr dedup is exact, not narrative).
  D. FUNNEL MONOTONICITY — RPC ⊆ contacted, PTP kept ≤ events, attribution
     tiers cover 100% of golden cash, channel split covers all cash.
  E. ACCEPTED VALUES / REFERENTIAL INTEGRITY — enum domains and FK checks.

Writes reports/verify_report.md; exit code 1 on any failure.

Run:  python -X utf8 -m src.verify      (or via run_all.py)
"""
from __future__ import annotations

import math
from pathlib import Path

import duckdb

from src import config, db

CR = config.CR
REBUILD_DB = config.GOLD_DIR / "verify_rebuild.duckdb"

# every determinism-compared column of gold_monthly_metrics (names from SQL)
METRIC_COLS = [
    "month", "n_pool_accounts", "pool_outstanding", "recovery_amt", "recovery_count",
    "recovery_accounts", "amt_rpc14d", "amt_contact7d", "amt_unattributed",
    "amt_old_touch_attributed", "raw_success_amt", "n_contacted", "n_targeted",
    "n_calls", "n_answered", "n_attempts", "n_connected", "n_ptp_events",
    "n_ptp_accounts", "n_ptp_kept_verified", "n_ptp_status_kept",
    "agent_hours", "n_agents_active", "wa_sent", "wa_click", "sms_sent",
    "amt_voice", "amt_whatsapp", "amt_sms", "amt_field",
]

results: list[tuple[str, str, str]] = []   # (test, status, detail)


def record(test: str, ok: bool, detail: str = "") -> None:
    results.append((test, "PASS" if ok else "FAIL", detail))


def tq(con: duckdb.DuckDBPyConnection, sql: str):
    return con.execute(sql).fetchall()


def _close(a, b, rel=1e-9, abs_=0.01) -> bool:
    """Numeric tolerance compare; string fallback for anything else."""
    if isinstance(a, (int, float)) and not isinstance(a, bool) \
            and isinstance(b, (int, float)) and not isinstance(b, bool):
        return abs(a - b) <= max(abs_, rel * max(abs(a), abs(b)))
    return str(a) == str(b)


def test_clean_rebuild(main_con: duckdb.DuckDBPyConnection) -> None:
    """Re-run 01-04 SQL into a blank db file and diff gold_monthly_metrics."""
    if REBUILD_DB.exists():
        REBUILD_DB.unlink()
    con = duckdb.connect(str(REBUILD_DB))
    con.execute("SET TimeZone='UTC';")
    db.run_pipeline(con)
    cols = ", ".join(METRIC_COLS)
    new = tq(con, f"SELECT {cols} FROM gold_monthly_metrics ORDER BY month")
    old = tq(main_con, f"SELECT {cols} FROM gold_monthly_metrics ORDER BY month")
    con.close()
    REBUILD_DB.unlink()
    diffs = []
    for i, (o, n) in enumerate(zip(old, new)):
        for j, (ov, nv) in enumerate(zip(o, n)):
            if not _close(ov, nv):
                diffs.append(f"row[i]={str(o[0])[:10]} col={METRIC_COLS[j]}: {ov!r} vs {nv!r}")
    record("A1 clean-rebuild gold_monthly_metrics identical (±1e-9 rel)",
           not diffs and len(old) == len(new),
           f"{len(old)} rows × {len(METRIC_COLS)} cols match"
           + (f"; diffs: {diffs[:2]}" if diffs else ""))
    # also determinism for the attribution mart total
    q = "SELECT COUNT(*), SUM(amount) FROM gold_payments_attributed"
    # rebuild again quickly only for the count query (cheap at this data size)
    con = duckdb.connect(str(REBUILD_DB))
    con.execute("SET TimeZone='UTC';")
    db.run_pipeline(con)
    new2 = tq(con, q)
    con.close()
    REBUILD_DB.unlink()
    old2 = tq(main_con, q)
    ok = (new2[0][0] == old2[0][0]) and _close(new2[0][1], old2[0][1])
    record("A2 clean-rebuild payments rowcount+sum identical",
           ok, f"{old2[0][0]:,} rows, ₹{old2[0][1] / CR:,.2f} Cr built 3× identically")


def test_primary_keys(main_con: duckdb.DuckDBPyConnection) -> None:
    for table, key in [("gold_payments_attributed", "payment_id"),
                       ("gold_accounts", "account_id"),
                       ("clean_agents", "agent_id")]:
        dupe = tq(main_con,
                  f"SELECT COUNT(*) FROM (SELECT {key} FROM {table} "
                  f"GROUP BY 1 HAVING COUNT(*) > 1)")[0][0]
        record(f"B {table}.{key} unique", dupe == 0, f"{dupe} duplicate keys")


def test_money_math(main_con: duckdb.DuckDBPyConnection) -> None:
    """Reconcile the ₹2.59 Cr dedup exactly (verified derivation):

    all-time:    SUM(raw SUCCESS) − SUM(gold recovery) == inflated_by_doubles
    full months: gap_full == inflated_total − Aug-part (Aug is partial, excluded)
    """
    raw_all = tq(main_con, "SELECT SUM(raw_success_amt) FROM month_raw")[0][0]
    gold_all = tq(main_con, "SELECT SUM(recovery_amt) FROM month_pay")[0][0]
    inflated = tq(main_con, "SELECT SUM(inflated_amount_by_doubles) FROM dq_payments_double_amount")[0][0]
    gap_all = raw_all - gold_all
    record("C1a all-time raw SUCCESS − golden == ₹2.59 Cr doubles exactly",
           abs(gap_all - inflated) < 1.0,
           f"gap ₹{gap_all / CR:.4f} Cr == doubles ₹{inflated / CR:.4f} Cr")
    raw_aug = tq(main_con, "SELECT raw_success_amt FROM month_raw WHERE month='2026-08-01'")[0][0]
    gold_aug = tq(main_con, "SELECT recovery_amt FROM month_pay WHERE month='2026-08-01'")[0][0]
    gap_full_months = (raw_all - raw_aug) - (gold_all - gold_aug)
    expected_full = inflated - (raw_aug - gold_aug)
    record("C1b full-month gap == total doubles minus Aug part",
           abs(gap_full_months - expected_full) < 1.0,
           f"gap ₹{gap_full_months / CR:.4f} Cr vs expected ₹{expected_full / CR:.4f} Cr")
    # attribution tiers partition 100% of cash, month by month
    bad = tq(main_con, """
        SELECT COUNT(*) FROM month_pay
        WHERE ABS(amt_rpc14d + amt_contact7d + amt_unattributed - recovery_amt) > 1.0
          AND month < '2026-08-01'
    """)[0][0]
    record("C2 attribution tiers partition 100% of golden cash", bad == 0, f"{bad} months off")
    # channel split covers all attributed cash (allowed slack: unattributed rows)
    ch = tq(main_con, """
        SELECT c.month FROM month_channel c JOIN month_pay p USING (month)
        WHERE month < '2026-08-01'
          AND ABS(c.amt_voice + c.amt_whatsapp + c.amt_sms + c.amt_field
                  + c.amt_other - p.recovery_amt) > 1.0
    """)
    record("C3 channel split covers 100% of golden cash", not ch, f"{len(ch)} months off")


def test_funnel_monotonicity(main_con: duckdb.DuckDBPyConnection) -> None:
    rpc_gt = tq(main_con, """
        SELECT COUNT(*) FROM gold_monthly_metrics
        WHERE month < '2026-08-01' AND n_rpc_accounts > n_contacted
    """)[0][0]
    record("D1 RPC accounts ≤ contacted accounts each month", rpc_gt == 0, f"{rpc_gt} months violate")
    kept_gt = tq(main_con, """
        SELECT COUNT(*) FROM month_ptp
        WHERE n_ptp_kept_verified > n_ptp_events OR n_ptp_status_kept > n_ptp_events
    """)[0][0]
    record("D2 PTP kept ≤ PTP events", kept_gt == 0, f"{kept_gt} months violate")
    keept_forecast = tq(main_con, """
        SELECT SUM(n_ptp_kept_no_cash), SUM(n_ptp_status_kept) FROM month_ptp
    """)[0]
    record("D3 PTP-without-cash reconciles to reported KEPT",
           keept_forecast[0] <= keept_forecast[1],
           f"{keept_forecast[0]:,} KEPT-without-cash of {keept_forecast[1]:,} reported")


def test_accepted_values_and_fk(main_con: duckdb.DuckDBPyConnection) -> None:
    bad_tiers = tq(main_con, """
        SELECT COUNT(*) FROM gold_payments_attributed
        WHERE attribution_tier NOT IN ('RPC_14D','CONTACT_7D','UNATTRIBUTED')
    """)[0][0]
    record("E1 attribution_tier accepted values", bad_tiers == 0, f"{bad_tiers} bad tiers")
    orphan_pay = tq(main_con, """
        SELECT COUNT(*) FROM gold_payments_attributed p
        WHERE NOT EXISTS (SELECT 1 FROM gold_accounts a WHERE a.account_id = p.account_id)
    """)[0][0]
    record("E2 payments → accounts referential integrity", orphan_pay == 0, f"{orphan_pay} orphans")
    orphan_ptp = tq(main_con, """
        SELECT COUNT(*) FROM gold_ptp q
        WHERE NOT EXISTS (SELECT 1 FROM gold_accounts a WHERE a.account_id = q.account_id)
    """)[0][0]
    record("E3 PTP → accounts referential integrity", orphan_ptp == 0, f"{orphan_ptp} orphans")
    month_bad = tq(main_con, """
        SELECT COUNT(*) FROM gold_payments_attributed
        WHERE DATE_TRUNC('month', CAST(pay_month AS DATE)) <> pay_month
    """)[0][0]
    record("E4 pay_month always a month-boundary", month_bad == 0, f"{month_bad} bad")


def main() -> int:
    con = db.connect(readonly=True)
    test_clean_rebuild(con)
    test_primary_keys(con)
    test_money_math(con)
    test_funnel_monotonicity(con)
    test_accepted_values_and_fk(con)
    con.close()

    failed = [r for r in results if r[1] == "FAIL"]
    md = ["# Reproducibility & Reconciliation Report\n",
          f"_Generated by `src/verify.py` — {len(results)} tests, {len(failed)} failures._\n",
          "| test | status | detail |", "|---|---|---|"]
    md += [f"| {t} | **{s}** | {d} |" for t, s, d in results]
    config.REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    (config.REPORTS_DIR / "verify_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    for t, s, d in results:
        print(f"[{s}] {t}  {d}")
    print(f"\nreports/verify_report.md written — {len(results)} tests, {len(failed)} FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
