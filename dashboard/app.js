/* ============================================================================
   Recovery Forensics — Executive Dashboard (single screen)
   Reads window.DASH (dashboard/data.js). Vanilla JS, no build step.
   A CEO should reach the decision in ~60 seconds: verdict -> money -> action.
   ========================================================================== */

const D = window.DASH;
const fmt = (v, d = 2) => (v == null ? "–" : Number(v).toLocaleString("en-IN", { maximumFractionDigits: d }));
const cr = (v, d = 2) => "₹" + fmt(v, d) + " Cr";

/* ------------------------------------------------------------------ header */
document.getElementById("badge-verdict").textContent = D.headline.verdict;
document.getElementById("verdict-detail").textContent = D.headline.verdict_detail;
document.getElementById("meta-window").textContent =
  "Data window: " + D.meta.data_window + " · " + D.meta.business_tz;
document.getElementById("portfolio-outstanding").textContent = cr(D.meta.portfolio_outstanding_cr, 0);

/* ------------------------------------------------------------------- kpis */
const kpis = [
  {
    label: "Actual recovery (Jan–Jul)",
    value: cr(D.headline.total_gold_cr),
    sub: "deduplicated SUCCESS cash, IST months",
  },
  {
    label: "Reported raw 'recovery'",
    value: cr(D.headline.total_raw_cr),
    sub: "includes ₹2.59 Cr double-posted rows",
    delta: (D.headline.total_raw_cr - D.headline.total_gold_cr).toFixed(2) + " Cr inflated",
  },
  {
    label: "True MoM trend",
    value: (D.headline.trend.slope_per_month * 1).toFixed(3) + " Cr/mo",
    sub: "p = " + D.headline.trend.p_value.toFixed(2) + " — statistically flat (n.s.)",
  },
  {
    label: "PTP kept rate (reported → verified)",
    value: D.headline.tilting_errors.ptp_reported_kept_rate_pct + "% → " +
           D.headline.tilting_errors.ptp_verified_kept_rate_pct + "%",
    sub: "4,309 'KEPT' promises with zero cash",
  },
  {
    label: "Attribution drift",
    value: "₹0 → " + fmt(D.headline.tilting_errors.stale_touch_attribution_jul_cr) + " Cr",
    sub: "stale-touch credit by Jul under legacy logic",
  },
  {
    label: "Calls in wrong hour bucket",
    value: D.headline.tilting_errors.tz_misclassified_calls_pct + "%",
    sub: "before row-level timezone normalization",
  },
];
const kpiWrap = document.getElementById("kpi-strip");
kpis.forEach(k => {
  const el = document.createElement("div");
  el.className = "kpi card";
  el.innerHTML =
    '<div class="kpi-label">' + k.label + "</div>" +
    '<div class="kpi-value">' + k.value + "</div>" +
    (k.delta ? '<div class="kpi-sub warn">' + k.delta + "</div>" : "") +
    '<div class="kpi-sub">' + k.sub + "</div>";
  kpiWrap.appendChild(el);
});

/* --------------------------------------------------------- reported vs gold */
const momG = D.headline.gold_mom_pct; // aligned to months[1..]
new Chart(document.getElementById("chart-main"), {
  type: "line",
  data: {
    labels: D.headline.months,
    datasets: [
      {
        label: "Reported (raw SUCCESS incl. duplicates, Cr)",
        data: D.headline.raw_recovery_cr,
        borderColor: "#8b93ff",
        backgroundColor: "rgba(139,147,255,.12)",
        borderWidth: 2,
        tension: 0.25,
        pointRadius: 3,
      },
      {
        label: "Golden definition (deduplicated, IST attributed, Cr)",
        data: D.headline.gold_recovery_cr,
        borderColor: "#34d2a5",
        backgroundColor: "rgba(52,210,165,.12)",
        borderWidth: 2.5,
        tension: 0.25,
        pointRadius: 4,
      },
      {
        label: "MoM % (golden)",
        data: momG,
        yAxisID: "y2",
        borderColor: "rgba(255,190,80,.85)",
        borderDash: [5, 4],
        borderWidth: 1.5,
        pointRadius: 2.5,
        tension: 0.3,
      },
    ],
  },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#aab2c8", font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.05)" } },
      y: { ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.07)" } },
      y2: { position: "right", grid: { display: false }, ticks: { color: "rgba(255,190,80,.8)", callback: v => v + "%" } },
    },
  },
});

