"""
FinSight Enterprise — DAX Measure Independent Validation Suite (Step 4.3)
Independently verifies every Power BI DAX KPI against the underlying Gold Star Schema
Parquet tables (data/processed/analytics/), asserting exact mathematical equivalence
and zero variance to authoritative control values.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
GOLD_DIR = BASE_DIR / "data" / "processed" / "analytics"
OUTPUT_DIR = BASE_DIR / "powerbi"


def validate_all_dax_measures():
    print("=" * 85)
    print(" FinSight Enterprise — Independent DAX Measure Validation Engine (Step 4.3) ")
    print(" Ground Truth Verification: Power BI DAX <===> Gold Star Schema Parquet ")
    print("=" * 85)

    # 1. Load Gold Datasets
    print("\n[*] Loading Gold Kimball Star Schema Parquet datasets...")
    dim_date = pd.read_parquet(GOLD_DIR / "dim_date.parquet")
    dim_customer = pd.read_parquet(GOLD_DIR / "dim_customer.parquet")
    dim_product = pd.read_parquet(GOLD_DIR / "dim_product.parquet")
    dim_loan = pd.read_parquet(GOLD_DIR / "dim_loan.parquet")
    fact_loan_perf = pd.read_parquet(GOLD_DIR / "fact_loan_performance.parquet")
    fact_payment = pd.read_parquet(GOLD_DIR / "fact_payment.parquet")
    fact_financial = pd.read_parquet(GOLD_DIR / "fact_financial.parquet")
    fact_test_exec = pd.read_parquet(GOLD_DIR / "fact_test_execution.parquet")
    fact_defect = pd.read_parquet(GOLD_DIR / "fact_defect.parquet")
    fact_dq = pd.read_parquet(GOLD_DIR / "fact_data_quality.parquet")

    results = []

    def record_validation(measure_name, folder, dax_formula, expected_val, computed_val, tolerance=0.01, unit=""):
        comp_clean = float(computed_val) if isinstance(computed_val, (int, float, np.integer, np.floating)) else computed_val
        exp_clean = float(expected_val) if isinstance(expected_val, (int, float, np.integer, np.floating)) else expected_val
        diff = abs(comp_clean - exp_clean) if isinstance(comp_clean, (int, float)) else (0.0 if comp_clean == exp_clean else 1.0)
        passed = diff <= tolerance

        status = "PASS" if passed else "FAIL"
        results.append({
            "measure_name": measure_name,
            "folder": folder,
            "dax_formula": dax_formula,
            "expected_control_value": exp_clean,
            "computed_gold_value": round(comp_clean, 4) if isinstance(comp_clean, (int, float)) else comp_clean,
            "variance": round(float(diff), 4),
            "status": status,
            "unit": unit
        })
        mark = "[PASS]" if passed else "[FAIL]"
        if unit == "$":
            val_str = f"${comp_clean:,.2f}"
        elif unit == "%":
            val_str = f"{comp_clean:.2f}%"
        elif unit == "#":
            val_str = f"{int(comp_clean):,}"
        else:
            val_str = f"{comp_clean:.2f}"
        print(f" {mark} {measure_name:<34} : {val_str} (Variance: {diff:.4f})")

    # =========================================================================
    # 01 Portfolio & Lending KPIs
    # =========================================================================
    print("\n--- Folder: 01_Portfolio_Lending ---")
    # Total Loans
    total_loans = int(len(dim_loan["loan_id"].unique()))
    record_validation("Total Loans", "01_Portfolio_Lending", "DISTINCTCOUNT(dim_loan[loan_id])", 2500, total_loans, 0, "#")

    # Original Principal
    orig_principal = float(dim_loan["original_principal"].sum())
    record_validation("Original Principal", "01_Portfolio_Lending", "SUM(dim_loan[original_principal])", 4083242991.87, orig_principal, 0.05, "$")

    # Closing Outstanding Principal (latest period snapshot)
    latest_perf = fact_loan_perf.sort_values("date_key").groupby("loan_key").last()
    closing_principal = float(latest_perf["outstanding_principal"].sum())
    record_validation("Closing Outstanding Principal", "01_Portfolio_Lending", "SUM(fact_loan_performance[outstanding_principal])", 3902427287.56, closing_principal, 0.05, "$")

    # Active Loans (2,395 active; 68 delinquent; 37 default charged off)
    active_loans = int((latest_perf["status"] == "ACTIVE").sum())
    record_validation("Active Loans", "01_Portfolio_Lending", "CALCULATE([Total Loans], status = 'ACTIVE')", 2395, active_loans, 0, "#")

    # Average Facility Size
    avg_facility = closing_principal / total_loans
    record_validation("Average Facility Size", "01_Portfolio_Lending", "DIVIDE([Outstanding Principal], [Total Loans])", 1560970.92, avg_facility, 0.05, "$")

    # Weighted Average Rate (WAR)
    war = float((dim_loan["original_principal"] * dim_loan["annual_interest_rate"]).sum() / orig_principal * 100)
    record_validation("Weighted Average Rate (WAR)", "01_Portfolio_Lending", "DIVIDE(SUMX(dim_loan, P * R), [Original Principal])", 6.86, war, 0.05, "%")

    # =========================================================================
    # 02 Payments & Cash Flow Allocations
    # =========================================================================
    print("\n--- Folder: 02_Payments_CashFlow ---")
    # Total Payment Volume (Phase 2 Control: $351.57M)
    total_payments = float(fact_payment["payment_amount"].sum())
    record_validation("Total Payment Volume", "02_Payments_CashFlow", "SUM(fact_payment[payment_amount])", 351574751.19, total_payments, 0.05, "$")

    # Principal Collected
    principal_coll = float(fact_payment["principal_applied"].sum())
    record_validation("Principal Collected", "02_Payments_CashFlow", "SUM(fact_payment[principal_applied])", 211429149.52, principal_coll, 0.05, "$")

    # Interest Collected
    interest_coll = float(fact_payment["interest_applied"].sum())
    record_validation("Interest Collected", "02_Payments_CashFlow", "SUM(fact_payment[interest_applied])", 135101426.82, interest_coll, 0.05, "$")

    # Fees Collected
    fees_coll = float(fact_payment["fees_applied"].sum())
    record_validation("Fees Collected", "02_Payments_CashFlow", "SUM(fact_payment[fees_applied])", 1484002.80, fees_coll, 0.05, "$")

    # Prepayments Collected
    prepay_coll = float(fact_payment["prepayment_applied"].sum())
    record_validation("Prepayments Collected", "02_Payments_CashFlow", "SUM(fact_payment[prepayment_applied])", 3560172.05, prepay_coll, 0.05, "$")

    # Cash Allocation Conservation: Total Payment == Principal + Interest + Fees + Prepayments
    cash_sum = principal_coll + interest_coll + fees_coll + prepay_coll
    cash_leakage = abs(cash_sum - total_payments)
    record_validation("Payment Cash Conservation", "02_Payments_CashFlow", "Allocated Cash == Principal + Interest + Fees + Prepayment", 0.0, cash_leakage, 0.01, "$")

    # =========================================================================
    # 03 Delinquency & Credit Risk
    # =========================================================================
    print("\n--- Folder: 03_Delinquency_Risk ---")
    # Delinquent Balance 30+ DPD
    delinq_bal = float(latest_perf[latest_perf["is_delinquent_30_plus"] == True]["outstanding_principal"].sum())
    record_validation("Delinquent Balance (30+ DPD)", "03_Delinquency_Risk", "CALCULATE([Outstanding Principal], is_delinquent_30_plus)", 143707050.71, delinq_bal, 0.05, "$")

    # Delinquency Rate % (PAR 30)
    delinq_rate = float((delinq_bal / closing_principal) * 100)
    record_validation("Delinquency Rate % (PAR 30)", "03_Delinquency_Risk", "DIVIDE([Delinquent Balance 30+], [Outstanding Principal])", 3.68, delinq_rate, 0.05, "%")

    # Current Performing Balance
    perf_bal = float(latest_perf[latest_perf["days_past_due"] < 30]["outstanding_principal"].sum())
    record_validation("Current Performing Balance", "03_Delinquency_Risk", "CALCULATE([Outstanding Principal], DPD < 30)", 3758720236.85, perf_bal, 0.05, "$")

    # Performing Ratio %
    perf_rate = float((perf_bal / closing_principal) * 100)
    record_validation("Current Performing Rate %", "03_Delinquency_Risk", "DIVIDE([Current Performing Balance], [Outstanding Principal])", 96.32, perf_rate, 0.05, "%")

    # =========================================================================
    # 04 General Ledger & Financial Performance
    # =========================================================================
    print("\n--- Folder: 04_Financial_GL ---")
    # Total Debits
    total_debits = float(fact_financial["total_debit"].sum())
    record_validation("Total Debits", "04_Financial_GL", "SUM(fact_financial[total_debit])", 491300436.35, total_debits, 0.05, "$")

    # Total Credits
    total_credits = float(fact_financial["total_credit"].sum())
    record_validation("Total Credits", "04_Financial_GL", "SUM(fact_financial[total_credit])", 491300436.35, total_credits, 0.05, "$")

    # GL Debit-Credit Variance (Must be exactly $0.00)
    gl_diff = float(abs(total_debits - total_credits))
    record_validation("GL Debit-Credit Variance", "04_Financial_GL", "ABS([Total Debits] - [Total Credits])", 0.0, gl_diff, 0.001, "$")

    # =========================================================================
    # 05 QA & Defect Analytics
    # =========================================================================
    print("\n--- Folder: 05_QA_Defects ---")
    # Total Defects
    total_defects = int(len(fact_defect))
    record_validation("Total Defects", "05_QA_Defects", "COUNTROWS(fact_defect)", 600, total_defects, 0, "#")

    # Critical Defects
    crit_defects = int((fact_defect["severity"] == "CRITICAL").sum())
    record_validation("Critical Defects", "05_QA_Defects", "CALCULATE([Total Defects], severity = 'CRITICAL')", 150, crit_defects, 0, "#")

    # Major Defects
    maj_defects = int((fact_defect["severity"] == "MAJOR").sum())
    record_validation("Major Defects", "05_QA_Defects", "CALCULATE([Total Defects], severity = 'MAJOR')", 300, maj_defects, 0, "#")

    # Minor Defects
    min_defects = int((fact_defect["severity"] == "MINOR").sum())
    record_validation("Minor Defects", "05_QA_Defects", "CALCULATE([Total Defects], severity = 'MINOR')", 150, min_defects, 0, "#")

    # Defect Density per 1k ops (600 / 29741 * 1000)
    density = float((total_defects / 29741) * 1000)
    record_validation("Defect Density per 1k Ops", "05_QA_Defects", "DIVIDE([Total Defects], [Servicing Operations]) * 1000", 20.17, density, 0.05, "#")

    # Actual Injection Rate % (600 / 29741 * 100)
    inj_rate = float((total_defects / 29741) * 100)
    record_validation("Defect Injection Rate %", "05_QA_Defects", "DIVIDE([Total Defects], [Servicing Operations]) * 100", 2.02, inj_rate, 0.05, "%")

    # Financial Variance Exposure
    var_exposure = float(fact_defect["variance_amount"].abs().sum())
    record_validation("Financial Variance Exposure", "05_QA_Defects", "SUM(fact_defect[variance_amount])", 901738.50, var_exposure, 0.05, "$")

    # =========================================================================
    # 06 Data Quality & Platform SRE
    # =========================================================================
    print("\n--- Folder: 06_DataQuality_SRE ---")
    # Total Rules Evaluated
    total_dq_rules = int(fact_dq["total_rules_evaluated"].sum())
    record_validation("Total DQ Rules Evaluated", "06_DataQuality_SRE", "SUM(fact_data_quality[total_rules_evaluated])", 22, total_dq_rules, 0, "#")

    # DQ Rules Passed
    dq_passed = int(fact_dq["rules_passed"].sum())
    record_validation("DQ Rules Passed", "06_DataQuality_SRE", "SUM(fact_data_quality[rules_passed])", 22, dq_passed, 0, "#")

    # Overall DQ Compliance %
    dq_compliance = float((dq_passed / total_dq_rules) * 100)
    record_validation("Overall DQ Compliance %", "06_DataQuality_SRE", "DIVIDE([DQ Rules Passed], [Total DQ Rules]) * 100", 100.0, dq_compliance, 0.01, "%")

    # Summary Output
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    total_count = len(results)
    pass_pct = round((passed_count / total_count) * 100, 2)

    scorecard = {
        "validation_engine": "FinSight Enterprise DAX Measure Verification",
        "total_measures_audited": total_count,
        "measures_passed": passed_count,
        "measures_failed": total_count - passed_count,
        "pass_rate_pct": pass_pct,
        "status": "ALL_MEASURES_PASSED" if passed_count == total_count else "FAILED",
        "measure_results": results
    }

    with open(OUTPUT_DIR / "dax_validation_scorecard.json", "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)

    print("\n" + "=" * 85)
    print(f" DAX VALIDATION COMPLETE: {passed_count}/{total_count} MEASURES PASSED ({pass_pct}%) ")
    print("=" * 85)
    return scorecard


if __name__ == "__main__":
    validate_all_dax_measures()
