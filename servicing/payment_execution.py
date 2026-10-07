"""
FinSight Enterprise — Payment Execution Simulation Engine (Stage 2.3.3)
Simulates realistic borrower servicing behaviors (ON_TIME, LATE, PARTIAL, MISSED, EARLY).
Produces finance.payments records with deterministic tracking.
"""

from decimal import Decimal, ROUND_HALF_EVEN
from datetime import timedelta
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers
from generation.random_state import DeterministicRandomState
from servicing.config import SERVICING_BEHAVIORS, REFERENCE_TIMESTAMP


def simulate_payments(
    schedules_df: pd.DataFrame,
    rng: DeterministicRandomState
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Simulates servicing payment receipts across the portfolio.
    Returns:
    - payments_df: Executed payment records (matching finance.payments)
    - billing_events_df: Metadata detailing behavior, due dates, payment dates, and fees assessed.
    """
    behavior_names = [b[0] for b in SERVICING_BEHAVIORS]
    behavior_weights = [b[1] for b in SERVICING_BEHAVIORS]

    payments = []
    billing_events = []
    payment_counter = 1

    payment_methods = ["ACH", "WIRE", "INTERNAL_TRANSFER", "LOCKBOX"]
    method_weights = [0.70, 0.15, 0.10, 0.05]

    for _, sched in schedules_df.iterrows():
        loan_id = sched["loan_id"]
        period_num = int(sched["period_number"])
        due_date = sched["due_date"]
        sched_principal = to_decimal(sched["scheduled_principal"])
        sched_interest = to_decimal(sched["scheduled_interest"])
        base_due = to_decimal(sched["total_amount_due"])

        # Determine servicing behavior deterministically
        behavior = rng.choices(behavior_names, weights=behavior_weights)[0]

        fee_assessed = Decimal("0.00")
        prepayment_amount = Decimal("0.00")

        if behavior == "ON_TIME":
            payment_date = due_date
            payment_amount = base_due
        elif behavior == "LATE":
            days_late = rng.randint(5, 45)
            payment_date = due_date + timedelta(days=days_late)
            # Contractual late fee: 5% of monthly due, min $25
            fee_assessed = max(Decimal("25.00"), round_bankers(base_due * Decimal("0.05")))
            payment_amount = base_due + fee_assessed
        elif behavior == "PARTIAL":
            payment_date = due_date
            ratio = Decimal(str(round(rng.uniform(0.50, 0.85), 2)))
            payment_amount = round_bankers(base_due * ratio)
        elif behavior == "EARLY":
            days_early = rng.randint(2, 10)
            payment_date = due_date - timedelta(days=days_early)
            prepayment_ratio = Decimal(str(round(rng.uniform(0.10, 0.25), 2)))
            prepayment_amount = round_bankers(base_due * prepayment_ratio)
            payment_amount = base_due + prepayment_amount
        elif behavior == "MISSED":
            payment_date = None
            payment_amount = Decimal("0.00")
            fee_assessed = max(Decimal("25.00"), round_bankers(base_due * Decimal("0.05")))

        # Record billing event
        billing_events.append({
            "schedule_id": sched["schedule_id"],
            "loan_id": loan_id,
            "period_number": period_num,
            "behavior": behavior,
            "due_date": due_date,
            "payment_date": payment_date,
            "scheduled_principal_due": float(sched_principal),
            "scheduled_interest_due": float(sched_interest),
            "fee_assessed": float(fee_assessed),
            "prepayment_intended": float(prepayment_amount),
            "total_due_with_fees": float(base_due + fee_assessed),
            "amount_paid": float(payment_amount)
        })

        # If payment occurred, create finance.payments row
        if payment_amount > Decimal("0.00"):
            payment_id = f"PMT-{payment_counter:08d}"
            method = rng.choices(payment_methods, weights=method_weights)[0]
            ref_num = f"REF-{payment_id}-{loan_id}"

            payments.append({
                "payment_id": payment_id,
                "loan_id": loan_id,
                "period_number": period_num,
                "schedule_id": sched["schedule_id"],
                "payment_date": payment_date,
                "payment_amount": float(payment_amount),
                "payment_method": method,
                "status": "PROCESSED",
                "reference_number": ref_num,
                "created_at": REFERENCE_TIMESTAMP
            })
            payment_counter += 1

    return pd.DataFrame(payments), pd.DataFrame(billing_events)