/* ---------------------------------------------------------------- funnel */
const F = D.funnel;
const avg = a => a.reduce((x, y) => x + y, 0) / a.length;
const funnelRows = [
  ["Accounts targeted / month", avg(F.targeted), "#5b7fff", Math.max(...F.targeted)],
  ["Contacted (any channel)", avg(F.contacted_all), "#4ea1f7", Math.max(...F.contacted_all)],
  ["Right-party contacts", avg(F.rpc), "#34d2a5", Math.max(...F.rpc)],
  ["Promises to pay", avg(F.ptp), "#f7b32b", Math.max(...F.ptp)],
  ["PTP verified by cash", avg(F.ptp_kept_verified), "#f76f4e", Math.max(...F.ptp)],
  ["Paying accounts", avg(F.paid), "#a26ef7", Math.max(...F.paid)],
];
const maxRow = Math.max(...funnelRows.map(r => r[1]));
const funnelBox = document.getElementById("funnel");
funnelRows.forEach(([label, val, color, den]) => {
  const row = document.createElement("div");
  row.className = "funnel-row";
  row.innerHTML =
    '<div class="funnel-label">' + label + "</div>" +
    '<div class="funnel-bar-wrap"><div class="funnel-bar" style="width:' +
    (100 * val / maxRow) + "%;background:" + color + '"></div></div>' +
    '<div class="funnel-value">' + fmt(val, 0) + "</div>";
  funnelBox.appendChild(row);
});

/* ------------------------------------------------------------- channel mix */
new Chart(document.getElementById("chart-channel"), {
  type: "bar",
  data: {
    labels: D.channel.months,
    datasets: [
      { label: "Voice", data: D.channel.voice, stack: "s", backgroundColor: "#3b6fe0" },
      { label: "WhatsApp", data: D.channel.whatsapp, stack: "s", backgroundColor: "#2fbf9f" },
      { label: "SMS", data: D.channel.sms, stack: "s", backgroundColor: "#f7b32b" },
      { label: "Field", data: D.channel.field, stack: "s", backgroundColor: "#a26ef7" },
    ],
  },
  options: {
    plugins: {
      stacked100: { enable: false },
      legend: { labels: { color: "#aab2c8", font: { size: 11 } } },
    },
    maintainAspectRatio: false,
    scales: {
      x: { stacked: true, ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.05)" } },
      y: { stacked: true, ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.07)" } },
    },
  },
});

/* ------------------------------------------------------- attribution lines */
new Chart(document.getElementById("chart-attrib"), {
  type: "line",
  data: {
    labels: D.headline.months,
    datasets: [
      { label: "RPC ≤14d (golden)", data: D.attribution.rpc14d_credit_cr, borderColor: "#34d2a5", borderWidth: 2, tension: .3 },
      { label: "Contact ≤7d", data: D.attribution.contact7d_credit_cr, borderColor: "#4ea1f7", borderWidth: 2, tension: .3 },
      { label: "Stale touch >30d (legacy system credits these)", data: D.attribution.stale_touch_credit_cr, borderColor: "#f76f4e", borderWidth: 2.5, tension: .3, borderDash: [6, 3] },
    ],
  },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#aab2c8", font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.05)" } },
      y: { ticks: { color: "#8f96ad", callback: v => v + " Cr" }, grid: { color: "rgba(255,255,255,.07)" } },
    },
  },
});

