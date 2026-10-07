"""
FinSight Enterprise — Loan Terms Generator
Generates detailed contract terms for each master loan facility.
"""

from datetime import datetime, timezone
import pandas as pd
from generation.config import LOAN_PRODUCTS, REFERENCE_TIMESTAMP


def generate_loan_terms(loans_df: pd.DataFrame) -> pd.DataFrame:
    """Generates 1:1 contractual loan terms matching product specifications."""
    terms = []

    for _, loan in loans_df.iterrows():
        prod = LOAN_PRODUCTS[loan["product_code"]]
        term_id = f"TERM-{loan['loan_id']}"

        terms.append({
            "term_id": term_id,
            "loan_id": loan["loan_id"],
            "rate_type": prod["rate_type"],
            "interest_method": prod["interest_method"],
            "amortization_schedule": prod["default_amortization"],
            "benchmark_index": prod["benchmark_index"],
            "margin_spread_bps": prod["base_spread_bps"],
            "payment_frequency": "MONTHLY",
            "grace_period_days": 15,
            "late_fee_rate_pct": 0.0500,
            "effective_date": loan["start_date"],
            "created_at": REFERENCE_TIMESTAMP
        })

    return pd.DataFrame(terms)
