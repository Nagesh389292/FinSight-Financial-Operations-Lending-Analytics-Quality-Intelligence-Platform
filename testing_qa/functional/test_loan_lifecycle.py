"""
FinSight Enterprise — Automated QA Test Suite: Loan Servicing & Lifecycle
Validates payment waterfall execution, state machine transitions, and DPD buckets.
Linked to: BRD-CORE-005, BRD-CORE-006, BRD-CORE-007
"""

from decimal import Decimal
import pytest


def execute_payment_waterfall(
    payment_amount: Decimal,
    fees_due: Decimal,
    interest_due: Decimal,
    scheduled_principal: Decimal
) -> dict:
    """Simulates payment waterfall cash allocation according to contractual rules."""
    rem = payment_amount

    # 1. Fees
    fee_applied = min(rem, fees_due)
    rem -= fee_applied

    # 2. Interest
    interest_applied = min(rem, interest_due)
    rem -= interest_applied

    # 3. Scheduled Principal
    principal_applied = min(rem, scheduled_principal)
    rem -= principal_applied

    # 4. Prepayment / Unscheduled Principal
    prepayment_applied = rem

    return {
        "fee_applied": fee_applied,
        "interest_applied": interest_applied,
        "principal_applied": principal_applied,
        "prepayment_applied": prepayment_applied,
        "unallocated": Decimal("0.00")
    }


def classify_delinquency(dpd: int) -> str:
    """Classifies DPD into banking regulatory aging buckets."""
    if dpd <= 0:
        return "CURRENT"
    elif 1 <= dpd <= 29:
        return "BUCKET_1"
    elif 30 <= dpd <= 59:
        return "BUCKET_2"
    elif 60 <= dpd <= 89:
        return "BUCKET_3"
    else:
        return "DEFAULT"


@pytest.mark.requirement("BRD-CORE-006")
def test_full_payment_waterfall():
    """
    Test Scenario: Exact on-time payment covering fee, interest, and principal.
    Amount Paid: $1,550.00 | Fee: $50.00 | Interest: $500.00 | Scheduled Principal: $1,000.00
    """
    res = execute_payment_waterfall(
        payment_amount=Decimal("1550.00"),
        fees_due=Decimal("50.00"),
        interest_due=Decimal("500.00"),
        scheduled_principal=Decimal("1000.00")
    )
    assert res["fee_applied"] == Decimal("50.00")
    assert res["interest_applied"] == Decimal("500.00")
    assert res["principal_applied"] == Decimal("1000.00")
    assert res["prepayment_applied"] == Decimal("0.00")


@pytest.mark.requirement("BRD-CORE-006")
def test_short_payment_waterfall_preserves_priority():
    """
    Test Scenario: Short payment ($400.00) must cover Fee ($50) first, partial Interest ($350), and zero Principal.
    """
    res = execute_payment_waterfall(
        payment_amount=Decimal("400.00"),
        fees_due=Decimal("50.00"),
        interest_due=Decimal("500.00"),
        scheduled_principal=Decimal("1000.00")
    )
    assert res["fee_applied"] == Decimal("50.00")
    assert res["interest_applied"] == Decimal("350.00")
    assert res["principal_applied"] == Decimal("0.00")
    assert res["prepayment_applied"] == Decimal("0.00")


@pytest.mark.requirement("BRD-CORE-006")
def test_prepayment_waterfall_surplus():
    """
    Test Scenario: Excess payment ($2,550.00) applies $1,000 to unscheduled principal prepayment.
    """
    res = execute_payment_waterfall(
        payment_amount=Decimal("2550.00"),
        fees_due=Decimal("50.00"),
        interest_due=Decimal("500.00"),
        scheduled_principal=Decimal("1000.00")
    )
    assert res["principal_applied"] == Decimal("1000.00")
    assert res["prepayment_applied"] == Decimal("1000.00")


@pytest.mark.requirement("BRD-CORE-007")
def test_dpd_delinquency_bucket_classification():
    """
    Test Scenario: Verify correct regulatory aging bucket assignment.
    """
    assert classify_delinquency(0) == "CURRENT"
    assert classify_delinquency(15) == "BUCKET_1"
    assert classify_delinquency(45) == "BUCKET_2"
    assert classify_delinquency(75) == "BUCKET_3"
    assert classify_delinquency(91) == "DEFAULT"
    assert classify_delinquency(180) == "DEFAULT"
