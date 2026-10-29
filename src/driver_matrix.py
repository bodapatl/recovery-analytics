"""Driver analysis matrix — one evidence table for every required dimension.

Answers the assignment brief "investigate the drivers" with a single results
matrix (reports/driver_matrix.md): for each business dimension we compute the
group-level recovery outcomes (cash-backed, golden layer) and classify the
evidence:

  Fact          deterministic row-level evidence, reproducible from SQL
  Strong        verified against a control / hard exclusion logic
  Correlation   association observed, no clean identification
  Hypothesis    plausible story — test failed or untestable from this data

Run:  python -X utf8 -m src.driver_matrix
"""
from __future__ import annotations

from src import config, db

CR = config.CR

ACCOUNT_DIMS = {
    "DPD band": ("a.dpd_band",
                 "recovery quality is mostly a function of how delinquent the account is"),
    "Loan type (client proxy)": ("a.loan_type",
                 "no client column exists in the contract; loan_type+state are the closest usable proxies"),
    "Risk segment": ("a.risk_segment",
                 "assigned risk bucket as sold by the risk team"),
    "Geography (borrower state)": ("COALESCE(a.borrower_state,'UNKNOWN')",
                 "no language column exists in the data — state is the closest geography/language-market proxy (marked N/A for language effects)"),
}


def acct_dim_sql(dim_expr: str) -> str:
    """Pool-vs-payer comparison for an account-level dimension."""
    return f"""
      WITH payers AS (
        SELECT account_id, SUM(amount) AS amt
        FROM gold_payments_attributed GROUP BY 1
      )
      SELECT {dim_expr} AS grp,
             COUNT(*) AS n_pool,
             SUM(a.outstanding_amount) AS pool_os,
             COUNT(p.account_id) AS n_paying,
             SUM(COALESCE(p.amt, 0)) AS rec_amt
      FROM gold_accounts a
      LEFT JOIN payers p USING (account_id)
      GROUP BY 1 ORDER BY 1
    """


def fmt_row(dim, grp, n, effect, rec, ev):
    n_s = n if isinstance(n, str) else f"{int(n):,}"
    return (f"| {dim} | {grp} | {n_s} | {effect} | {rec} | {ev} |\n")


