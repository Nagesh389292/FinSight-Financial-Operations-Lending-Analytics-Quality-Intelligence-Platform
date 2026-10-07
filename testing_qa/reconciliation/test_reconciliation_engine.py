"""
FinSight Enterprise — Automated QA Test Suite: Financial Reconciliation Engine
Validates expected vs actual tolerance checking and defect candidate extraction.
Linked to: BRD-FIN-005, BRD-FIN-006
"""

from decimal import Decimal
import pytest
from api.app.services.math_truth import MathematicalTruthEngine


@pytest.mark.requirement("BRD-FIN-005")
def test_reconciliation_exact_pass():
    """
    Test Scenario: Processed value matches expected value exactly.
    Expected: $12,450.00 | Actual: $12,450.00
    Result: PASS, Variance: $0.00
    """
    res = MathematicalTruthEngine.reconcile_calculation(
        expected=Decimal("12450.00"),
        actual=Decimal("12450.00"),
        tolerance=Decimal("0.01")
    )
    assert res["status"] == "PASS"
    assert res["variance"] == Decimal("0.00")
    assert res["is_within_tolerance"] is True


@pytest.mark.requirement("BRD-FIN-006")
def test_reconciliation_sub_penny_tolerance_pass():
    """
    Test Scenario: Sub-penny rounding variance within $0.01 threshold passes.
    Expected: $8,450.005 | Actual: $8,450.010 | Diff: $0.005 <= $0.01
    Result: PASS
    """
    res = MathematicalTruthEngine.reconcile_calculation(
        expected=Decimal("8450.005"),
        actual=Decimal("8450.010"),
        tolerance=Decimal("0.01")
    )
    assert res["status"] == "PASS"
    assert res["is_within_tolerance"] is True


@pytest.mark.requirement("BRD-FIN-006")
def test_reconciliation_penny_breach_fail():
    """
    Test Scenario: Variance of $0.02 breaches $0.01 tolerance and flags FAIL.
    Expected: $10,000.00 | Actual: $10,000.02
    Result: FAIL
    """
    res = MathematicalTruthEngine.reconcile_calculation(
        expected=Decimal("10000.00"),
        actual=Decimal("10000.02"),
        tolerance=Decimal("0.01")
    )
    assert res["status"] == "FAIL"
    assert res["is_within_tolerance"] is False
    assert res["variance"] == Decimal("0.02")


@pytest.mark.requirement("BRD-FIN-006")
def test_reconciliation_severe_miscalculation_fail():
    """
    Test Scenario: Material calculation discrepancy ($350.00 accrual error).
    Expected: $12,450.00 | Actual: $12,800.00
    Result: FAIL, Variance: +$350.00
    """
    res = MathematicalTruthEngine.reconcile_calculation(
        expected=Decimal("12450.00"),
        actual=Decimal("12800.00"),
        tolerance=Decimal("0.01")
    )
    assert res["status"] == "FAIL"
    assert res["variance"] == Decimal("350.00")
    assert res["variance_pct"] == Decimal("2.81")
