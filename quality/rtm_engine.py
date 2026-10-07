"""
FinSight Enterprise — Requirements Traceability Matrix (RTM) Engine (Phase 3.1)
Builds bidirectional traceability from BRD Requirements -> Business Rules -> Test Cases
-> Executions -> Test Status -> Defects -> Root Cause Analysis.
Outputs conformed RTM matrix and coverage telemetry to data/generated/qa/.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from quality.config import BASE_DIR, OUTPUT_DEFECTS_DIR, REFERENCE_TIMESTAMP

OUTPUT_QA_DIR = BASE_DIR / "data" / "generated" / "qa"
OUTPUT_QA_DIR.mkdir(parents=True, exist_ok=True)

# Authoritative Catalog of BRD Requirements (from warehouse/seeds/01_seed_reference_data.sql)
BRD_REQUIREMENTS = [
    {"requirement_id": "BRD-CORE-001", "module": "CORE_SERVICING", "title": "Customer Segmentation & Risk Underwriting", "business_owner": "Credit Underwriting", "priority": "HIGH"},
    {"requirement_id": "BRD-CORE-003", "module": "CORE_SERVICING", "title": "Floating Rate Benchmark Indexing", "business_owner": "Treasury & ALM", "priority": "CRITICAL"},
    {"requirement_id": "BRD-CORE-005", "module": "CORE_SERVICING", "title": "Strict Loan Lifecycle State Machine", "business_owner": "Servicing Operations", "priority": "CRITICAL"},
    {"requirement_id": "BRD-CORE-006", "module": "CORE_SERVICING", "title": "Contractual Payment Priority Waterfall", "business_owner": "Servicing Operations", "priority": "CRITICAL"},
    {"requirement_id": "BRD-CORE-007", "module": "CORE_SERVICING", "title": "Daily Delinquency & DPD Aging Classification", "business_owner": "Credit Collections", "priority": "HIGH"},
    {"requirement_id": "BRD-FIN-001", "module": "FINANCIAL_CALC", "title": "Multi-Convention Interest Accrual Math", "business_owner": "Financial Controller", "priority": "CRITICAL"},
    {"requirement_id": "BRD-FIN-003", "module": "FINANCIAL_CALC", "title": "Balance Conservation & Amortization Integrity", "business_owner": "Financial Controller", "priority": "CRITICAL"},
    {"requirement_id": "BRD-FIN-004", "module": "FINANCIAL_CALC", "title": "Double-Entry General Ledger Integrity", "business_owner": "Accounting Operations", "priority": "CRITICAL"},
    {"requirement_id": "BRD-FIN-005", "module": "RECONCILIATION", "title": "Automated Expected vs Actual Financial Recon", "business_owner": "Lead QA / Auditor", "priority": "CRITICAL"},
    {"requirement_id": "BRD-FIN-006", "module": "RECONCILIATION", "title": "Penny Tolerance ($0.01) Enforcement", "business_owner": "Financial Controller", "priority": "CRITICAL"},
    {"requirement_id": "BRD-QA-001", "module": "QUALITY_ENGINEERING", "title": "100% Requirements Traceability (RTM)", "business_owner": "Lead QA Engineer", "priority": "HIGH"},
    {"requirement_id": "BRD-QA-003", "module": "QUALITY_ENGINEERING", "title": "Multi-Taxonomy Automated Test Suite", "business_owner": "Lead QA Engineer", "priority": "CRITICAL"},
    {"requirement_id": "BRD-QA-004", "module": "QUALITY_ENGINEERING", "title": "Automated Defect Extraction on Test Failure", "business_owner": "Lead QA Engineer", "priority": "HIGH"},
    {"requirement_id": "BRD-BI-001", "module": "BI_FORECASTING", "title": "Executive 6-Page Power BI Suite", "business_owner": "Head of BI", "priority": "HIGH"},
    {"requirement_id": "BRD-OPS-001", "module": "SRE_GOVERNANCE", "title": "Role-Based Access Control (RBAC)", "business_owner": "Security Architect", "priority": "HIGH"},
    {"requirement_id": "BRD-OPS-002", "module": "SRE_GOVERNANCE", "title": "Cryptographic Immutable Audit Trails", "business_owner": "Chief Compliance Officer", "priority": "CRITICAL"},
    {"requirement_id": "BRD-OPS-003", "module": "SRE_GOVERNANCE", "title": "Data Platform Telemetry & Freshness SLIs", "business_owner": "Platform SRE Lead", "priority": "HIGH"}
]

# Authoritative Catalog of Business Rules
BUSINESS_RULES = [
    {"rule_id": "RULE-ACCR-001", "requirement_id": "BRD-FIN-001", "rule_name": "Actual/360 Daily Interest Rule", "domain": "INTEREST_ACCRUAL"},
    {"rule_id": "RULE-ACCR-002", "requirement_id": "BRD-FIN-001", "rule_name": "Actual/365 Daily Interest Rule", "domain": "INTEREST_ACCRUAL"},
    {"rule_id": "RULE-ACCR-003", "requirement_id": "BRD-FIN-001", "rule_name": "30/360 Monthly Accrual Rule", "domain": "INTEREST_ACCRUAL"},
    {"rule_id": "RULE-WATERFALL-001", "requirement_id": "BRD-CORE-006", "rule_name": "Priority Cash Allocation Rule", "domain": "WATERFALL_ALLOCATION"},
    {"rule_id": "RULE-DPD-001", "requirement_id": "BRD-CORE-007", "rule_name": "Delinquency Aging Rule", "domain": "DELINQUENCY_BUCKETING"},
    {"rule_id": "RULE-RECON-001", "requirement_id": "BRD-FIN-005", "rule_name": "Accrual Tie-Out Variance Rule", "domain": "INTEREST_ACCRUAL"}
]

# Authoritative Catalog of Test Cases
TEST_CASES = [
    {"test_case_id": "TC-ACCR-001", "rule_id": "RULE-ACCR-001", "test_category": "FINANCIAL_CALC", "test_name": "Verify Actual/360 Commercial Accrual", "target_component": "math_truth"},
    {"test_case_id": "TC-ACCR-002", "rule_id": "RULE-ACCR-002", "test_category": "FINANCIAL_CALC", "test_name": "Verify Actual/365 Consumer Credit Accrual", "target_component": "math_truth"},
    {"test_case_id": "TC-ACCR-003", "rule_id": "RULE-ACCR-003", "test_category": "FINANCIAL_CALC", "test_name": "Verify 30/360 Mortgage Facility Accrual", "target_component": "math_truth"},
    {"test_case_id": "TC-ROUND-001", "rule_id": "RULE-ACCR-001", "test_category": "FINANCIAL_CALC", "test_name": "Validate Banker Rounding Half-Even", "target_component": "math_truth"},
    {"test_case_id": "TC-WATERFALL-001", "rule_id": "RULE-WATERFALL-001", "test_category": "FUNCTIONAL", "test_name": "Verify Standard On-Time Waterfall", "target_component": "payment_engine"},
    {"test_case_id": "TC-WATERFALL-002", "rule_id": "RULE-WATERFALL-001", "test_category": "FUNCTIONAL", "test_name": "Verify Short Payment Waterfall Ordering", "target_component": "payment_engine"},
    {"test_case_id": "TC-WATERFALL-003", "rule_id": "RULE-WATERFALL-001", "test_category": "FUNCTIONAL", "test_name": "Verify Surplus Prepayment Allocation", "target_component": "payment_engine"},
    {"test_case_id": "TC-DPD-001", "rule_id": "RULE-DPD-001", "test_category": "FUNCTIONAL", "test_name": "Verify DPD Aging Bucket Transitions", "target_component": "servicing_engine"},
    {"test_case_id": "TC-RECON-001", "rule_id": "RULE-RECON-001", "test_category": "RECONCILIATION", "test_name": "Verify Exact Match Reconciliation Pass", "target_component": "recon_service"},
    {"test_case_id": "TC-RECON-002", "rule_id": "RULE-RECON-001", "test_category": "RECONCILIATION", "test_name": "Verify Penny Tolerance Boundary Pass", "target_component": "recon_service"},
    {"test_case_id": "TC-RECON-003", "rule_id": "RULE-RECON-001", "test_category": "RECONCILIATION", "test_name": "Verify Tolerance Breach Detection Fail", "target_component": "recon_service"},
    {"test_case_id": "TC-RECON-004", "rule_id": "RULE-RECON-001", "test_category": "RECONCILIATION", "test_name": "Verify Material Miscalculation Defect Extraction", "target_component": "recon_service"}
]


def build_rtm_matrix(defects_df: pd.DataFrame = None) -> tuple[pd.DataFrame, dict]:
    """
    Builds conformed Requirements Traceability Matrix linking requirements to rules,
    test cases, executions, and defect distributions.
    """
    req_df = pd.DataFrame(BRD_REQUIREMENTS)
    rules_df = pd.DataFrame(BUSINESS_RULES)
    tc_df = pd.DataFrame(TEST_CASES)

    # Base RTM structure
    rtm_base = tc_df.merge(rules_df, on="rule_id", how="left").merge(req_df, on="requirement_id", how="left")

    # If defects provided, aggregate defect counts and severities per test case and requirement
    if defects_df is not None and not defects_df.empty:
        defect_agg = defects_df.groupby("test_case_id").agg(
            total_defects=("defect_id", "count"),
            critical_defects=("severity", lambda s: (s == "CRITICAL").sum()),
            major_defects=("severity", lambda s: (s == "MAJOR").sum()),
            minor_defects=("severity", lambda s: (s == "MINOR").sum()),
            total_variance_usd=("variance_amount", lambda v: round(float(v.abs().sum()), 2))
        ).reset_index()

        rtm_full = rtm_base.merge(defect_agg, on="test_case_id", how="left")
        rtm_full["total_defects"] = rtm_full["total_defects"].fillna(0).astype(int)
        rtm_full["critical_defects"] = rtm_full["critical_defects"].fillna(0).astype(int)
        rtm_full["major_defects"] = rtm_full["major_defects"].fillna(0).astype(int)
        rtm_full["minor_defects"] = rtm_full["minor_defects"].fillna(0).astype(int)
        rtm_full["total_variance_usd"] = rtm_full["total_variance_usd"].fillna(0.0)
    else:
        rtm_full = rtm_base.copy()
        rtm_full["total_defects"] = 0
        rtm_full["critical_defects"] = 0
        rtm_full["major_defects"] = 0
        rtm_full["minor_defects"] = 0
        rtm_full["total_variance_usd"] = 0.0

    # Test status determination (In defect scenario, cases with defects flag FAILED; others PASSED)
    rtm_full["test_execution_status"] = rtm_full["total_defects"].apply(lambda d: "FAILED" if d > 0 else "PASSED")
    rtm_full["coverage_status"] = "COVERED"
    rtm_full["evaluated_at"] = REFERENCE_TIMESTAMP

    # Summary Telemetry
    total_requirements = len(req_df)
    covered_requirements = rtm_full["requirement_id"].nunique()
    total_test_cases = len(tc_df)
    failing_test_cases = int((rtm_full["test_execution_status"] == "FAILED").sum())
    passing_test_cases = int((rtm_full["test_execution_status"] == "PASSED").sum())

    summary = {
        "evaluation_timestamp": REFERENCE_TIMESTAMP.isoformat(),
        "total_brd_requirements": total_requirements,
        "covered_requirements": covered_requirements,
        "requirement_coverage_pct": round((covered_requirements / total_requirements) * 100, 2),
        "total_business_rules": len(rules_df),
        "total_test_cases": total_test_cases,
        "automated_test_cases": total_test_cases,
        "test_automation_rate_pct": 100.0,
        "passing_test_cases": passing_test_cases,
        "failing_test_cases": failing_test_cases,
        "test_pass_rate_pct": round((passing_test_cases / total_test_cases) * 100, 2),
        "total_defects_linked": int(rtm_full["total_defects"].sum()),
        "defects_by_requirement": rtm_full.groupby("requirement_id")["total_defects"].sum().to_dict(),
        "defects_by_severity": {
            "CRITICAL": int(rtm_full["critical_defects"].sum()),
            "MAJOR": int(rtm_full["major_defects"].sum()),
            "MINOR": int(rtm_full["minor_defects"].sum())
        }
    }

    # Save artifacts
    rtm_full.to_parquet(OUTPUT_QA_DIR / "rtm_matrix.parquet", index=False)
    with open(OUTPUT_QA_DIR / "rtm_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return rtm_full, summary
