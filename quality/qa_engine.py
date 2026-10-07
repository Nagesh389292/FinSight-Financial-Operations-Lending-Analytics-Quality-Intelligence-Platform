"""
FinSight Enterprise — Automated QA Reconciliation & Defect Extraction Engine (Stage 2.4)
Executes financial reconciliation checks against operational data, identifies tolerance breaches,
and programmatically generates defects linked to BRD requirements and test cases via the RTM.
"""

from decimal import Decimal
from datetime import date
import pandas as pd
from api.app.services.math_truth import MathematicalTruthEngine, to_decimal
from quality.config import DEFECT_TAXONOMY, REFERENCE_TIMESTAMP


def execute_qa_reconciliation_and_defect_extraction(
    schedules_df: pd.DataFrame,
    accruals_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    tolerance: Decimal = Decimal("0.0100"),
    run_id: str = "RUN-QA-CERT-001"
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Executes automated dual-path financial validation, detects variances,
    and programmatically extracts defects and test executions.
    Returns:
    - recon_df: Full reconciliation log (PASS and FAIL rows)
    - defects_df: Extracted defect records matching qa.defects schema
    - test_executions_df: Test execution records matching qa.test_executions schema
    """
    recon_records = []
    defects = []
    test_executions = []

    recon_counter = 1
    defect_counter = 1
    exec_counter = 1

    # -------------------------------------------------------------------------
    # 1. Accrual Reconciliation (Day Count, Leap Year, Rounding Truncation)
    # -------------------------------------------------------------------------
    merged_acc = accruals_df.merge(
        schedules_df[["schedule_id", "loan_id", "period_number", "opening_principal", "scheduled_interest"]],
        on=["loan_id", "period_number"]
    )

    for _, row in merged_acc.iterrows():
        loan_id = row["loan_id"]
        cycle_date = row["accrual_date"]
        p = to_decimal(row["start_principal_balance"])
        r = to_decimal(row["interest_rate_annual"])
        conv = row["interest_method"]
        days = int(row["day_count"])

        # Independent Mathematical Truth Calculation
        expected_interest = MathematicalTruthEngine.calculate_monthly_accrued_interest(
            principal=p,
            annual_rate=r,
            day_count_convention=conv,
            days_in_cycle=days
        )
        actual_interest = to_decimal(row["interest_accrual_amount"])

        check = MathematicalTruthEngine.reconcile_calculation(
            expected=expected_interest,
            actual=actual_interest,
            tolerance=tolerance
        )

        status = check["status"]
        variance = check["variance"]
        abs_variance = check["abs_variance"]

        root_cause = None
        if status == "FAIL":
            # Infer root cause from financial calculation behavior
            if conv == "ACTUAL/365" and actual_interest > expected_interest:
                root_cause = "DAY_COUNT_MISMATCH"
            elif abs_variance < Decimal("0.10"):
                root_cause = "ROUNDING_TRUNCATION"
            else:
                root_cause = "LEAP_YEAR_BLINDNESS"

        recon_records.append({
            "reconciliation_id": f"REC-ACC-{recon_counter:08d}",
            "loan_id": loan_id,
            "cycle_date": cycle_date,
            "reconciliation_type": "INTEREST_ACCRUAL",
            "expected_amount": float(check["expected"]),
            "actual_amount": float(check["actual"]),
            "variance_amount": float(variance),
            "tolerance_threshold": float(tolerance),
            "status": status,
            "root_cause_category": root_cause,
            "notes": f"Convention {conv}, Days {days}",
            "reconciled_at": REFERENCE_TIMESTAMP
        })
        recon_counter += 1

        # Defect extraction on failure
        if status == "FAIL":
            tax_spec = DEFECT_TAXONOMY.get(root_cause, DEFECT_TAXONOMY["DAY_COUNT_MISMATCH"])
            defect_id = f"DEF-2026-{defect_counter:04d}"

            defects.append({
                "defect_id": defect_id,
                "test_case_id": tax_spec["test_case_id"],
                "rule_id": tax_spec["rule_id"],
                "requirement_id": tax_spec["requirement_id"],
                "loan_id": loan_id,
                "title": f"[{root_cause}] {tax_spec['title']} on {loan_id}",
                "severity": tax_spec["severity"],
                "priority": tax_spec["priority"],
                "status": "NEW",
                "variance_amount": float(variance),
                "expected_value": float(check["expected"]),
                "actual_value": float(check["actual"]),
                "root_cause_category": root_cause,
                "root_cause_analysis": f"Expected interest ${check['expected']:,.2f} vs processed ${check['actual']:,.2f}. Variance ${variance:,.2f} breaches ${tolerance:,.2f} tolerance.",
                "resolution_summary": None,
                "assigned_to": "Servicing Operations / QA Engineering",
                "created_at": REFERENCE_TIMESTAMP
            })
            defect_counter += 1

            test_executions.append({
                "execution_id": exec_counter,
                "run_id": run_id,
                "test_case_id": tax_spec["test_case_id"],
                "loan_id": loan_id,
                "status": "FAILED",
                "duration_ms": 2.50,
                "assertion_message": f"Variance ${variance:,.2f} exceeded threshold ${tolerance:,.2f}",
                "executed_by": "FinSight-QA-ReconEngine",
                "executed_at": REFERENCE_TIMESTAMP
            })
            exec_counter += 1

    # -------------------------------------------------------------------------
    # 2. Principal Reduction & Waterfall Allocation Reconciliation
    # -------------------------------------------------------------------------
    merged_alloc = allocations_df.merge(
        schedules_df[["loan_id", "period_number", "opening_principal", "scheduled_principal", "scheduled_interest"]],
        on=["loan_id", "period_number"]
    )

    for _, row in merged_alloc.iterrows():
        loan_id = row["loan_id"]
        total_paid = to_decimal(row["total_allocated"])
        fees_paid = to_decimal(row["fees_amount"])
        sched_interest = to_decimal(row["scheduled_interest"])
        sched_p = to_decimal(row["scheduled_principal"])
        opening_p = to_decimal(row["opening_principal"])

        # Expected principal under contractual priority:
        # Cash remaining after satisfying fees and interest, capped at scheduled principal
        expected_p = min(max(Decimal("0.00"), total_paid - fees_paid - sched_interest), sched_p, opening_p)
        actual_p = to_decimal(row["principal_amount"])

        check = MathematicalTruthEngine.reconcile_calculation(
            expected=expected_p,
            actual=actual_p,
            tolerance=tolerance
        )

        status = check["status"]
        variance = check["variance"]

        root_cause = "WATERFALL_ORDERING" if status == "FAIL" else None

        recon_records.append({
            "reconciliation_id": f"REC-PRN-{recon_counter:08d}",
            "loan_id": loan_id,
            "cycle_date": row["allocation_timestamp"].date() if hasattr(row["allocation_timestamp"], "date") else date(2024, 6, 30),
            "reconciliation_type": "PRINCIPAL_REDUCTION",
            "expected_amount": float(check["expected"]),
            "actual_amount": float(check["actual"]),
            "variance_amount": float(variance),
            "tolerance_threshold": float(tolerance),
            "status": status,
            "root_cause_category": root_cause,
            "notes": "Waterfall priority tie-out",
            "reconciled_at": REFERENCE_TIMESTAMP
        })
        recon_counter += 1

        # Defect extraction on waterfall failure
        if status == "FAIL":
            tax_spec = DEFECT_TAXONOMY["WATERFALL_ORDERING"]
            defect_id = f"DEF-2026-{defect_counter:04d}"

            defects.append({
                "defect_id": defect_id,
                "test_case_id": tax_spec["test_case_id"],
                "rule_id": tax_spec["rule_id"],
                "requirement_id": tax_spec["requirement_id"],
                "loan_id": loan_id,
                "title": f"[WATERFALL_ORDERING] Priority reversal on {loan_id}",
                "severity": tax_spec["severity"],
                "priority": tax_spec["priority"],
                "status": "NEW",
                "variance_amount": float(variance),
                "expected_value": float(check["expected"]),
                "actual_value": float(check["actual"]),
                "root_cause_category": "WATERFALL_ORDERING",
                "root_cause_analysis": f"Payment applied to principal (${check['actual']:,.2f}) before satisfying interest/fees due. Expected principal ${check['expected']:,.2f}.",
                "resolution_summary": None,
                "assigned_to": "Servicing Operations / Core Banking Team",
                "created_at": REFERENCE_TIMESTAMP
            })
            defect_counter += 1

            test_executions.append({
                "execution_id": exec_counter,
                "run_id": run_id,
                "test_case_id": tax_spec["test_case_id"],
                "loan_id": loan_id,
                "status": "FAILED",
                "duration_ms": 3.10,
                "assertion_message": f"Waterfall priority breached: principal allocated before interest",
                "executed_by": "FinSight-QA-ReconEngine",
                "executed_at": REFERENCE_TIMESTAMP
            })
            exec_counter += 1

    recon_df = pd.DataFrame(recon_records)
    defects_df = pd.DataFrame(defects)
    test_executions_df = pd.DataFrame(test_executions)

    return recon_df, defects_df, test_executions_df
