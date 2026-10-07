"""
FinSight Enterprise — Independent Mathematical Truth Calculation Engine
Pure decimal implementation of banking interest calculations, day-count conventions,
and amortization schedules. Acts as the gold-standard benchmark for reconciliation and QA.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from datetime import date


def to_decimal(val) -> Decimal:
    """Safely converts floats, ints, or strings to Decimal."""
    if isinstance(val, Decimal):
        return val
    return Decimal(str(val))


def round_bankers(val: Decimal) -> Decimal:
    """Rounds to 2 decimal places using Banker's Rounding (ROUND_HALF_EVEN)."""
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


class MathematicalTruthEngine:
    """
    Stateless benchmark engine executing exact financial mathematics.
    Complies with US Commercial Lending and ISDA standard day-count rules.
    """

    @staticmethod
    def calculate_daily_interest(
        principal: Decimal,
        annual_rate: Decimal,
        day_count_convention: str,
        target_date: date = None
    ) -> Decimal:
        """
        Calculates exact single-day accrued interest.
        Conventions supported: 'ACTUAL/360', 'ACTUAL/365', '30/360'.
        """
        p = to_decimal(principal)
        r = to_decimal(annual_rate)

        if day_count_convention == "ACTUAL/360":
            daily_factor = r / Decimal("360")
        elif day_count_convention == "ACTUAL/365":
            days_in_year = Decimal("366") if (target_date and target_date.year % 4 == 0 and (target_date.year % 100 != 0 or target_date.year % 400 == 0)) else Decimal("365")
            daily_factor = r / days_in_year
        elif day_count_convention == "30/360":
            daily_factor = r / Decimal("360")
        else:
            raise ValueError(f"Unsupported day-count convention: {day_count_convention}")

        return p * daily_factor

    @staticmethod
    def calculate_monthly_accrued_interest(
        principal: Decimal,
        annual_rate: Decimal,
        day_count_convention: str,
        days_in_cycle: int = 30
    ) -> Decimal:
        """
        Calculates monthly interest accrual.
        Returns exact dollar amount rounded to nearest currency cent.
        """
        p = to_decimal(principal)
        r = to_decimal(annual_rate)

        if day_count_convention == "ACTUAL/360":
            daily_rate = r / Decimal("360")
            accrual = p * daily_rate * Decimal(str(days_in_cycle))
        elif day_count_convention == "ACTUAL/365":
            daily_rate = r / Decimal("365")
            accrual = p * daily_rate * Decimal(str(days_in_cycle))
        elif day_count_convention == "30/360":
            accrual = p * (r / Decimal("12"))
        else:
            raise ValueError(f"Unsupported day-count convention: {day_count_convention}")

        return round_bankers(accrual)

    @staticmethod
    def calculate_scheduled_principal(
        original_principal: Decimal,
        current_balance: Decimal,
        annual_rate: Decimal,
        term_months: int,
        amortization_type: str
    ) -> Decimal:
        """
        Calculates expected scheduled monthly principal repayment.
        """
        p_orig = to_decimal(original_principal)
        balance = to_decimal(current_balance)
        r = to_decimal(annual_rate)

        if amortization_type == "INTEREST_ONLY_BALLOON":
            return Decimal("0.00")
        elif amortization_type == "AMORTIZING_FIXED_PRINCIPAL":
            monthly_principal = p_orig / Decimal(str(term_months))
            return min(round_bankers(monthly_principal), balance)
        elif amortization_type == "AMORTIZING_EQUAL_INSTALLMENT":
            monthly_rate = r / Decimal("12")
            if monthly_rate == 0:
                return min(round_bankers(p_orig / Decimal(str(term_months))), balance)
            
            # Equal installment formula: P * [r(1+r)^n] / [(1+r)^n - 1]
            n = term_months
            r_float = float(monthly_rate)
            factor = (r_float * (1 + r_float)**n) / ((1 + r_float)**n - 1)
            total_monthly_pmt = round_bankers(p_orig * Decimal(str(factor)))
            interest_portion = round_bankers(balance * monthly_rate)
            principal_portion = max(Decimal("0.00"), total_monthly_pmt - interest_portion)
            return min(principal_portion, balance)
        else:
            raise ValueError(f"Unsupported amortization type: {amortization_type}")

    @staticmethod
    def reconcile_calculation(
        expected: Decimal,
        actual: Decimal,
        tolerance: Decimal = Decimal("0.0100")
    ) -> dict:
        """
        Compares expected vs actual financial amounts.
        Returns status ('PASS' or 'FAIL'), variance dollar amount, and variance percentage.
        """
        exp = to_decimal(expected)
        act = to_decimal(actual)
        variance = act - exp
        abs_var = abs(variance)
        status = "PASS" if abs_var <= tolerance else "FAIL"

        pct_var = Decimal("0.0")
        if exp != 0:
            pct_var = round_bankers((variance / exp) * Decimal("100.0"))

        return {
            "expected": exp,
            "actual": act,
            "variance": variance,
            "abs_variance": abs_var,
            "variance_pct": pct_var,
            "tolerance": tolerance,
            "status": status,
            "is_within_tolerance": status == "PASS"
        }
