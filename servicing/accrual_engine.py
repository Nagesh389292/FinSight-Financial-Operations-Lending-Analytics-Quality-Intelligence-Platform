"""
FinSight Enterprise — Daily Accrual Engine (Stage 2.3.2)
Calculates daily/period interest accruals across ACTUAL/360, ACTUAL/365, and 30/360 conventions.
Retains full explanatory context for each calculation to power auditability and QA reconciliation.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from datetime import date
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers
from servicing.config import REFERENCE_TIMESTAMP


def calculate_day_fraction(
    convention: str,
    days_count: int,
    target_date: date = None
) -> tuple[Decimal, int]:
    """
    Returns (day_fraction, day_count) under the specified convention.
    """
    if convention == "ACTUAL/360":
        fraction = Decimal(str(days_count)) / Decimal("360")
        return fraction, days_count
    elif convention == "ACTUAL/365":
        fraction = Decimal(str(days_count)) / Decimal("365")
        return fraction, days_count
    elif convention == "30/360":
        # 30/360 assumes standard 30-day month / 360-day year
        fraction = Decimal("30") / Decimal("360")
        return fraction, 30
    else:
        fraction = Decimal(str(days_count)) / Decimal("360")
        return fraction, days_count


def generate_accruals(
    schedules_df: pd.DataFrame,
    loans_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Generates fully auditable interest accruals for each billing cycle period.
    Retains all explanatory calculation inputs: opening_balance, rate, convention,
    day_count, day_fraction, interest_amount, fee_amount, and closing_balance.
    """
    merged = schedules_df.merge(loans_df[["loan_id", "interest_rate_annual"]], on="loan_id")
    accruals = []
    accrual_counter = 1

    for _, row in merged.iterrows():
        loan_id = row["loan_id"]
        accrual_date = row["due_date"]
        opening_balance = to_decimal(row["opening_principal"])
        annual_rate = to_decimal(row["interest_rate_annual"])
        convention = row["interest_method"]
        days_in_period = int(row["days_in_period"])

        # Calculate exact fraction
        day_frac, day_cnt = calculate_day_fraction(convention, days_in_period, target_date=accrual_date)

        # Precise interest accrual calculation
        interest_amount = round_bankers(opening_balance * annual_rate * day_frac)
        fee_amount = Decimal("0.00")
        closing_balance = round_bankers(opening_balance + interest_amount)

        accruals.append({
            "accrual_id": f"ACC-{accrual_counter:08d}",
            "loan_id": loan_id,
            "period_number": row["period_number"],
            "accrual_date": accrual_date,
            "start_principal_balance": float(opening_balance),
            "interest_rate_annual": float(annual_rate),
            "interest_method": convention,
            "day_count": day_cnt,
            "day_fraction": float(round(day_frac, 8)),
            "interest_accrual_amount": float(interest_amount),
            "fee_accrual_amount": float(fee_amount),
            "cumulative_unpaid_interest": float(interest_amount),
            "closing_balance": float(closing_balance),
            "is_posted_to_gl": True,
            "created_at": REFERENCE_TIMESTAMP
        })
        accrual_counter += 1

    return pd.DataFrame(accruals)
