"""
FinSight Enterprise — Data Governance, Lineage & Cryptographic Audit Engine (Phase 3.4)
Establishes the governance chain: Data -> Owner -> Definition -> Lineage -> Quality -> Audit.
Implements SHA-256 state hashing for immutable audit trails matching governance.audit_log DDL.
Outputs governance catalog and audit trails to data/generated/qa/.
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

from quality.config import BASE_DIR, REFERENCE_TIMESTAMP

OUTPUT_QA_DIR = BASE_DIR / "data" / "generated" / "qa"
OUTPUT_QA_DIR.mkdir(parents=True, exist_ok=True)

# 1. Authoritative Enterprise Data Lineage & Governance Catalog
DATA_LINEAGE_CATALOG = [
    {
        "table_name": "raw_fred_macro",
        "schema": "raw",
        "domain": "Macroeconomics",
        "data_owner": "Treasury & Market Risk",
        "classification": "PUBLIC",
        "source_system": "Federal Reserve Bank of St. Louis (FRED API)",
        "upstream_sources": ["FRED: SOFR, FEDFUNDS, DGS10, CPIAUCNS, UNRATE, DPRIME"],
        "downstream_consumers": ["core.loan_terms", "analytics.fact_financial", "forecasting.models"],
        "update_frequency": "Monthly / Daily",
        "quality_sla": "100% Completeness, 0 Imputation Gaps"
    },
    {
        "table_name": "core.customers",
        "schema": "core",
        "domain": "Lending Core",
        "data_owner": "Credit Underwriting & KYC",
        "classification": "CONFIDENTIAL (Synthetic PII)",
        "source_system": "Customer Origination Simulator",
        "upstream_sources": ["generation.customer_generator"],
        "downstream_consumers": ["core.loans", "analytics.dim_customer"],
        "update_frequency": "Daily Batch",
        "quality_sla": "Zero Duplicate Customer IDs, FICO between 300-850"
    },
    {
        "table_name": "core.loans",
        "schema": "core",
        "domain": "Lending Core",
        "data_owner": "Servicing Operations",
        "classification": "CONFIDENTIAL",
        "source_system": "Loan Origination Simulator",
        "upstream_sources": ["core.customers", "core.loan_products", "raw_fred_macro"],
        "downstream_consumers": ["finance.payments", "analytics.dim_loan", "analytics.fact_loan_performance"],
        "update_frequency": "Real-time / Batch",
        "quality_sla": "100% Referential Integrity, Principal > 0"
    },
    {
        "table_name": "finance.payments",
        "schema": "finance",
        "domain": "Financial Servicing",
        "data_owner": "Cash & Treasury Management",
        "classification": "RESTRICTED",
        "source_system": "Payment Servicing Engine",
        "upstream_sources": ["servicing.payment_execution"],
        "downstream_consumers": ["finance.payment_allocations", "finance.accounting_entries", "analytics.fact_payment"],
        "update_frequency": "Daily Servicing Cycle",
        "quality_sla": "100% Positive Payment Amounts, Zero Orphans"
    },
    {
        "table_name": "finance.payment_allocations",
        "schema": "finance",
        "domain": "Financial Accounting",
        "data_owner": "Financial Controller",
        "classification": "RESTRICTED",
        "source_system": "Waterfall Allocation Engine",
        "upstream_sources": ["finance.payments", "core.loan_terms"],
        "downstream_consumers": ["finance.accounting_entries", "analytics.fact_payment"],
        "update_frequency": "Daily Allocation Batch",
        "quality_sla": "Exact Conservation: Allocated == Fees + Interest + Principal + Prepayment"
    },
    {
        "table_name": "finance.accounting_entries",
        "schema": "finance",
        "domain": "General Ledger",
        "data_owner": "Accounting Operations",
        "classification": "RESTRICTED",
        "source_system": "General Ledger Double-Entry Engine",
        "upstream_sources": ["finance.interest_accruals", "finance.payment_allocations"],
        "downstream_consumers": ["analytics.fact_financial", "powerbi.financial_reporting"],
        "update_frequency": "Daily GL Close",
        "quality_sla": "Zero Unbalanced Entries: Sum(Debit) == Sum(Credit)"
    },
    {
        "table_name": "qa.defects",
        "schema": "qa",
        "domain": "Quality Engineering",
        "data_owner": "Head of Quality Engineering",
        "classification": "INTERNAL",
        "source_system": "Automated QA Reconciliation Engine",
        "upstream_sources": ["quality.qa_engine", "api.app.services.math_truth"],
        "downstream_consumers": ["analytics.fact_defect", "powerbi.qa_console"],
        "update_frequency": "Continuous CI/CD",
        "quality_sla": "100% RTM Traceability, MTTR < 48 Hours for Criticals"
    }
]


def generate_sha256_hash(payload_str: str) -> str:
    """Computes SHA-256 hash of a stringified entity payload."""
    return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()


def build_governance_audit_trails(
    loans_df: pd.DataFrame,
    defects_df: pd.DataFrame,
    sample_size: int = 50
) -> tuple[pd.DataFrame, dict]:
    """
    Builds cryptographic immutable audit log events matching governance.audit_log schema.
    Returns:
    - audit_log_df: governance.audit_log records
    - governance_metadata: Data dictionary and governance metadata summary
    """
    audit_records = []
    audit_counter = 1

    # 1. Audit Log: Loan Origination Events
    for _, loan in loans_df.head(sample_size).iterrows():
        loan_id = loan["loan_id"]
        pre_state = "NULL" # Origination has no prior state
        post_state = json.dumps({
            "loan_id": loan_id,
            "principal": float(loan["principal_original"]),
            "rate": float(loan["interest_rate_annual"]),
            "status": "ACTIVE"
        }, sort_keys=True)

        audit_records.append({
            "audit_id": audit_counter,
            "user_id": "USR-CREDIT-OFFICER-01",
            "role_id": "ROLE_CREDIT_ANALYST",
            "action_type": "LOAN_ORIGINATED",
            "entity_type": "LOAN",
            "entity_id": loan_id,
            "pre_state_hash": generate_sha256_hash(pre_state),
            "post_state_hash": generate_sha256_hash(post_state),
            "change_payload": post_state,
            "client_ip": "10.14.20.105",
            "timestamp_utc": REFERENCE_TIMESTAMP
        })
        audit_counter += 1

    # 2. Audit Log: Defect Triage & Reconciliation Override Events
    for _, defect in defects_df.head(sample_size).iterrows():
        defect_id = defect["defect_id"]
        pre_state = json.dumps({"defect_id": defect_id, "status": "NEW"}, sort_keys=True)
        post_state = json.dumps({
            "defect_id": defect_id,
            "status": defect["status"],
            "severity": defect["severity"],
            "variance": float(defect["variance_amount"])
        }, sort_keys=True)

        audit_records.append({
            "audit_id": audit_counter,
            "user_id": "USR-QA-LEAD-01",
            "role_id": "ROLE_QA_ANALYST",
            "action_type": "DEFECT_TRIAGED",
            "entity_type": "DEFECT",
            "entity_id": defect_id,
            "pre_state_hash": generate_sha256_hash(pre_state),
            "post_state_hash": generate_sha256_hash(post_state),
            "change_payload": post_state,
            "client_ip": "10.14.20.188",
            "timestamp_utc": REFERENCE_TIMESTAMP
        })
        audit_counter += 1

    audit_df = pd.DataFrame(audit_records)

    governance_metadata = {
        "catalog_timestamp": REFERENCE_TIMESTAMP.isoformat(),
        "total_governed_entities": len(DATA_LINEAGE_CATALOG),
        "data_lineage_catalog": DATA_LINEAGE_CATALOG,
        "audit_log_records_count": len(audit_df),
        "immutable_hashing_algorithm": "SHA-256",
        "audit_retention_policy_years": 7
    }

    # Save artifacts
    audit_df.to_parquet(OUTPUT_QA_DIR / "audit_log.parquet", index=False)
    with open(OUTPUT_QA_DIR / "data_governance_catalog.json", "w", encoding="utf-8") as f:
        json.dump(governance_metadata, f, indent=2)

    return audit_df, governance_metadata
