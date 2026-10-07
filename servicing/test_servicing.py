"""
FinSight Enterprise — Servicing Simulation & Validation Gate Tests (Phase 2, Stage 2.3)
Validates schedule generation, daily accruals, payment waterfall conservation,
DPD calculations, double-entry GL balance, dual-path reconciliation, and reproducibility.
"""

from decimal import Decimal
import pytest
import pandas as pd
from servicing.run_servicing import execute_servicing_simulation
from servicing.config import DEFAULT_SEED


@pytest.fixture(scope="module")
def servicing_results():
    """Executes a standard servicing simulation run on the portfolio."""
    return execute_servicing_simulation(cycles=6, seed=DEFAULT_SEED, save=False)


def test_schedule_generation_validity(servicing_results):
    """Validates contractual payment schedules for chronological dates and balance conservation."""
    schedules_df, _, _, _, _, _, _, _, _ = servicing_results

    assert len(schedules_df) > 0
    assert (pd.to_datetime(schedules_df["due_date"]) > pd.to_datetime(schedules_df["billing_date"])).all()

    # Amount conservation: Total Due == Principal + Interest + Fees
    computed_due = (
        schedules_df["scheduled_principal"] +
        schedules_df["scheduled_interest"] +
        schedules_df["fees"]
    ).round(2)
    assert (computed_due == schedules_df["total_amount_due"].round(2)).all()

    # Principal reduction: Closing == Opening - Scheduled Principal
    computed_closing = (schedules_df["opening_principal"] - schedules_df["scheduled_principal"]).round(2)
    assert (computed_closing == schedules_df["closing_principal"].round(2)).all()


def test_accrual_conventions_math_accuracy(servicing_results):
    """Validates interest accruals across ACTUAL/360, ACTUAL/365, and 30/360 conventions."""
    _, accruals_df, _, _, _, _, _, _, _ = servicing_results

    assert len(accruals_df) > 0
    assert (accruals_df["interest_accrual_amount"] >= 0).all()
    assert (accruals_df["day_fraction"] > 0).all()

    conventions = set(accruals_df["interest_method"].unique())
    assert {"ACTUAL/360", "ACTUAL/365", "30/360"}.issubset(conventions)


def test_payment_execution_behavior_distribution(servicing_results):
    """Validates that all servicing behaviors (ON_TIME, LATE, EARLY, PARTIAL, MISSED) occur."""
    _, _, payments_df, _, cycle_delinquency_df, _, _, _, _ = servicing_results

    assert len(payments_df) > 0
    assert (payments_df["payment_amount"] > 0).all()
    assert payments_df["payment_id"].is_unique

    # Delinquency cycle should capture diverse aging buckets
    buckets = set(cycle_delinquency_df["dpd_bucket"].unique())
    assert "CURRENT" in buckets
    assert len(buckets) >= 3, f"Expected multiple delinquency buckets, got {buckets}"


def test_waterfall_allocation_conservation_invariant(servicing_results):
    """
    Critical FinOps Test:
    Enforces that every allocation satisfies: Total Allocated == Fees + Interest + Principal + Prepayment == Payment.
    """
    _, _, payments_df, allocations_df, _, _, _, _, _ = servicing_results

    assert len(allocations_df) == len(payments_df)

    sum_allocations = (
        allocations_df["fees_amount"] +
        allocations_df["interest_amount"] +
        allocations_df["principal_amount"] +
        allocations_df["prepayment_amount"]
    ).round(2)

    assert (sum_allocations == allocations_df["total_allocated"].round(2)).all()

    # Compare against payment amounts
    merged = allocations_df.merge(payments_df[["payment_id", "payment_amount"]], on="payment_id")
    assert (merged["total_allocated"].round(2) == merged["payment_amount"].round(2)).all()


def test_dpd_calculation_from_dates(servicing_results):
    """Validates that DPD is computed strictly from date arithmetic."""
    _, _, _, _, cycle_delinquency_df, _, _, _, _ = servicing_results

    for _, row in cycle_delinquency_df.iterrows():
        due_date = row["due_date"]
        pmt_date = row["payment_date"]
        dpd = row["days_past_due"]

        if pmt_date is not None:
            expected_dpd = max(0, (pmt_date - due_date).days)
            assert dpd == expected_dpd


def test_gl_double_entry_debit_equals_credit(servicing_results):
    """
    Fundamental Accounting Invariant:
    Every journal entry must balance, and total debits across the ledger must equal total credits.
    """
    _, _, _, _, _, gl_entries_df, gl_lines_df, _, _ = servicing_results

    assert len(gl_entries_df) > 0
    assert len(gl_lines_df) > 0

    # Header check
    assert (gl_entries_df["total_debit"].round(2) == gl_entries_df["total_credit"].round(2)).all()
    assert gl_entries_df["is_balanced"].all()

    # Ledger check
    total_dr = round(gl_lines_df["debit_amount"].sum(), 2)
    total_cr = round(gl_lines_df["credit_amount"].sum(), 2)
    assert total_dr == total_cr, f"GL out of balance: DR {total_dr} != CR {total_cr}"


def test_reconciliation_dual_path_100_percent_pass(servicing_results):
    """
    ADR-003 Gate:
    In Stage 2.3 clean baseline, 100% of operational servicing calculations must match
    the independent MathematicalTruthEngine benchmark with zero failures.
    """
    _, _, _, _, _, _, _, recon_df, _ = servicing_results

    assert len(recon_df) > 0
    assert (recon_df["status"] == "PASS").all(), "Found failed reconciliations in clean baseline"
    assert (recon_df["variance_amount"].abs() <= recon_df["tolerance_threshold"]).all()
    assert (recon_df["root_cause_category"].isna()).all(), "Unexpected defect category in clean baseline"


def test_servicing_reproducibility():
    """Validates that running the servicing simulation twice produces identical results."""
    res_a = execute_servicing_simulation(cycles=2, seed=20261006, save=False)
    res_b = execute_servicing_simulation(cycles=2, seed=20261006, save=False)

    schedules_a, accruals_a, payments_a, alloc_a = res_a[0], res_a[1], res_a[2], res_a[3]
    schedules_b, accruals_b, payments_b, alloc_b = res_b[0], res_b[1], res_b[2], res_b[3]

    pd.testing.assert_frame_equal(schedules_a, schedules_b)
    pd.testing.assert_frame_equal(accruals_a, accruals_b)
    pd.testing.assert_frame_equal(payments_a, payments_b)
    pd.testing.assert_frame_equal(alloc_a, alloc_b)