/* ------------------------------------------------------------- PTP chart */
new Chart(document.getElementById("chart-ptp"), {
  type: "bar",
  data: {
    labels: D.headline.months,
    datasets: [
      { label: "Reported PTP kept rate %", data: D.ptp_probe.reported_kept_rate_pct, backgroundColor: "#f76f4e" },
      { label: "Verified by cash %", data: D.ptp_probe.verified_kept_rate_pct, backgroundColor: "#34d2a5" },
    ],
  },
  options: {
    maintainAspectRatio: false,
    plugins: { legend: { labels: { color: "#aab2c8", font: { size: 11 } } } },
    scales: {
      x: { ticks: { color: "#8f96ad" }, grid: { color: "rgba(255,255,255,.05)" } },
      y: { ticks: { color: "#8f96ad", callback: v => v + "%" }, grid: { color: "rgba(255,255,255,.07)" } },
    },
  },
});

/* ------------------------------------------------------ counterfactual card */
const CF = D.counterfactual;
document.getElementById("cf-design").innerHTML = `
  <span class="chip">Treatment:</span> ${CF.design.treatment}<br>
  <span class="chip">Control:</span> ${CF.design.control}<br>
  <span class="chip">Matching:</span> ${CF.design.matching} (${CF.design.identified_cells} matched cells)`;
const bars = CF.recovery_per_targeted_account_inr;
new Chart(document.getElementById("chart-cf"), {
  type: "bar",
  data: {
    labels: ["Control pre", "Control post", "Treatment pre", "Treatment post"],
    datasets: [{
      label: "Recovery ₹ / targeted account / month",
      data: [bars.control_pre, bars.control_post, bars.treatment_pre, bars.treatment_post],
      backgroundColor: ["#3b6fe0", "#5b8bff", "#f7b32b", "#ffd166"],
    }],
  },
  options: {
    plugins: { legend: { display: false } },
    maintainAspectRatio: false,
    scales: {
      x: { ticks: { color: "#8f96ad" }, grid: { display: false } },
      y: { ticks: { color: "#8f96ad", callback: v => "₹" + (v / 1000).toFixed(0) + "k" }, grid: { color: "rgba(255,255,255,.07)" } },
    },
  },
});
document.getElementById("cf-verdict").innerHTML =
  "<b>Result: ₹" + fmt(CF.did_inr_per_account, 0) + "/account/month (" + CF.did_pct_of_treatment_pre +
  "%).</b> " + (CF.did_uncertainty ? "95% CI ₹" + fmt(CF.did_uncertainty.ci95_inr_per_acct[0],0) + " to ₹" +
  fmt(CF.did_uncertainty.ci95_inr_per_acct[1],0) + ", p = " + CF.did_uncertainty.p_value + " — " +
  "the CI straddles zero, so <b>no detectable strategy lift</b> (exploratory; needs a geo-split)." : "≈ no genuine lift.")
  + (CF.placebo_test ? " <em>Permutation placebo (2,000 arm-swaps): p = " + CF.placebo_test.p_placebo + ".</em>" : "")
  + " Counterfactual ≈ reality: <b>" + cr(CF.counterfactual_monthly_recovery_cr) + "</b> monthly recovery would have looked materially the same."
  + (D.counterfactual_pretrend ? " <em>Pre-trend check plotted in the notebook; null result treated as exploratory.</em>" : "");

