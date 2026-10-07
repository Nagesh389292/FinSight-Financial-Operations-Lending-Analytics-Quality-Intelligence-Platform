"""
FinSight Enterprise — Deterministic Loan Contract Generator
Generates clean loan facilities anchored to real FRED benchmarks and borrower profiles.
"""

from datetime import date, timedelta, datetime, timezone
import pandas as pd
from generation.config import LOAN_PRODUCTS, CUSTOMER_SEGMENTS, BENCHMARK_RATES, REFERENCE_TIMESTAMP
from generation.random_state import DeterministicRandomState


def generate_loans(customers_df: pd.DataFrame, count: int, rng: DeterministicRandomState) -> pd.DataFrame:
    """Generates `count` clean loan contract facilities."""
    loans = []
    base_start_date = date(2022, 1, 15)

    for i in range(1, count + 1):
        loan_id = f"LOAN-{i:06d}"
        
        # Select customer in round-robin / deterministic fashion
        cust = customers_df.iloc[(i - 1) % len(customers_df)]
        cust_type = cust["customer_type"]
        seg_spec = CUSTOMER_SEGMENTS[cust_type]

        # Select compatible product
        prod_code = rng.choice(seg_spec["eligible_products"])
        prod_spec = LOAN_PRODUCTS[prod_code]

        # Principal size: scaled realistically within product bounds
        min_p = prod_spec["min_principal"]
        max_p = prod_spec["max_principal"]
        principal = round(rng.uniform(min_p, max_p), 2)

        # Interest Rate Calculation:
        # Floating: Benchmark (SOFR/Prime) + Contractual Margin
        # Fixed: Fixed Contract Rate (+ risk margin if Subprime)
        risk_adjustment = 0.005000 if cust["risk_category"] == "SUBPRIME" else 0.000000

        if prod_spec["rate_type"] == "FLOATING":
            benchmark_name = prod_spec["benchmark_index"]
            benchmark_rate = BENCHMARK_RATES.get(benchmark_name, 0.040000)
            margin_spread = prod_spec["base_spread_bps"] / 10000.0
            interest_rate = round(benchmark_rate + margin_spread + risk_adjustment, 6)
        else:
            fixed_base = prod_spec["fixed_contract_rate"]
            interest_rate = round(fixed_base + risk_adjustment, 6)

        # Term and Dates
        term_months = prod_spec["default_term_months"]
        start_offset_days = rng.randint(0, 720) # Originated between Jan 2022 and Dec 2023
        start_date = base_start_date + timedelta(days=start_offset_days)
        # Approximate maturity date
        maturity_date = start_date + timedelta(days=int(term_months * 30.4375))

        loans.append({
            "loan_id": loan_id,
            "customer_id": cust["customer_id"],
            "product_code": prod_code,
            "status": "ACTIVE",
            "principal_original": principal,
            "principal_outstanding": principal,
            "interest_rate_annual": interest_rate,
            "term_months": term_months,
            "start_date": start_date,
            "maturity_date": maturity_date,
            "days_past_due": 0,
            "servicing_status": "CURRENT",
            "created_at": REFERENCE_TIMESTAMP,
            "updated_at": REFERENCE_TIMESTAMP
        })

    return pd.DataFrame(loans)