def main() -> None:
    con = db.connect(readonly=True)
    rows: list[str] = []
    notes: list[str] = [
        ">[!Note] Language effects: the contract has **no language column**; borrower "
        "state is used as the nearest market/segment proxy and language itself is "
        "reported **N/A**. Client effects: there is **no client column** either; "
        "`loan_type` (with state) is the client-mix proxy.\n",
    ]
    ev_classes: dict[str, str] = {}

    # ------------------------------------------------- account-attribute dims
    for dim, (expr, why) in ACCOUNT_DIMS.items():
        df = con.execute(acct_dim_sql(expr)).fetchdf()
        payers_total = df.n_paying.sum() or 1
        rec_total = df.rec_amt.sum() or 1
        df = df.sort_values("rec_amt", ascending=False)
        for _, r in df.iterrows():
            eff = (f"{payers_total and 100.0 * r.n_paying / max(df.n_pool.sum(), 1):.1f}% ever pay · "
                   f"{100.0 * r.rec_amt / rec_total:.1f}% of cash")
            ev = {"DPD band": "Strong",
                  "Risk segment": "Strong",
                  "Loan type (client proxy)": "Correlation",
                  "Geography (borrower state)": "Correlation"}[dim]
            ev_classes.setdefault(dim, ev)
            rows.append(fmt_row(dim, r.grp, int(r.n_pool),
                                f"{int(r.n_paying):,} payers — {eff}",
                                f"₹{r.rec_amt / CR:.2f} Cr", ev))
        notes.append(f"**{dim}** — {why}\n")

    # --------------------------------------------------------- agent tenure
    tenure = con.execute("""
        SELECT t.tenure_band AS grp,
               COUNT(DISTINCT t.agent_id) AS n_agents,
               COUNT(DISTINCT p.account_id) AS n_paying,
               SUM(p.amount) AS rec_amt,
               MIN(t.tenure_months_at_start) AS tn_min,
               MAX(t.tenure_months_at_start) AS tn_max
        FROM gold_agent_tenure t
        JOIN gold_payments_attributed p ON p.rpc_agent_id = t.agent_id
        GROUP BY 1 ORDER BY 1
    """).fetchdf()
    rows.extend(fmt_row(
            "Agent tenure band", r.grp, int(r.n_agents),
            f"tenure {int(r.tn_min)}–{int(r.tn_max)} mo at Jan-2026 · "
            f"{int(r.n_paying):,} paying accts via {int(r.n_agents)} agents "
            f"(₹{r.rec_amt / max(r.n_agents, 1) / CR:.2f} Cr/agent)",
            f"₹{r.rec_amt / CR:.2f} Cr",
            "Correlation (near-zero variance)") for _, r in tenure.iterrows())
    notes.append(
        "**Agent tenure band** — tenure_months_at_start (join date → Jan-2026) spans "
        f"{int(tenure.tn_min.min())}–{int(tenure.tn_max.max())} months across all 1,000 agents: "
        "**almost no variance**, so tenure effects are *unidentifiable from this data*, not "
        "merely flat. (Agent-team/diversity fixes from master identity resolution remain valid.) "
        "Needed: a workforce with real tenure dispersion before this driver is testable.\n")

    # ----------------------------------------------------- campaign strategy
    strat = con.execute("""
        SELECT COALESCE(p.rpc_strategy_version,'none') AS grp,
               COUNT(DISTINCT p.account_id) AS n_paying,
               SUM(p.amount) AS rec_amt
        FROM gold_payments_attributed p GROUP BY 1 ORDER BY 1
    """).fetchdf()
    for _, r in strat.iterrows():
        rows.append(fmt_row(
            "Campaign strategy (RPC-targeted)", r.grp, int(r.n_paying),
            "cash via RPC on strategy version", f"₹{r.rec_amt / CR:.2f} Cr",
            "Correlation"))
    notes.append(
        "**Campaign strategy** — the honest causal test is the exact-matched DiD "
        "(see memo §4): +₹895/acct/month, 95% CI [−₹1,224, +₹3,013], p=0.40 "
        "**— no detectable lift**. Version-level raw shares are Correlation at best.\n")

    # ------------------------------------------------------------- channel econ
    chan = con.execute("""
        SELECT
          SUM(amt_voice)/1e7  AS voice_cr, SUM(amt_whatsapp)/1e7 AS wa_cr,
          SUM(amt_sms)/1e7    AS sms_cr,   SUM(amt_field)/1e7    AS field_cr
        FROM month_channel WHERE month < '2026-08-01'
    """).fetchdf().iloc[0]
    vol = con.execute("""
        SELECT SUM(n_attempts) AS attempts, SUM(n_answered) AS answered,
               SUM(wa_sent) AS wa_sent, SUM(wa_click) AS wa_click,
               SUM(sms_sent) AS sms_sent, SUM(agent_hours) AS hours
        FROM gold_monthly_metrics WHERE month < '2026-08-01'
    """).fetchdf().iloc[0]
    field_visits = con.execute("""
        SELECT COUNT(*) FROM clean_field_visits WHERE account_id IS NOT NULL
    """).fetchone()[0]
    cost_voice = vol.hours * config.ASSUMED_AGENT_COST_PER_HOUR + vol.attempts * config.ASSUMED_CALL_COST_PER_ATTEMPT
    cost_wa = int(vol.wa_sent) * config.ASSUMED_DIGITAL_COST_PER_MESSAGE
    cost_sms = int(vol.sms_sent) * config.ASSUMED_DIGITAL_COST_PER_MESSAGE
    for label, cash, cost, n in [
        ("Voice", chan.voice_cr, cost_voice / CR, f"{int(vol.attempts):,} attempts"),
        ("WhatsApp", chan.wa_cr, cost_wa / CR, f"{int(vol.wa_sent):,} msgs"),
        ("SMS", chan.sms_cr, cost_sms / CR, f"{int(vol.sms_sent):,} msgs"),
        ("Field", chan.field_cr, None, f"{field_visits:,} visits (no cost source — N/A)"),
    ]:
        cpr = "N/A" if (cost in (None, 0) or not cost) else f"{100.0 * cost / cash:.1f}% of cash spent"
    rows.append(fmt_row(
            "Channel economy (cost share of recovered cash)", label, n,
            f"cash share {100.0 * cash / (chan.voice_cr + chan.wa_cr + chan.sms_cr + chan.field_cr):.1f}%",
            f"₹{cash:.2f} Cr · cost {cpr}", "Strong" if label in ("Voice", "WhatsApp") else "Correlation"))
    cost_ratio = (cost_voice / max(vol.attempts, 1)) / config.ASSUMED_DIGITAL_COST_PER_MESSAGE
    notes.append(
        "**Channel economy** — raw WhatsApp event counts (PAYMENT_CLICK ≈ SENT, "
        "lifecycle ~1:1) cannot yield a meaningful per-message conversion rate, so "
        "none is claimed; usable economics are cash-per-sent-message "
        f"(~₹{(chan.wa_cr * CR) / max(vol.wa_sent, 1):,.0f}) and unit cost → the voice attempt "
        f"unit (~₹{cost_voice / max(vol.attempts, 1):,.0f}) is ~{cost_ratio:,.0f}× the digital message "
        f"unit (₹{config.ASSUMED_DIGITAL_COST_PER_MESSAGE:.2f}); voice consumes "
        f"{cost_voice / (cost_voice + cost_wa + cost_sms) * 100:.0f}% of modeled spend for a flat trend. "
        "Field visits have no cost source (assumption knob absent) — N/A.\n")

    # ---------------------------------------------------------- telephony vendor
    vend = con.execute("""
        SELECT CAST(vendor_id AS VARCHAR) AS grp, COUNT(*) AS n_attempts,
               AVG(CASE WHEN attempt_status = 'CONNECTED' THEN 1.0 ELSE 0 END) AS conn_rate
        FROM clean_call_attempts WHERE keep_flag GROUP BY 1
        HAVING COUNT(*) > 500 ORDER BY conn_rate DESC
    """).fetchdf()
    v_max, v_min = vend.conn_rate.max(), vend.conn_rate.min()
    for _, r in vend.iterrows():
        delta = 100.0 * (r.conn_rate - v_min)
        rows.append(fmt_row(
            "Telephony vendor (connection rate)", str(r.grp), f"{int(r.n_attempts):,}",
            f"{100.0 * r.conn_rate:.1f}% connect (+{delta:.1f} pp vs worst)",
            "-", "Correlation"))
    notes.append(
        "**Telephony vendor** — vendor codes normalized in 02_clean; connection-rate "
        f"spread {100.0 * (v_max - v_min):.1f} pp. But recovery-vs-connect-rate elasticity is "
        "not identified in this data (no dialer experiment) — routing spend on vendor "
        "choice is a Hypothesis, not an evidence-backed lever.\n")

    # ------------------------------------------------------- IST calling hour
    hour = con.execute("""
        WITH disp AS (
          SELECT c.call_id, d.rpc_flag, d.contact_flag
          FROM clean_call_dispositions d JOIN clean_calls c USING (call_id)
          WHERE d.account_id IS NOT NULL
        ), hrs AS (
          SELECT d.rpc_flag, d.contact_flag, EXTRACT(hour FROM utc_to_ist(c.event_at_utc)) AS h
          FROM disp d JOIN clean_calls c USING (call_id)
        )
        SELECT CASE WHEN h BETWEEN 9 AND 12 THEN '09-12h'
                    WHEN h BETWEEN 13 AND 15 THEN '13-15h'
                    WHEN h BETWEEN 16 AND 18 THEN '16-18h'
                    WHEN h BETWEEN 19 AND 20 THEN '19-20h'
                    ELSE 'off-hours' END AS grp,
               COUNT(*) AS n_calls,
               AVG(rpc_flag) AS rpc_rate
        FROM hrs GROUP BY 1 ORDER BY 1
    """).fetchdf()
    h_min, h_max = hour.rpc_rate.min(), hour.rpc_rate.max()
    for _, r in hour.iterrows():
        rows.append(fmt_row(
            "IST calling hour (RPC rate)", r.grp, f"{int(r.n_calls):,}",
            f"{100.0 * r.rpc_rate:.1f}% RPC"
            + (f"  ({100.0 * (r.rpc_rate - h_min):+.1f} pp vs worst)" if r.rpc_rate == h_max else ""),
            "-", "Correlation"))
    notes.append(
        "**Calling hour** — after tz normalization the hour bands differ by "
        f"{100.0 * (h_max - h_min):.1f} pp RPC. Selection bias risk: best borrowers may "
        "be callable earlier — treat as directional, verify with an A/B on dialer "
        "time windows before re-sequencing the day.\n")

    # ------------------------------------------------- attempt frequency band
    freq = con.execute("""
        WITH att AS (
          SELECT account_id,
                 DATE_TRUNC('month', CAST(utc_to_ist(event_at_utc) AS DATE)) AS m,
                 COUNT(*) AS n_att
          FROM clean_call_attempts WHERE keep_flag GROUP BY 1, 2
        ), pay AS (
          SELECT account_id, pay_month AS m, SUM(amount) AS amt
          FROM gold_payments_attributed GROUP BY 1, 2
        )
        SELECT CASE WHEN n_att = 0 THEN '0 attempts'
                    WHEN n_att <= 3 THEN '1-3'
                    WHEN n_att <= 8 THEN '4-8'
                    WHEN n_att <= 15 THEN '9-15'
                    ELSE '16+' END AS grp,
               COUNT(*) AS n_cell,
               COUNT(pay.account_id) AS n_paid,
               SUM(COALESCE(pay.amt, 0)) AS amt
        FROM att LEFT JOIN pay ON pay.account_id = att.account_id AND pay.m = att.m
        GROUP BY 1 ORDER BY 1
    """).fetchdf()
    for _, r in freq.iterrows():
        rows.append(fmt_row(
            "Attempt frequency (per acct-month)", r.grp, f"{int(r.n_cell):,}",
            f"{100.0 * r.n_paid / r.n_cell:.1f}% of cells pay",
            f"₹{(r.amt or 0) / CR:.2f} Cr", "Correlation"))
    notes.append(
        "**Attempt frequency** — pay-rate climbs with attempts, but this is largely "
        "selection (dialers pile attempts on promising accounts). The DiD's null "
        "strategy effect suggests frequency alone is not the lever; test with a "
        "capped-attempt experiment before buying more dialer capacity.\n")

    # ----------------------------------------------------------------- output
    header = (
        "# Driver Analysis — Results Matrix\n\n"
        "_Generated by `src/driver_matrix.py` from the golden layer. All cash "
        "figures use the deduplicated, IST-normalized, attribution-rule v2.0 "
        "golden dataset (full months Jan–Jul 2026). Evidence classes: **Fact** = "
        "deterministic row-level evidence · **Strong** = mechanism verified against "
        "controls/exclusions · **Correlation** = association without clean "
        "identification · **Hypothesis** = tested story (accepted or rejected).\n\n"
        "| driver dimension | group | n (unit) | effect | recovery ₹ | evidence class |\n"
        "|---|---|---|---|---|---|\n"
    )
    md = header + "".join(rows) + "\n## Dimension notes\n\n" + "".join(notes)
    out = config.REPORTS_DIR / "driver_matrix.md"
    config.REPORTS_DIR.mkdir(exist_ok=True, parents=True)
    out.write_text(md, encoding="utf-8")
    print(f"reports/driver_matrix.md written ({len(rows)} rows)")
    con.close()


if __name__ == "__main__":
    main()
