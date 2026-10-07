"""
FinSight Enterprise — Data Quality (DQ) SLI Framework (Phase 3.2)
Executes comprehensive automated data quality audits across 5 enterprise categories:
1. COMPLETENESS (Null/missing value auditing)
2. VALIDITY (Schema format, range, and enumeration conformance)
3. UNIQUENESS (Primary key duplicate detection)
4. REFERENTIAL_INTEGRITY (Foreign key orphan checks)
5. FINANCIAL_CONSERVATION (Double-entry balance and waterfall conservation invariants)

Outputs audit results matching governance.data_quality_results DDL.
"""

import json
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np

from quality.config import BASE_DIR, REFERENCE_TIMESTAMP

OUTPUT_QA_DIR = BASE_DIR / "data" / "generated" / "qa"
OUTPUT_QA_DIR.mkdir(parents=True, exist_ok=True)


def run_data_quality_audit(
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    terms_df: pd.DataFrame,
    schedules_df: pd.DataFrame,
    accruals_df: pd.DataFrame,
    payments_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    gl_entries_df: pd.DataFrame = None
) -> tuple[pd.DataFrame, dict]:
    """
    Executes automated data quality rules across all core and finance entities.
    Returns:
    - dq_results_df: governance.data_quality_results records
    - scorecard: Summary SLI metrics
    """
    results = []
    rule_counter = 1

    def record_check(name, category, schema, table, col, total, failing, sample=None):
        nonlocal rule_counter
        pass_rate = round(((total - failing) / total) * 100, 2) if total > 0 else 100.0
        status = "PASSED" if failing == 0 else ("WARNING" if pass_rate >= 98.0 else "FAILED")

        results.append({
            "dq_result_id": rule_counter,
            "check_name": name,
            "check_category": category,
            "target_schema": schema,
            "target_table": table,
            "target_column": col,
            "status": status,
            "records_evaluated": int(total),
            "failing_records_count": int(failing),
            "pass_rate_pct": float(pass_rate),
            "error_sample": json.dumps(sample or {}),
            "evaluated_at": REFERENCE_TIMESTAMP
        })
        rule_counter += 1

    # =========================================================================
    # 1. COMPLETENESS (Non-null validations)
    # =========================================================================
    # Customers
    total_cust = len(customers_df)
    cust_nulls = customers_df[["customer_id", "legal_name", "credit_score", "annual_income"]].isna().sum().sum()
    record_check("DQ_COMPL_CUST_MANDATORY", "COMPLETENESS", "core", "customers", "*", total_cust, cust_nulls)

    # Loans
    total_loans = len(loans_df)
    loans_nulls = loans_df[["loan_id", "customer_id", "product_code", "principal_original", "interest_rate_annual", "start_date", "maturity_date"]].isna().sum().sum()
    record_check("DQ_COMPL_LOAN_MANDATORY", "COMPLETENESS", "core", "loans", "*", total_loans, loans_nulls)

    # Payments & Allocations
    total_pmt = len(payments_df)
    pmt_nulls = payments_df[["payment_id", "loan_id", "payment_date", "payment_amount"]].isna().sum().sum()
    record_check("DQ_COMPL_PMT_MANDATORY", "COMPLETENESS", "finance", "payments", "*", total_pmt, pmt_nulls)

    total_alloc = len(allocations_df)
    alloc_nulls = allocations_df[["allocation_id", "payment_id", "loan_id", "principal_amount", "interest_amount", "total_allocated"]].isna().sum().sum()
    record_check("DQ_COMPL_ALLOC_MANDATORY", "COMPLETENESS", "finance", "payment_allocations", "*", total_alloc, alloc_nulls)

    # =========================================================================
    # 2. UNIQUENESS (Primary key duplicate audits)
    # =========================================================================
    record_check("DQ_UNIQ_CUSTOMER_ID", "UNIQUENESS", "core", "customers", "customer_id", total_cust, customers_df["customer_id"].duplicated().sum())
    record_check("DQ_UNIQ_LOAN_ID", "UNIQUENESS", "core", "loans", "loan_id", total_loans, loans_df["loan_id"].duplicated().sum())
    record_check("DQ_UNIQ_PRODUCT_CODE", "UNIQUENESS", "core", "loan_products", "product_code", len(products_df), products_df["product_code"].duplicated().sum())
    record_check("DQ_UNIQ_PAYMENT_ID", "UNIQUENESS", "finance", "payments", "payment_id", total_pmt, payments_df["payment_id"].duplicated().sum())
    record_check("DQ_UNIQ_ACCRUAL_ID", "UNIQUENESS", "finance", "interest_accruals", "accrual_id", len(accruals_df), accruals_df["accrual_id"].duplicated().sum())

    # =========================================================================
    # 3. VALIDITY & RANGE BOUNDS
    # =========================================================================
    # Credit score bounds [300, 850]
    invalid_credit = ((customers_df["credit_score"] < 300) | (customers_df["credit_score"] > 850)).sum()
    record_check("DQ_VAL_CREDIT_SCORE_RANGE", "VALIDITY", "core", "customers", "credit_score", total_cust, invalid_credit)

    # Principal positive bounds
    invalid_principal = (loans_df["principal_original"] <= 0).sum()
    record_check("DQ_VAL_POSITIVE_PRINCIPAL", "VALIDITY", "core", "loans", "principal_original", total_loans, invalid_principal)

    # Interest rate realistic bounds [0.5%, 35%]
    invalid_rates = ((loans_df["interest_rate_annual"] < 0.005) | (loans_df["interest_rate_annual"] > 0.35)).sum()
    record_check("DQ_VAL_RATE_BOUNDS", "VALIDITY", "core", "loans", "interest_rate_annual", total_loans, invalid_rates)

    # Maturity date > start date
    invalid_dates = (pd.to_datetime(loans_df["maturity_date"]) <= pd.to_datetime(loans_df["start_date"])).sum()
    record_check("DQ_VAL_MATURITY_CHRONOLOGY", "VALIDITY", "core", "loans", "maturity_date", total_loans, invalid_dates)

    # Day-count convention enumeration
    allowed_conventions = {"ACTUAL/360", "ACTUAL/365", "30/360"}
    invalid_conv = (~terms_df["interest_method"].isin(allowed_conventions)).sum()
    record_check("DQ_VAL_DAYCOUNT_ENUM", "VALIDITY", "core", "loan_terms", "interest_method", len(terms_df), invalid_conv)

    # DPD non-negative
    invalid_dpd = (loans_df["days_past_due"] < 0).sum()
    record_check("DQ_VAL_DPD_NON_NEGATIVE", "VALIDITY", "core", "loans", "days_past_due", total_loans, invalid_dpd)

    # =========================================================================
    # 4. REFERENTIAL INTEGRITY (Foreign key orphan checks)
    # =========================================================================
    # Loan -> Customer
    orphan_cust = (~loans_df["customer_id"].isin(customers_df["customer_id"])).sum()
    record_check("DQ_RI_LOAN_CUSTOMER_FK", "REFERENTIAL_INTEGRITY", "core", "loans", "customer_id", total_loans, orphan_cust)

    # Loan -> Product
    orphan_prod = (~loans_df["product_code"].isin(products_df["product_code"])).sum()
    record_check("DQ_RI_LOAN_PRODUCT_FK", "REFERENTIAL_INTEGRITY", "core", "loans", "product_code", total_loans, orphan_prod)

    # Terms -> Loan
    orphan_terms = (~terms_df["loan_id"].isin(loans_df["loan_id"])).sum()
    record_check("DQ_RI_TERM_LOAN_FK", "REFERENTIAL_INTEGRITY", "core", "loan_terms", "loan_id", len(terms_df), orphan_terms)

    # Payments -> Loan
    orphan_pmt_loan = (~payments_df["loan_id"].isin(loans_df["loan_id"])).sum()
    record_check("DQ_RI_PAYMENT_LOAN_FK", "REFERENTIAL_INTEGRITY", "finance", "payments", "loan_id", total_pmt, orphan_pmt_loan)

    # Allocations -> Payment
    orphan_alloc_pmt = (~allocations_df["payment_id"].isin(payments_df["payment_id"])).sum()
    record_check("DQ_RI_ALLOC_PAYMENT_FK", "REFERENTIAL_INTEGRITY", "finance", "payment_allocations", "payment_id", total_alloc, orphan_alloc_pmt)

    # =========================================================================
    # 5. FINANCIAL CONSERVATION (Accounting & Servicing Invariants)
    # =========================================================================
    # Waterfall allocation sum conservation: Allocated == Fees + Interest + Principal + Prepayment
    alloc_sum = (
        allocations_df["fees_amount"] +
        allocations_df["interest_amount"] +
        allocations_df["principal_amount"] +
        allocations_df["prepayment_amount"]
    ).round(2)
    alloc_diff = (alloc_sum != allocations_df["total_allocated"].round(2)).sum()
    record_check("DQ_FIN_WATERFALL_CONSERVATION", "VALIDITY", "finance", "payment_allocations", "total_allocated", total_alloc, alloc_diff)

    # GL Balance Check if GL entries provided: Sum(Debit) == Sum(Credit)
    if gl_entries_df is not None and not gl_entries_df.empty:
        total_gl = len(gl_entries_df)
        unbalanced_entries = (gl_entries_df["total_debit"].round(2) != gl_entries_df["total_credit"].round(2)).sum()
        record_check("DQ_FIN_GL_DEBIT_CREDIT_BALANCE", "VALIDITY", "finance", "accounting_entries", "total_debit", total_gl, unbalanced_entries)

    dq_df = pd.DataFrame(results)

    # Scorecard Aggregation
    total_rules = len(dq_df)
    passed_rules = int((dq_df["status"] == "PASSED").sum())
    failed_rules = int((dq_df["status"] == "FAILED").sum())
    total_records_audited = int(dq_df["records_evaluated"].sum())

    cat_status = {}
    for (cat, st), count in dq_df.groupby(["check_category", "status"]).size().items():
        if cat not in cat_status:
            cat_status[cat] = {}
        cat_status[cat][st] = int(count)

    scorecard = {
        "audit_timestamp": REFERENCE_TIMESTAMP.isoformat(),
        "total_rules_evaluated": total_rules,
        "rules_passed": passed_rules,
        "rules_failed": failed_rules,
        "overall_compliance_pct": round((passed_rules / total_rules) * 100, 2),
        "total_records_audited": total_records_audited,
        "rules_by_category": cat_status,
        "status": "PASSED" if failed_rules == 0 else "FAILED"
    }

    # Save DQ outputs
    dq_df.to_parquet(OUTPUT_QA_DIR / "data_quality_results.parquet", index=False)
    with open(OUTPUT_QA_DIR / "dq_scorecard.json", "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    return dq_df, scorecard
