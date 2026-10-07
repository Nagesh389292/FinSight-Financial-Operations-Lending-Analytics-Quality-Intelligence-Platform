"""
FinSight Enterprise — Servicing Engine Configuration (Stage 2.3)
"""

from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = BASE_DIR / "data" / "generated" / "contracts"
OUTPUT_SERVICING_DIR = BASE_DIR / "data" / "generated" / "servicing"

DEFAULT_SEED = 20261006
REFERENCE_TIMESTAMP = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)
AS_OF_DATE = datetime(2024, 6, 30).date()

# Number of monthly servicing cycles to simulate per facility
DEFAULT_SIMULATION_CYCLES = 6

# Servicing payment behaviors and deterministic weights
SERVICING_BEHAVIORS = [
    ("ON_TIME", 0.82),
    ("LATE", 0.08),
    ("EARLY", 0.05),
    ("PARTIAL", 0.03),
    ("MISSED", 0.02)
]

# Chart of Accounts for General Ledger double-entry posting
GL_CHART_OF_ACCOUNTS = {
    "10100": {"name": "Cash and Clearing Account", "category": "ASSET"},
    "12000": {"name": "Loans Principal Receivable", "category": "ASSET"},
    "12100": {"name": "Accrued Interest Receivable", "category": "ASSET"},
    "12200": {"name": "Fees and Charges Receivable", "category": "ASSET"},
    "40100": {"name": "Interest Income", "category": "REVENUE"},
    "40200": {"name": "Loan Servicing & Fee Income", "category": "REVENUE"}
}

# Delinquency buckets per banking regulatory guidelines
DPD_BUCKETS = [
    (0, 0, "CURRENT", "CURRENT"),
    (1, 29, "BUCKET_1", "GRACE_PERIOD"),
    (30, 59, "BUCKET_2", "DELINQUENT_30"),
    (60, 89, "BUCKET_3", "DELINQUENT_60"),
    (90, 999999, "DEFAULT", "DEFAULT_90_PLUS")
]
