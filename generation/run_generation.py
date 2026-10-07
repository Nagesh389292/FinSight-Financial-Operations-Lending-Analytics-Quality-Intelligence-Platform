"""
FinSight Enterprise — Contract Generation Orchestrator (Phase 2, Stage 2.2)
Orchestrates deterministic generation of customers, loan facilities, and loan terms.
Runs validation gates before saving outputs to data/generated/contracts/.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generation.config import DEFAULT_SEED, OUTPUT_DIR
from generation.random_state import DeterministicRandomState
from generation.customer_generator import generate_customers
from generation.product_generator import generate_loan_products
from generation.loan_generator import generate_loans
from generation.loan_term_generator import generate_loan_terms
from generation.validators import validate_contracts, ContractValidationError


def execute_generation(loan_count: int = 100, seed: int = DEFAULT_SEED, save: bool = True):
    print("=" * 75)
    print(f" FinSight Enterprise — Contract Generation Pipeline [Count={loan_count:,}, Seed={seed}] ")
    print("=" * 75)

    rng = DeterministicRandomState(seed=seed)

    # 1. Generate Products
    products_df = generate_loan_products()
    print(f"[+] Loaded {len(products_df)} standard loan products.")

    # 2. Generate Customers (1:1 with loan count for 100-loan batch, or proportionate)
    cust_count = loan_count
    customers_df = generate_customers(count=cust_count, rng=rng)
    print(f"[+] Generated {len(customers_df)} deterministic borrower profiles.")

    # 3. Generate Loans
    loans_df = generate_loans(customers_df=customers_df, count=loan_count, rng=rng)
    print(f"[+] Generated {len(loans_df)} master loan facilities.")

    # 4. Generate Terms
    terms_df = generate_loan_terms(loans_df=loans_df)
    print(f"[+] Generated {len(terms_df)} detailed contractual loan terms.")

    # 5. Run Validation Gates
    print("\n[*] Running Automated Contract Validation Gates...")
    is_valid, errors = validate_contracts(
        customers_df=customers_df,
        products_df=products_df,
        loans_df=loans_df,
        terms_df=terms_df
    )

    if not is_valid:
        print("[!] CONTRACT VALIDATION GATES FAILED:")
        for err in errors:
            print(f"    - {err}")
        raise ContractValidationError(f"Validation failed with {len(errors)} errors.")

    print("[+] All validation gates PASSED cleanly (Referential integrity, Financial bounds, Rate logic)!")

    # 6. Save Artifacts if requested
    if save:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cust_path = OUTPUT_DIR / "customers.parquet"
        loans_path = OUTPUT_DIR / "loans.parquet"
        terms_path = OUTPUT_DIR / "loan_terms.parquet"

        customers_df.to_parquet(cust_path, index=False)
        loans_df.to_parquet(loans_path, index=False)
        terms_df.to_parquet(terms_path, index=False)

        summary = {
            "generation_timestamp": datetime.now(timezone.utc).isoformat(),
            "random_seed": seed,
            "loan_count": loan_count,
            "customer_count": len(customers_df),
            "product_count": len(products_df),
            "floating_loans_count": int((terms_df["rate_type"] == "FLOATING").sum()),
            "fixed_loans_count": int((terms_df["rate_type"] == "FIXED").sum()),
            "total_portfolio_principal_usd": float(loans_df["principal_original"].sum()),
            "avg_interest_rate_pct": float(round(loans_df["interest_rate_annual"].mean() * 100, 4)),
            "validation_status": "PASSED",
            "injected_defects_count": 0 # Explicitly 0 in Stage 2.2 clean contracts
        }

        with open(OUTPUT_DIR / "generation_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 75)
        print(" CONTRACT GENERATION SUMMARY ")
        print("=" * 75)
        print(f"Total Loan Contracts         : {summary['loan_count']:,}")
        print(f"Floating Rate Contracts      : {summary['floating_loans_count']:,}")
        print(f"Fixed Rate Contracts         : {summary['fixed_loans_count']:,}")
        print(f"Total Portfolio Value        : ${summary['total_portfolio_principal_usd']:,.2f}")
        print(f"Average Annual Interest Rate : {summary['avg_interest_rate_pct']:.2f}%")
        print(f"Injected Defects             : {summary['injected_defects_count']} (Stage 2.2 Clean Contracts)")
        print(f"Validation Status            : {summary['validation_status']}")
        print("=" * 75)

    return customers_df, products_df, loans_df, terms_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight Enterprise Contract Generator")
    parser.add_argument("--count", type=int, default=100, help="Number of loans to generate (default: 100)")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Random seed (default: {DEFAULT_SEED})")
    args = parser.parse_args()

    execute_generation(loan_count=args.count, seed=args.seed)
