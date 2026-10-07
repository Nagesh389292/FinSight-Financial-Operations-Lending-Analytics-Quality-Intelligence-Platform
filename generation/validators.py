"""
FinSight Enterprise — Contract Generation Validation Gatekeeper
Enforces referential integrity, financial boundaries, and rate/day-count logic.
"""

from typing import Tuple, List
import pandas as pd


class ContractValidationError(Exception):
    """Raised when generated contracts breach financial or referential rules."""
    pass


def validate_contracts(
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    terms_df: pd.DataFrame
) -> Tuple[bool, List[str]]:
    """
    Executes comprehensive validation suite across generated tables.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    # 1. Referential Integrity Checks
    valid_customer_ids = set(customers_df["customer_id"])
    invalid_cust_fks = set(loans_df["customer_id"]) - valid_customer_ids
    if invalid_cust_fks:
        errors.append(f"Referential Integrity Failure: {len(invalid_cust_fks)} loans reference non-existent customers.")

    valid_product_codes = set(products_df["product_code"])
    invalid_prod_fks = set(loans_df["product_code"]) - valid_product_codes
    if invalid_prod_fks:
        errors.append(f"Referential Integrity Failure: {len(invalid_prod_fks)} loans reference non-existent products.")

    valid_loan_ids = set(loans_df["loan_id"])
    invalid_term_fks = set(terms_df["loan_id"]) - valid_loan_ids
    if invalid_term_fks:
        errors.append(f"Referential Integrity Failure: {len(invalid_term_fks)} terms reference non-existent loans.")

    # 1:1 Relationship check for loan terms
    if len(terms_df) != len(loans_df) or terms_df["loan_id"].duplicated().any():
        errors.append("Loan Terms 1:1 Cardinality Failure: Mismatched count or duplicate loan_id in terms.")

    # 2. Financial Constraint Checks
    if (loans_df["principal_original"] <= 0).any():
        errors.append("Financial Constraint Failure: Detected non-positive original principal.")

    if (loans_df["principal_outstanding"] < 0).any():
        errors.append("Financial Constraint Failure: Detected negative outstanding principal.")

    if (loans_df["interest_rate_annual"] < 0).any():
        errors.append("Financial Constraint Failure: Detected negative annual interest rate.")

    if (loans_df["term_months"] <= 0).any():
        errors.append("Financial Constraint Failure: Detected non-positive loan term.")

    invalid_dates = loans_df[loans_df["maturity_date"] <= loans_df["start_date"]]
    if not invalid_dates.empty:
        errors.append(f"Date Boundary Failure: {len(invalid_dates)} loans have maturity_date <= start_date.")

    # 3. Rate Logic Checks
    fixed_with_benchmark = terms_df[(terms_df["rate_type"] == "FIXED") & (terms_df["benchmark_index"].notna())]
    if not fixed_with_benchmark.empty:
        errors.append(f"Rate Logic Failure: {len(fixed_with_benchmark)} FIXED loans have benchmark_index populated.")

    floating_without_benchmark = terms_df[(terms_df["rate_type"] == "FLOATING") & (terms_df["benchmark_index"].isna())]
    if not floating_without_benchmark.empty:
        errors.append(f"Rate Logic Failure: {len(floating_without_benchmark)} FLOATING loans have missing benchmark_index.")

    # 4. Day-Count Logic Checks
    valid_methods = {"ACTUAL/360", "ACTUAL/365", "30/360"}
    invalid_day_counts = set(terms_df["interest_method"]) - valid_methods
    if invalid_day_counts:
        errors.append(f"Day-Count Logic Failure: Detected unsupported conventions: {invalid_day_counts}")

    # 5. Customer Underwriting Checks
    invalid_credit_scores = customers_df[(customers_df["credit_score"] < 300) | (customers_df["credit_score"] > 850)]
    if not invalid_credit_scores.empty:
        errors.append(f"Underwriting Failure: {len(invalid_credit_scores)} customers have credit scores outside [300, 850].")

    if (customers_df["annual_income"] <= 0).any():
        errors.append("Underwriting Failure: Detected non-positive customer annual income.")

    if (customers_df["debt_to_income_ratio"] < 0).any():
        errors.append("Underwriting Failure: Detected negative debt-to-income ratio.")

    is_valid = len(errors) == 0
    return is_valid, errors
