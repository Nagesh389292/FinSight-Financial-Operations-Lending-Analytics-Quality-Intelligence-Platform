"""
FinSight Enterprise — Automated QA Test Suite: Financial Calculations
Validates day-count accruals, banker's rounding, and amortization schedules.
Linked to: BRD-FIN-001, BRD-FIN-002, BRD-FIN-003
"""

from decimal import Decimal
from datetime import date
import pytest
from api.app.services.math_truth import MathematicalTruthEngine, round_bankers


@pytest.mark.requirement("BRD-FIN-001")
def test_actual_360_accrual_calculation():
    """
    Test Scenario: Verify standard US Commercial Actual/360 day-count calculation.
    Principal: $1,000,000, Annual Rate: 6.00%, Days: 30
    Expected: 1,000,000 * (0.06 / 360) * 30 = $5,000.00
    """
    principal = Decimal("1000000.00")
    rate = Decimal("0.06000")
    
    accrual = MathematicalTruthEngine.calculate_monthly_accrued_interest(
        principal=principal,
        annual_rate=rate,
        day_count_convention="ACTUAL/360",
        days_in_cycle=30
    )
    assert accrual == Decimal("5000.00"), f"Expected $5,000.00, got {accrual}"


@pytest.mark.requirement("BRD-FIN-001")
def test_actual_365_accrual_calculation():
    """
    Test Scenario: Verify UK/Commonwealth Actual/365 day-count calculation.
    Principal: $100,000, Annual Rate: 7.30%, Days: 30
    Expected: 100,000 * (0.073 / 365) * 30 = $600.00
    """
    principal = Decimal("100000.00")
    rate = Decimal("0.07300")
    
    accrual = MathematicalTruthEngine.calculate_monthly_accrued_interest(
        principal=principal,
        annual_rate=rate,
        day_count_convention="ACTUAL/365",
        days_in_cycle=30
    )
    assert accrual == Decimal("600.00"), f"Expected $600.00, got {accrual}"


@pytest.mark.requirement("BRD-FIN-001")
def test_30_360_european_accrual():
    """
    Test Scenario: Verify 30/360 Bond Basis day-count calculation.
    Principal: $250,000, Annual Rate: 4.80%
    Expected: 250,000 * (0.048 / 12) = $1,000.00
    """
    principal = Decimal("250000.00")
    rate = Decimal("0.04800")
    
    accrual = MathematicalTruthEngine.calculate_monthly_accrued_interest(
        principal=principal,
        annual_rate=rate,
        day_count_convention="30/360"
    )
    assert accrual == Decimal("1000.00"), f"Expected $1,000.00, got {accrual}"


@pytest.mark.requirement("BRD-FIN-001")
def test_bankers_rounding_half_even():
    """
    Test Scenario: Banker's Rounding (ROUND_HALF_EVEN) must round to nearest even cent.
    2.125 -> 2.12 (even)
    2.135 -> 2.14 (even)
    """
    assert round_bankers(Decimal("2.125")) == Decimal("2.12")
    assert round_bankers(Decimal("2.135")) == Decimal("2.14")
    assert round_bankers(Decimal("2.145")) == Decimal("2.14")
    assert round_bankers(Decimal("2.155")) == Decimal("2.16")


@pytest.mark.requirement("BRD-FIN-003")
def test_interest_only_scheduled_principal_zero():
    """
    Test Scenario: Interest-only loans must have scheduled principal of $0.00 prior to balloon maturity.
    """
    sched_p = MathematicalTruthEngine.calculate_scheduled_principal(
        original_principal=Decimal("5000000.00"),
        current_balance=Decimal("5000000.00"),
        annual_rate=Decimal("0.055"),
        term_months=36,
        amortization_type="INTEREST_ONLY_BALLOON"
    )
    assert sched_p == Decimal("0.00")
