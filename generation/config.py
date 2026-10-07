"""
FinSight Enterprise — Contract Generation Configuration & Product Catalog
Anchors contract generation parameters to real FRED data and Phase 1 core schemas.
"""

from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_FRED_DIR = BASE_DIR / "data" / "raw" / "fred"
OUTPUT_DIR = BASE_DIR / "data" / "generated" / "contracts"

DEFAULT_SEED = 20261006
REFERENCE_TIMESTAMP = datetime(2026, 10, 6, 0, 0, 0, tzinfo=timezone.utc)

# 1. Benchmark Rates Retrieval from Bronze FRED Data
FRED_MATRIX_PATH = RAW_FRED_DIR / "fred_monthly_macro_matrix.parquet"

def get_latest_benchmarks():
    """Reads latest benchmark rates from Bronze FRED Parquet."""
    if FRED_MATRIX_PATH.exists():
        df = pd.read_parquet(FRED_MATRIX_PATH)
        latest_sofr = float(df["SOFR"].dropna().iloc[-1]) / 100.0 if "SOFR" in df.columns else 0.0389
        latest_prime = float(df["DPRIME"].dropna().iloc[-1]) / 100.0 if "DPRIME" in df.columns else 0.0700
        latest_10y = float(df["DGS10"].dropna().iloc[-1]) / 100.0 if "DGS10" in df.columns else 0.0528
    else:
        latest_sofr = 0.038900
        latest_prime = 0.070000
        latest_10y = 0.052800

    return {
        "SOFR": round(latest_sofr, 6),
        "DPRIME": round(latest_prime, 6),
        "DGS10": round(latest_10y, 6)
    }

BENCHMARK_RATES = get_latest_benchmarks()

# 2. Operating Regions
REGIONS = ["NORTHEAST", "MIDWEST", "SOUTH", "WEST"]

# 3. Customer Segments & Risk Profiles
CUSTOMER_SEGMENTS = {
    "COMMERCIAL_CORP": {
        "customer_type": "COMMERCIAL_CORP",
        "segment": "CORPORATE",
        "min_income": 5_000_000.0,
        "max_income": 50_000_000.0,
        "min_credit_score": 680,
        "max_credit_score": 850,
        "eligible_products": ["PROD-COMM-REV", "PROD-COMM-TERM"]
    },
    "COMMERCIAL_SME": {
        "customer_type": "COMMERCIAL_SME",
        "segment": "SMALL_BUSINESS",
        "min_income": 250_000.0,
        "max_income": 4_500_000.0,
        "min_credit_score": 620,
        "max_credit_score": 820,
        "eligible_products": ["PROD-SME-WC"]
    },
    "RETAIL_CONSUMER": {
        "customer_type": "RETAIL_CONSUMER",
        "segment": "PRIME_RETAIL",
        "min_income": 45_000.0,
        "max_income": 250_000.0,
        "min_credit_score": 580,
        "max_credit_score": 840,
        "eligible_products": ["PROD-RET-INST"]
    },
    "RETAIL_MORTGAGE": {
        "customer_type": "RETAIL_MORTGAGE",
        "segment": "PRIME_RETAIL",
        "min_income": 85_000.0,
        "max_income": 450_000.0,
        "min_credit_score": 660,
        "max_credit_score": 850,
        "eligible_products": ["PROD-MORT-30"]
    }
}

# 4. Standard Product Definitions
LOAN_PRODUCTS = {
    "PROD-COMM-REV": {
        "product_code": "PROD-COMM-REV",
        "product_name": "Commercial Revolving Credit Facility",
        "product_family": "COMMERCIAL_LENDING",
        "rate_type": "FLOATING",
        "benchmark_index": "SOFR",
        "base_spread_bps": 275, # 2.75%
        "interest_method": "ACTUAL/360",
        "default_amortization": "INTEREST_ONLY_BALLOON",
        "min_principal": 1_000_000.0,
        "max_principal": 15_000_000.0,
        "min_term_months": 12,
        "max_term_months": 60,
        "default_term_months": 36
    },
    "PROD-COMM-TERM": {
        "product_code": "PROD-COMM-TERM",
        "product_name": "Corporate Term Loan Facility",
        "product_family": "COMMERCIAL_LENDING",
        "rate_type": "FIXED",
        "benchmark_index": None,
        "fixed_contract_rate": 0.065000, # 6.50%
        "base_spread_bps": 0,
        "interest_method": "ACTUAL/360",
        "default_amortization": "EQUAL_INSTALLMENT",
        "min_principal": 500_000.0,
        "max_principal": 10_000_000.0,
        "min_term_months": 12,
        "max_term_months": 120,
        "default_term_months": 60
    },
    "PROD-SME-WC": {
        "product_code": "PROD-SME-WC",
        "product_name": "SME Working Capital Line",
        "product_family": "SME_LENDING",
        "rate_type": "FLOATING",
        "benchmark_index": "DPRIME",
        "base_spread_bps": 225, # 2.25%
        "interest_method": "ACTUAL/360",
        "default_amortization": "FIXED_PRINCIPAL",
        "min_principal": 50_000.0,
        "max_principal": 1_500_000.0,
        "min_term_months": 6,
        "max_term_months": 36,
        "default_term_months": 24
    },
    "PROD-RET-INST": {
        "product_code": "PROD-RET-INST",
        "product_name": "Consumer Fixed Installment Loan",
        "product_family": "CONSUMER_CREDIT",
        "rate_type": "FIXED",
        "benchmark_index": None,
        "fixed_contract_rate": 0.089000, # 8.90%
        "base_spread_bps": 0,
        "interest_method": "ACTUAL/365",
        "default_amortization": "EQUAL_INSTALLMENT",
        "min_principal": 5_000.0,
        "max_principal": 100_000.0,
        "min_term_months": 12,
        "max_term_months": 60,
        "default_term_months": 48
    },
    "PROD-MORT-30": {
        "product_code": "PROD-MORT-30",
        "product_name": "30-Year Residential Fixed Mortgage",
        "product_family": "RESIDENTIAL_MORTGAGE",
        "rate_type": "FIXED",
        "benchmark_index": None,
        "fixed_contract_rate": 0.062500, # 6.25%
        "base_spread_bps": 0,
        "interest_method": "30/360",
        "default_amortization": "EQUAL_INSTALLMENT",
        "min_principal": 100_000.0,
        "max_principal": 1_500_000.0,
        "min_term_months": 120,
        "max_term_months": 360,
        "default_term_months": 360
    }
}
