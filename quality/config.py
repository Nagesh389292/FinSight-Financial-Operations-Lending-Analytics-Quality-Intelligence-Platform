"""
FinSight Enterprise — Quality Assurance & Defect Injection Configuration (Stage 2.4)
"""

from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent.parent
BASELINE_DIR = BASE_DIR / "data" / "generated" / "servicing"
CONTRACTS_DIR = BASE_DIR / "data" / "generated" / "contracts"
SCENARIO_DEFECT_DIR = BASE_DIR / "data" / "scenarios" / "defect_injection_001"
OUTPUT_DEFECTS_DIR = BASE_DIR / "data" / "generated" / "defects"

DEFAULT_SEED = 20261006
REFERENCE_TIMESTAMP = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)

# Controlled defect injection proportion (~2.5% of eligible test scenarios)
DEFECT_RATE_TARGET = 0.0250

# Authoritative RTM Defect Taxonomy
DEFECT_TAXONOMY = {
    "DAY_COUNT_MISMATCH": {
        "title": "Day-Count Convention Mismatch (Actual/360 applied to Actual/365)",
        "requirement_id": "BRD-FIN-001",
        "rule_id": "RULE-ACCR-002",
        "test_case_id": "TC-ACCR-002",
        "severity": "MAJOR",
        "priority": "P2",
        "description": "Servicing engine applied Actual/360 day-count denominator (360) to a contractual Actual/365 facility, artificially inflating accrued interest."
    },
    "ROUNDING_TRUNCATION": {
        "title": "Premature Precision Truncation (Penny Drift Breach)",
        "requirement_id": "BRD-FIN-001",
        "rule_id": "RULE-ACCR-001",
        "test_case_id": "TC-ROUND-001",
        "severity": "MINOR",
        "priority": "P3",
        "description": "Calculation pipeline executed raw float truncation instead of Banker's Rounding (ROUND_HALF_EVEN), introducing multi-cent cumulative drift."
    },
    "WATERFALL_ORDERING": {
        "title": "Payment Priority Waterfall Reversal (Principal before Interest/Fees)",
        "requirement_id": "BRD-CORE-006",
        "rule_id": "RULE-WATERFALL-001",
        "test_case_id": "TC-WATERFALL-002",
        "severity": "CRITICAL",
        "priority": "P1",
        "description": "Servicing allocation engine violated contractual hierarchy by applying cash to principal reduction before satisfying outstanding late fees and accrued interest."
    },
    "LEAP_YEAR_BLINDNESS": {
        "title": "Leap Year Accrual Blindness (Missing Feb 29 Leap Day)",
        "requirement_id": "BRD-FIN-001",
        "rule_id": "RULE-ACCR-002",
        "test_case_id": "TC-ACCR-002",
        "severity": "MAJOR",
        "priority": "P2",
        "description": "Daily interest calculation engine ignored the 29th leap day in February 2024, causing a full day's interest accrual deficit."
    }
}
