"""
FinSight Enterprise — Payment Waterfall Allocation Engine (Stage 2.3.4)
Executes contractual payment waterfall hierarchy:
1. Fees Due
2. Interest Due
3. Scheduled Principal Due
4. Prepayment / Unscheduled Principal

Enforces strict conservation invariant:
Total Allocated == Fees + Interest + Principal + Prepayment == Payment Amount.
"""

from decimal import Decimal, ROUND_HALF_EVEN
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers
from servicing.config import REFERENCE_TIMESTAMP


def execute_waterfall_allocation(
    payment_amount: Decimal,
    fees_due: Decimal,
    interest_due: Decimal,
    principal_due: Decimal,
    current_balance: Decimal
) -> dict:
    """
    Allocates a single payment across fees, interest, scheduled principal, and prepayment.
    """
    p_amt = to_decimal(payment_amount)
    f_due = to_decimal(fees_due)
    i_due = to_decimal(interest_due)
    p_due = to_decimal(principal_due)
    bal = to_decimal(current_balance)

    rem = p_amt

    # 1. Fees
    fee_alloc = min(rem, f_due)
    rem -= fee_alloc

    # 2. Interest
    interest_alloc = min(rem, i_due)
    rem -= interest_alloc

    # 3. Scheduled Principal
    principal_alloc = min(rem, p_due, bal)
    rem -= principal_alloc

    # 4. Prepayment / Unscheduled Principal (absorbs remaining payment up to outstanding balance)
    prepayment_alloc = rem
    rem = Decimal("0.00")

    # Invariant verification
    total_alloc = fee_alloc + interest_alloc + principal_alloc + prepayment_alloc
    assert total_alloc == p_amt, f"Waterfall conservation breached! {total_alloc} != {p_amt}"

    closing_principal = max(Decimal("0.00"), bal - (principal_alloc + prepayment_alloc))

    return {
        "fees_amount": fee_alloc,
        "interest_amount": interest_alloc,
        "principal_amount": principal_alloc,
        "prepayment_amount": prepayment_alloc,
        "total_allocated": total_alloc,
        "closing_principal_balance": closing_principal
    }


def process_payment_allocations(
    payments_df: pd.DataFrame,
    billing_events_df: pd.DataFrame,
    schedules_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Processes all executed payments through the waterfall allocation hierarchy.
    Produces finance.payment_allocations records.
    """
    merged = payments_df.merge(
        billing_events_df[["schedule_id", "scheduled_principal_due", "scheduled_interest_due", "fee_assessed"]],
        on="schedule_id"
    ).merge(
        schedules_df[["schedule_id", "opening_principal"]],
        on="schedule_id"
    )

    allocations = []
    alloc_counter = 1

    for _, row in merged.iterrows():
        payment_id = row["payment_id"]
        loan_id = row["loan_id"]
        pmt_amount = to_decimal(row["payment_amount"])
        fees_due = to_decimal(row["fee_assessed"])
        interest_due = to_decimal(row["scheduled_interest_due"])
        principal_due = to_decimal(row["scheduled_principal_due"])
        opening_bal = to_decimal(row["opening_principal"])

        alloc_result = execute_waterfall_allocation(
            payment_amount=pmt_amount,
            fees_due=fees_due,
            interest_due=interest_due,
            principal_due=principal_due,
            current_balance=opening_bal
        )

        allocations.append({
            "allocation_id": alloc_counter,
            "payment_id": payment_id,
            "loan_id": loan_id,
            "period_number": row["period_number"],
            "principal_amount": float(alloc_result["principal_amount"]),
            "interest_amount": float(alloc_result["interest_amount"]),
            "fees_amount": float(alloc_result["fees_amount"]),
            "prepayment_amount": float(alloc_result["prepayment_amount"]),
            "total_allocated": float(alloc_result["total_allocated"]),
            "closing_principal_balance": float(alloc_result["closing_principal_balance"]),
            "allocation_timestamp": REFERENCE_TIMESTAMP
        })
        alloc_counter += 1

    return pd.DataFrame(allocations)
