"""
FinSight Enterprise — Loan Product Reference Data Generator
Returns conformed loan products table matching Phase 1 schema.
"""

from datetime import datetime, timezone
import pandas as pd
from generation.config import LOAN_PRODUCTS, REFERENCE_TIMESTAMP


def generate_loan_products() -> pd.DataFrame:
    """Generates the authoritative loan products catalog."""
    rows = []
    for code, p in LOAN_PRODUCTS.items():
        rows.append({
            "product_code": p["product_code"],
            "product_name": p["product_name"],
            "product_family": p["product_family"],
            "rate_type": p["rate_type"],
            "interest_method": p["interest_method"],
            "default_amortization": p["default_amortization"],
            "benchmark_index": p["benchmark_index"],
            "base_spread_bps": p["base_spread_bps"],
            "min_term_months": p["min_term_months"],
            "max_term_months": p["max_term_months"],
            "is_active": True,
            "created_at": REFERENCE_TIMESTAMP
        })
    return pd.DataFrame(rows)