/* -------------------------------------------------------- investment card */
const INV = D.investment;
const optRows = (INV.options || []).map(o => {
  const v = o.verdict.startsWith("INVEST")
    ? '<span class="ok">INVEST (option 5)</span>'
    : '<span class="warn">defer</span>';
  return `<tr><td><b>${o.name}</b><br><small>${o.evidence}</small></td>` +
         `<td>₹${o.cost_cr} Cr</td>` +
         `<td>${o.incremental_annual_cr.conservative} / <b>${o.incremental_annual_cr.base}</b> / ${o.incremental_annual_cr.upside}</td>` +
         `<td>${o.net_roi_base ?? o.gross_roi_base}x</td><td>${o.breakeven_months_base > 12 ? "—" : o.breakeven_months_base + " mo"}</td><td>${v}</td></tr>`;
}).join("");
const WF = INV.whatsapp_funnel || {};
document.getElementById("invest-body").innerHTML = `
  <div class="invest-pick">Recommendation: <b>Option 5 — WhatsApp / digital engagement</b> (sole primary investment; ₹3.5 Cr deploy now, ₹6.5 Cr risk-gated behind the geo-split test). The AI concierge is an implementation lever <i>inside</i> option 5, not a separate option.</div>
  <table class="mini-table">
    <tr><th>Option (all 6 compared)</th><th>Cost</th><th>Incr. ₹Cr/yr C/B/U</th><th>Net ROI base</th><th>B/E base</th><th>Call</th></tr>
    ${optRows}
  </table>
  <table class="mini-table" style="margin-top:8px">
    <tr><td>Why not all ₹10 Cr now</td><td>${INV.full_10cr_program.why_not_full_10_now}</td></tr>
    <tr><td>ROI convention</td><td>net ROI = (base incremental − cost) ÷ cost: ${(INV.full_10cr_program.net_roi_deployment_scoped)}x on the ₹3.5 Cr deployment; ${INV.full_10cr_program.net_roi_if_all_10_committed_today}x if all ₹10 Cr were committed today</td></tr>
    <tr><td>Funnel (measured)</td><td>raw event counts (clicks ≈ sends, lifecycle ~1:1) give no usable conversion rate — estimate anchored on ~${WF.sent_pm} msgs/mo × ₹${WF.cash_per_sent_message_inr}/msg → ${cr(WF.attributed_cash_pm_cr)} attributed cash/mo</td></tr>
    <tr><td>Cases</td><td>conservative ${WF.incremental_annual_cr.conservative} Cr · base <b>${WF.incremental_annual_cr.base} Cr</b> · upside ${WF.incremental_annual_cr.upside} Cr</td></tr>
    <tr><td>Timing</td><td>${INV.timing.breakeven_note}</td></tr>
    <tr><td>Downside</td><td>${INV.downside}</td></tr>
    <tr><td>Confidence</td><td>${INV.confidence}</td></tr>
    <tr><td>Attribution coverage</td><td>${D.attribution_coverage ? D.attribution_coverage.definition + " = <b>" + D.attribution_coverage.avg_pct + "%</b> (" + D.attribution_coverage.min_pct + "–" + D.attribution_coverage.max_pct + "% by month) — the canonical figure used across all reports" : ""}</td></tr>
  </table>`;

/* ------------------------------------------------------------- dq table */
const dqbox = document.getElementById("dq-table");
D.dq_flags.forEach(f => {
  const tr = document.createElement("tr");
  tr.innerHTML =
    '<td class="sev sev-' + f.severity + '">' + f.severity.toUpperCase() + "</td>" +
    "<td>" + f.flag + "</td><td>" + f.impact + "</td>" +
    '<td class="' + (f.fixed ? "ok" : "warn") + '">' + (f.fixed ? "repaired" : "flagged · contract fix needed") + "</td>";
  dqbox.appendChild(tr);
});

/* ---------------------------------------------------------------- footer */
document.getElementById("footer-defs").innerHTML =
  "<b>Definitions.</b> Recovery = deduplicated SUCCESS payments in the IST month they landed. " +
  "Denominator = every account opened ≤ month end (survivorship-proof). Attribution = last RPC ≤14d &gt; last contact ≤7d &gt; unattributed. " +
  "PTP kept counted only when verified cash follows the promise. <b>Assumptions.</b> No cost table in source: agent cost ₹110/hr fully loaded, " +
  "telephony ₹0.45/attempt, digital ₹0.20/message (disclosed in the memo).";
