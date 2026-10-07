"""
FinSight Enterprise — Contract Generation & Validation Gate Tests (Phase 2, Stage 2.2)
Validates referential integrity, financial constraints, rate logic, day-count logic,
and 100% deterministic reproducibility across generation runs.
"""

import pytest
import pandas as pd
from generation.run_generation import execute_generation
from generation.validators import validate_contracts


@pytest.fixture(scope="module")
def generated_100_batch():
    """Generates a standard 100-contract validation batch."""
    return execute_generation(loan_count=100, seed=20261006, save=False)


def test_referential_integrity(generated_100_batch):
    """Every loan must reference a valid customer and product; every term must reference a valid loan."""
    customers_df, products_df, loans_df, terms_df = generated_100_batch

    assert len(loans_df) == 100
    assert len(terms_df) == 100

    # Foreign key checks
    assert loans_df["customer_id"].isin(customers_df["customer_id"]).all()
    assert loans_df["product_code"].isin(products_df["product_code"]).all()
    assert terms_df["loan_id"].isin(loans_df["loan_id"]).all()

    # 1:1 Cardinality check
    assert terms_df["loan_id"].nunique() == 100


def test_financial_constraints(generated_100_batch):
    """Validates positive principal, non-negative rate, positive term, and valid dates."""
    _, _, loans_df, terms_df = generated_100_batch

    assert (loans_df["principal_original"] > 0).all()
    assert (loans_df["principal_outstanding"] == loans_df["principal_original"]).all()
    assert (loans_df["interest_rate_annual"] > 0.0).all()
    assert (loans_df["term_months"] > 0).all()
    assert (loans_df["maturity_date"] > loans_df["start_date"]).all()


def test_rate_logic_consistency(generated_100_batch):
    """FIXED loans must have benchmark IS NULL; FLOATING loans must have benchmark IS NOT NULL."""
    _, _, loans_df, terms_df = generated_100_batch

    floating_terms = terms_df[terms_df["rate_type"] == "FLOATING"]
    fixed_terms = terms_df[terms_df["rate_type"] == "FIXED"]

    assert len(floating_terms) > 0, "Expected floating-rate contracts in sample"
    assert len(fixed_terms) > 0, "Expected fixed-rate contracts in sample"

    # FLOATING checks
    assert floating_terms["benchmark_index"].notna().all()
    assert floating_terms["benchmark_index"].isin(["SOFR", "DPRIME"]).all()

    # FIXED checks
    assert fixed_terms["benchmark_index"].isna().all()


def test_day_count_convention_logic(generated_100_batch):
    """Validates supported international day-count conventions."""
    _, _, _, terms_df = generated_100_batch

    allowed_methods = {"ACTUAL/360", "ACTUAL/365", "30/360"}
    actual_methods = set(terms_df["interest_method"].unique())

    assert actual_methods.issubset(allowed_methods)
    assert len(actual_methods) >= 2, "Expected multiple day-count conventions in generated portfolio"


def test_clean_contracts_zero_defects(generated_100_batch):
    """Stage 2.2 contracts must be 100% clean (zero defects, zero delinquency)."""
    _, _, loans_df, _ = generated_100_batch

    assert (loans_df["days_past_due"] == 0).all()
    assert (loans_df["servicing_status"] == "CURRENT").all()
    assert (loans_df["status"] == "ACTIVE").all()


def test_generation_reproducibility():
    """
    Critical Engineering Test:
    Running generation twice with the same seed must produce exact bit-for-bit identical DataFrames.
    """
    seed = 20261006

    # Run A
    cust_a, prod_a, loans_a, terms_a = execute_generation(loan_count=100, seed=seed, save=False)

    # Run B
    cust_b, prod_b, loans_b, terms_b = execute_generation(loan_count=100, seed=seed, save=False)

    # Exact bit-for-bit comparison across all entities (including deterministic timestamps)
    pd.testing.assert_frame_equal(cust_a, cust_b)
    pd.testing.assert_frame_equal(prod_a, prod_b)
    pd.testing.assert_frame_equal(loans_a, loans_b)
    pd.testing.assert_frame_equal(terms_a, terms_b)


def test_validation_gatekeeper_catches_invalid_contracts():
    """Validates that ContractValidationError is raised if data integrity is deliberately violated."""
    cust, prod, loans, terms = execute_generation(loan_count=20, seed=999, save=False)

    # Inject an intentional corruption on a copy: negative principal
    corrupted_loans = loans.copy()
    corrupted_loans.loc[0, "principal_original"] = -50000.0

    is_valid, errors = validate_contracts(cust, prod, corrupted_loans, terms)
    assert is_valid is False
    assert any("principal" in e.lower() for e in errors)


def test_saved_contracts_parquet_files_integrity():
    """Validates that saved parquet contract files exist on disk and meet production scale (>= 2,500)."""
    from generation.config import OUTPUT_DIR

    cust_path = OUTPUT_DIR / "customers.parquet"
    loans_path = OUTPUT_DIR / "loans.parquet"
    terms_path = OUTPUT_DIR / "loan_terms.parquet"

    assert cust_path.exists(), "customers.parquet missing"
    assert loans_path.exists(), "loans.parquet missing"
    assert terms_path.exists(), "loan_terms.parquet missing"

    df_cust = pd.read_parquet(cust_path)
    df_loans = pd.read_parquet(loans_path)
    df_terms = pd.read_parquet(terms_path)

    assert len(df_loans) >= 2500, f"Expected at least 2,500 loans, found {len(df_loans)}"
    assert len(df_cust) >= 2500, f"Expected at least 2,500 customers, found {len(df_cust)}"
    assert len(df_terms) >= 2500, f"Expected at least 2,500 terms, found {len(df_terms)}"
    assert (df_loans["days_past_due"] == 0).all()
    assert (df_loans["servicing_status"] == "CURRENT").all()
