"""Shared configuration for the recovery-analytics pipeline."""
from __future__ import annotations

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
GOLD_DIR = DATA_DIR / "golden"
SQL_DIR = ROOT / "sql"
REPORTS_DIR = ROOT / "reports"
ANALYSIS_DIR = ROOT / "analysis"
DASHBOARD_DIR = ROOT / "dashboard"

GOLD_DB = GOLD_DIR / "analytics.duckdb"

# ---------------------------------------------------------------------------
# Business clock
# ---------------------------------------------------------------------------
BUSINESS_TZ = "Asia/Kolkata"          # everything is reported in IST
PARTIAL_MONTH = "2026-08"             # data ends 2026-08-08 -> partial month

RAW_FILES = {
    "borrowers": "borrowers.csv",
    "accounts": "accounts.csv",
    "agents": "agents.csv",
    "agent_sessions": "agent_sessions.csv",
    "campaigns": "campaigns.csv",
    "daily_targeting": "daily_targeting.csv",
    "calls": "calls.csv",
    "call_attempts": "call_attempts.csv",
    "call_dispositions": "call_dispositions.csv",
    "whatsapp_events": "whatsapp_events.csv",
    "sms_events": "sms_events.csv",
    "field_visits": "field_visits.csv",
    "promises_to_pay": "promises_to_pay.csv",
    "payments": "payments.csv",
    "vendor_telephony": "vendor_telephony.csv",
    "account_status_history": "account_status_history.csv",
    "complaints": "complaints.csv",
}

# ---------------------------------------------------------------------------
# Documented assumptions for money-denominated KPIs that have no source table
# (voluntarily disclosed in the memo; a cost table would remove the need)
# ---------------------------------------------------------------------------
ASSUMED_AGENT_COST_PER_HOUR = 110.0     # fully loaded INR / agent-hour
ASSUMED_CALL_COST_PER_ATTEMPT = 0.45    # telephony variable cost / attempt
ASSUMED_DIGITAL_COST_PER_MESSAGE = 0.20 # WA/SMS blended cost / message

# CR for scaling in copy
CR = 1e7
