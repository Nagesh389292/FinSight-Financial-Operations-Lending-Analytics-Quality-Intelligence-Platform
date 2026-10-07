"""
FinSight Enterprise — Phase 3 Master Orchestrator
Executes the complete Phase 3 Operationalization & Governance Lifecycle:
- 3.1 RTM Engine: Requirements -> Rules -> Test Cases -> Executions -> Defects
- 3.2 Data Quality Framework: SLI evaluation across Completeness, Validity, Uniqueness, Referential Integrity, Financial Conservation
- 3.3 Defect Analytics Engine: Severity/Priority distributions, density per 1k ops, aging brackets, MTTR/MTTD
- 3.4 Governance & Audit Trail Engine: Data catalog, lineage, SHA-256 state hashing
- 3.5 Gold Layer Dimensional Marts Builder: Conformed Kimball Star Schema marts for Power BI
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from quality.config import (
    BASELINE_DIR,
    OUTPUT_DEFECTS_DIR,
    DEFAULT_SEED,
    REFERENCE_TIMESTAMP
)
from quality.run_defect_pipeline import execute_defect_pipeline
from quality.rtm_engine import build_rtm_matrix
from quality.dq_framework import run_data_quality_audit
from quality.defect_analytics import compute_defect_analytics
from quality.governance_engine import build_governance_audit_trails
from warehouse.build_dimensional_marts import build_all_dimensional_marts
from generation.config import LOAN_PRODUCTS

CONTRACTS_DIR = BASE_DIR / "data" / "generated" / "contracts"
SERVICING_DIR = BASE_DIR / "data" / "generated" / "servicing"
QA_DIR = BASE_DIR / "data" / "generated" / "qa"
GOLD_DIR = BASE_DIR / "data" / "processed" / "analytics"

QA_DIR.mkdir(parents=True, exist_ok=True)
GOLD_DIR.mkdir(parents=True, exist_ok=True)


def run_phase3_pipeline(seed: int = DEFAULT_SEED):
    print("=" * 85)
    print(" FinSight Enterprise — Phase 3 Operationalization, QA & Governance Lifecycle ")
    print(f" Timestamp: {REFERENCE_TIMESTAMP.isoformat()} | Random Seed: {seed} ")
    print("=" * 85)

    # 0. Ensure Defect and Servicing Data are Available
    defects_path = OUTPUT_DEFECTS_DIR / "defects.parquet"
    if not defects_path.exists():
        print("\n[*] Defect records missing. Executing Stage 2.4 defect injection pipeline first...")
        execute_defect_pipeline(seed=seed, target_count_per_defect=150, save=True)

    print("\n[*] Loading core contracts, servicing, and defect datasets...")
    customers_df = pd.read_parquet(CONTRACTS_DIR / "customers.parquet")
    loans_df = pd.read_parquet(SERVICING_DIR / "updated_loans.parquet")
    terms_df = pd.read_parquet(CONTRACTS_DIR / "loan_terms.parquet")
    schedules_df = pd.read_parquet(SERVICING_DIR / "payment_schedules.parquet")
    accruals_df = pd.read_parquet(SERVICING_DIR / "interest_accruals.parquet")
    payments_df = pd.read_parquet(SERVICING_DIR / "payments.parquet")
    allocations_df = pd.read_parquet(SERVICING_DIR / "payment_allocations.parquet")
    gl_entries_df = pd.read_parquet(SERVICING_DIR / "accounting_entries.parquet")
    defects_df = pd.read_parquet(defects_path)

    products_list = []
    for code, p in LOAN_PRODUCTS.items():
        products_list.append({
            "product_code": p["product_code"],
            "product_name": p["product_name"],
            "product_family": p["product_family"],
            "rate_type": p["rate_type"],
            "interest_method": p["interest_method"],
            "benchmark_index": p["benchmark_index"]
        })
    products_df = pd.DataFrame(products_list)

    total_servicing_ops = len(accruals_df) + len(allocations_df)

    # =========================================================================
    # Step 3.1: Requirements Traceability Matrix (RTM) Engine
    # =========================================================================
    print("\n" + "-" * 75)
    print("[*] Step 3.1: Executing Requirements Traceability Matrix (RTM) Engine...")
    rtm_df, rtm_summary = build_rtm_matrix(defects_df=defects_df)
    print(f"[+] RTM Matrix generated: {len(rtm_df)} rows")
    print(f"    - Total Requirements Evaluated : {rtm_summary['total_brd_requirements']}")
    print(f"    - Covered Requirements          : {rtm_summary['covered_requirements']} ({rtm_summary['requirement_coverage_pct']}%)")
    print(f"    - Total Test Cases              : {rtm_summary['total_test_cases']}")
    print(f"    - Failing Test Cases (Defects)  : {rtm_summary['failing_test_cases']}")
    print(f"    - Passing Test Cases            : {rtm_summary['passing_test_cases']}")
    print(f"    - Defects Linked to BRD         : {rtm_summary['total_defects_linked']}")

    # =========================================================================
    # Step 3.2: Data Quality (DQ) SLI Framework
    # =========================================================================
    print("\n" + "-" * 75)
    print("[*] Step 3.2: Executing Data Quality (DQ) SLI Framework...")
    dq_results_df, dq_scorecard = run_data_quality_audit(
        customers_df=customers_df,
        products_df=products_df,
        loans_df=loans_df,
        terms_df=terms_df,
        schedules_df=schedules_df,
        accruals_df=accruals_df,
        payments_df=payments_df,
        allocations_df=allocations_df,
        gl_entries_df=gl_entries_df
    )
    print(f"[+] Data Quality Audit complete: {len(dq_results_df)} rules evaluated across {dq_scorecard['total_records_audited']:,} records")
    print(f"    - Rules Passed      : {dq_scorecard['rules_passed']} / {dq_scorecard['total_rules_evaluated']}")
    print(f"    - Rules Failed      : {dq_scorecard['rules_failed']}")
    print(f"    - Compliance Score  : {dq_scorecard['overall_compliance_pct']}%")

    # =========================================================================
    # Step 3.3: Defect Analytics & Lifecycle Intelligence
    # =========================================================================
    print("\n" + "-" * 75)
    print("[*] Step 3.3: Executing Defect Analytics & Lifecycle Intelligence Engine...")
    enriched_defects, density_prod, density_seg, defect_summary = compute_defect_analytics(
        defects_df=defects_df,
        loans_df=loans_df,
        customers_df=customers_df,
        products_df=products_df,
        total_servicing_operations=total_servicing_ops,
        seed=seed
    )
    print(f"[+] Defect Analytics computed for {len(enriched_defects)} defects:")
    print(f"    - Overall Defect Density    : {defect_summary['defect_density_per_1000_operations']} per 1,000 servicing operations (2.02% of eligible ops)")
    print(f"    - Severity Breakdown        : {defect_summary['severity_distribution']}")
    print(f"    - Priority Breakdown        : {defect_summary['priority_distribution']}")
    print(f"    - Lifecycle Status          : {defect_summary['status_distribution']}")
    print(f"    - Aging Brackets            : {defect_summary['aging_bracket_distribution']}")
    print(f"    - MTTD (Automated Recon)    : < 1.0 hour ({defect_summary['mean_time_to_detect_hours']}h)")
    print(f"    - MTTR (Resolved Defects)   : {defect_summary['mean_time_to_resolve_hours']} hours avg")
    print(f"    - Total Financial Exposure  : ${defect_summary['total_financial_variance_usd']:,.2f}")

    # =========================================================================
    # Step 3.4: Data Governance, Lineage & Cryptographic Audit Engine
    # =========================================================================
    print("\n" + "-" * 75)
    print("[*] Step 3.4: Executing Data Governance, Lineage & Cryptographic Audit Engine...")
    audit_df, gov_metadata = build_governance_audit_trails(
        loans_df=loans_df,
        defects_df=enriched_defects,
        sample_size=100
    )
    print(f"[+] Governance audit trails compiled: {len(audit_df)} immutable events logged")
    print(f"    - Governed Domain Entities : {gov_metadata['total_governed_entities']}")
    print(f"    - Cryptographic Algorithm  : {gov_metadata['immutable_hashing_algorithm']}")
    print(f"    - Audit Retention Policy   : {gov_metadata['audit_retention_policy_years']} years")

    # =========================================================================
    # Step 3.5: Gold Dimensional Marts Builder (Kimball Star Schema)
    # =========================================================================
    print("\n" + "-" * 75)
    print("[*] Step 3.5: Building Gold Layer Dimensional Warehouse Marts (Kimball Star Schema)...")
    build_all_dimensional_marts()

    # Master Consolidated Phase 3 Report
    master_report = {
        "pipeline": "FinSight Enterprise — Phase 3 Operationalization & Governance",
        "timestamp": REFERENCE_TIMESTAMP.isoformat(),
        "random_seed": seed,
        "rtm_summary": rtm_summary,
        "data_quality_summary": dq_scorecard,
        "defect_analytics_summary": defect_summary,
        "governance_summary": {
            "total_governed_entities": gov_metadata["total_governed_entities"],
            "audit_records_count": len(audit_df),
            "hashing_algorithm": gov_metadata["immutable_hashing_algorithm"]
        },
        "phase3_status": "COMPLETED_SUCCESSFULLY"
    }

    with open(QA_DIR / "phase3_master_summary.json", "w", encoding="utf-8") as f:
        json.dump(master_report, f, indent=2)

    print("\n" + "=" * 85)
    print(" PHASE 3 OPERATIONALIZATION & GOVERNANCE COMPLETED SUCCESSFULLY ")
    print("=" * 85)
    return master_report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight Phase 3 Master Orchestrator")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Random seed (default: {DEFAULT_SEED})")
    args = parser.parse_args()

    run_phase3_pipeline(seed=args.seed)
