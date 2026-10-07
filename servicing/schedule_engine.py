"""
FinSight Enterprise — Payment Schedule Engine (Stage 2.3.1)
Generates contractual payment billing schedules prior to payment execution.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from datetime import date, timedelta
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers


def calculate_schedule_dates(origination_date: date, period_num: int) -> tuple[date, date]:
    """Calculates billing date and payment due date for a given monthly period."""
    billing_date = origination_date + timedelta(days=int(30.4375 * (period_num - 1)))
    due_date = origination_date + timedelta(days=int(30.4375 * period_num))
    return billing_date, due_date


def calculate_scheduled_interest_amount(
    principal: Decimal,
    annual_rate: Decimal,
    interest_method: str,
    days_count: int
) -> Decimal:
    """Calculates scheduled contractual interest for a billing cycle according to day-count convention."""
    p = to_decimal(principal)
    r = to_decimal(annual_rate)

    if interest_method == "ACTUAL/360":
        interest = p * (r / Decimal("360")) * Decimal(str(days_count))
    elif interest_method == "ACTUAL/365":
        interest = p * (r / Decimal("365")) * Decimal(str(days_count))
    elif interest_method == "30/360":
        interest = p * (r / Decimal("12"))
    else:
        # Fallback to 30/360
        interest = p * (r / Decimal("12"))

    return round_bankers(interest)


def generate_payment_schedules(
    loans_df: pd.DataFrame,
    terms_df: pd.DataFrame,
    cycles_to_simulate: int = 6
) -> pd.DataFrame:
    """
    Generates contractual payment schedules for all active loan facilities.
    Calculates period-by-period opening balance, scheduled principal, scheduled interest,
    total amount due, and closing balance.
    """
    # Merge loan and term specifications
    merged = loans_df.merge(terms_df, on="loan_id", suffixes=("", "_term"))
    schedules = []

    for _, row in merged.iterrows():
        loan_id = row["loan_id"]
        orig_principal = to_decimal(row["principal_original"])
        annual_rate = to_decimal(row["interest_rate_annual"])
        term_months = int(row["term_months"])
        start_date = row["start_date"]
        interest_method = row["interest_method"]
        amort_schedule = row["amortization_schedule"]

        periods = min(cycles_to_simulate, term_months)
        current_balance = orig_principal

        for p in range(1, periods + 1):
            schedule_id = f"SCH-{loan_id}-{p:03d}"
            billing_date, due_date = calculate_schedule_dates(start_date, p)
            days_count = (due_date - billing_date).days

            opening_principal = current_balance

            # Scheduled Interest
            sched_interest = calculate_scheduled_interest_amount(
                principal=opening_principal,
                annual_rate=annual_rate,
                interest_method=interest_method,
                days_count=days_count
            )

            # Scheduled Principal
            if amort_schedule == "INTEREST_ONLY_BALLOON":
                sched_principal = Decimal("0.00") if p < term_months else opening_principal
            elif amort_schedule == "AMORTIZING_FIXED_PRINCIPAL":
                fixed_p = orig_principal / Decimal(str(term_months))
                sched_principal = min(opening_principal, round_bankers(fixed_p))
            else: # EQUAL_INSTALLMENT / default amortizing
                monthly_rate = annual_rate / Decimal("12")
                if monthly_rate > 0:
                    r_f = float(monthly_rate)
                    n = term_months
                    factor = (r_f * (1 + r_f) ** n) / ((1 + r_f) ** n - 1)
                    total_pmt = round_bankers(orig_principal * Decimal(str(factor)))
                    sched_principal = min(opening_principal, max(Decimal("0.00"), total_pmt - sched_interest))
                else:
                    sched_principal = min(opening_principal, round_bankers(orig_principal / Decimal(str(term_months))))

            fees = Decimal("0.00")
            total_amount_due = round_bankers(sched_principal + sched_interest + fees)
            closing_principal = max(Decimal("0.00"), opening_principal - sched_principal)

            schedules.append({
                "schedule_id": schedule_id,
                "loan_id": loan_id,
                "period_number": p,
                "billing_date": billing_date,
                "due_date": due_date,
                "opening_principal": float(opening_principal),
                "scheduled_principal": float(sched_principal),
                "scheduled_interest": float(sched_interest),
                "fees": float(fees),
                "total_amount_due": float(total_amount_due),
                "closing_principal": float(closing_principal),
                "interest_method": interest_method,
                "days_in_period": days_count
            })

            current_balance = closing_principal

    return pd.DataFrame(schedules)
