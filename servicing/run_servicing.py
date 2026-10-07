"""
FinSight Enterprise — Servicing Simulation Orchestrator (Stage 2.3)
Coordinates the 7-stage servicing simulation pipeline:
2.3.1 Schedule Engine
2.3.2 Accrual Engine
2.3.3 Payment Execution
2.3.4 Waterfall Allocation
2.3.5 DPD & Aging Engine
2.3.6 General Ledger Journal Engine
2.3.7 Financial Reconciliation Engine
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from generation.random_state import DeterministicRandomState
from servicing.config import (
    CONTRACTS_DIR,
    OUTPUT_SERVICING_DIR,
    DEFAULT_SEED,
    DEFAULT_SIMULATION_CYCLES,
    REFERENCE_TIMESTAMP
)
from servicing.schedule_engine import generate_payment_schedules
from servicing.accrual_engine import generate_accruals
from servicing.payment_execution import simulate_payments
from servicing.waterfall_engine import process_payment_allocations
from servicing.dpd_engine import compute_portfolio_delinquency
from servicing.gl_engine import generate_gl_journals
from servicing.reconciliation_engine import run_servicing_reconciliation


def execute_servicing_simulation(
    cycles: int = DEFAULT_SIMULATION_CYCLES,
    seed: int = DEFAULT_SEED,
    save: bool = True
):
    print("=" * 80)
    print(f" FinSight Enterprise — Servicing Simulation Pipeline [Cycles={cycles}, Seed={seed}] ")
    print("=" * 80)

    # 1. Load generated contracts
    loans_path = CONTRACTS_DIR / "loans.parquet"
    terms_path = CONTRACTS_DIR / "loan_terms.parquet"

    if not loans_path.exists() or not terms_path.exists():
        raise FileNotFoundError(f"Contract parquets missing in {CONTRACTS_DIR}. Run Stage 2.2 first.")

    loans_df = pd.read_parquet(loans_path)
    terms_df = pd.read_parquet(terms_path)
    print(f"[+] Loaded {len(loans_df):,} master loan contracts and {len(terms_df):,} terms.")

    rng = DeterministicRandomState(seed=seed)

    # 2.3.1 Schedule Engine
    print("\n[*] Step 2.3.1: Generating Contractual Payment Schedules...")
    schedules_df = generate_payment_schedules(loans_df=loans_df, terms_df=terms_df, cycles_to_simulate=cycles)
    print(f"[+] Generated {len(schedules_df):,} scheduled billing periods.")

    # 2.3.2 Accrual Engine
    print("\n[*] Step 2.3.2: Calculating Daily & Period Interest Accruals...")
    accruals_df = generate_accruals(schedules_df=schedules_df, loans_df=loans_df)
    print(f"[+] Computed {len(accruals_df):,} auditable interest accrual entries.")

    # 2.3.3 Payment Execution
    print("\n[*] Step 2.3.3: Simulating Borrower Payment Execution...")
    payments_df, billing_events_df = simulate_payments(schedules_df=schedules_df, rng=rng)
    print(f"[+] Simulated {len(billing_events_df):,} billing events -> {len(payments_df):,} payment transactions.")

    # 2.3.4 Payment Waterfall Allocation
    print("\n[*] Step 2.3.4: Processing Payment Waterfall Hierarchy...")
    allocations_df = process_payment_allocations(
        payments_df=payments_df,
        billing_events_df=billing_events_df,
        schedules_df=schedules_df
    )
    print(f"[+] Executed {len(allocations_df):,} waterfall allocations (Fees -> Interest -> Principal -> Prepayment).")

    # 2.3.5 DPD & Aging Engine
    print("\n[*] Step 2.3.5: Calculating DPD and Delinquency Aging Buckets from Dates...")
    cycle_delinquency_df, updated_loans_df = compute_portfolio_delinquency(
        billing_events_df=billing_events_df,
        loans_df=loans_df,
        allocations_df=allocations_df
    )
    dpd_counts = cycle_delinquency_df["dpd_bucket"].value_counts().to_dict()
    print(f"[+] DPD aging evaluated: {dpd_counts}")

    # 2.3.6 General Ledger Journal Engine
    print("\n[*] Step 2.3.6: Posting Balanced Double-Entry General Ledger Journals...")
    gl_entries_df, gl_lines_df = generate_gl_journals(
        accruals_df=accruals_df,
        billing_events_df=billing_events_df,
        allocations_df=allocations_df,
        payments_df=payments_df
    )
    total_debits = round(gl_lines_df["debit_amount"].sum(), 2)
    total_credits = round(gl_lines_df["credit_amount"].sum(), 2)
    assert total_debits == total_credits, f"GL Unbalanced! Debits {total_debits} != Credits {total_credits}"
    print(f"[+] Posted {len(gl_entries_df):,} journal headers and {len(gl_lines_df):,} detail lines.")
    print(f"    Total Debits: ${total_debits:,.2f} | Total Credits: ${total_credits:,.2f} (BALANCED)")

    # 2.3.7 Financial Reconciliation Engine
    print("\n[*] Step 2.3.7: Running Dual-Path Financial Reconciliation Gates...")
    recon_df = run_servicing_reconciliation(
        schedules_df=schedules_df,
        accruals_df=accruals_df,
        allocations_df=allocations_df,
        gl_lines_df=gl_lines_df
    )
    recon_status_counts = recon_df["status"].value_counts().to_dict()
    print(f"[+] Reconciliation checks: {len(recon_df):,} total checks -> {recon_status_counts}")

    # Verify Stage 2.3 Clean Baseline Acceptance Gates
    pass_count = (recon_df["status"] == "PASS").sum()
    fail_count = (recon_df["status"] == "FAIL").sum()
    assert fail_count == 0, f"Stage 2.3 Clean Baseline violated! Found {fail_count} failed reconciliations."
    print("[+] 100% of financial reconciliation checks PASSED (Zero Defects in Clean Baseline)!")

    # 8. Save Artifacts
    if save:
        OUTPUT_SERVICING_DIR.mkdir(parents=True, exist_ok=True)
        schedules_df.to_parquet(OUTPUT_SERVICING_DIR / "payment_schedules.parquet", index=False)
        accruals_df.to_parquet(OUTPUT_SERVICING_DIR / "interest_accruals.parquet", index=False)
        payments_df.to_parquet(OUTPUT_SERVICING_DIR / "payments.parquet", index=False)
        allocations_df.to_parquet(OUTPUT_SERVICING_DIR / "payment_allocations.parquet", index=False)
        cycle_delinquency_df.to_parquet(OUTPUT_SERVICING_DIR / "delinquency_cycles.parquet", index=False)
        gl_entries_df.to_parquet(OUTPUT_SERVICING_DIR / "accounting_entries.parquet", index=False)
        gl_lines_df.to_parquet(OUTPUT_SERVICING_DIR / "accounting_entry_lines.parquet", index=False)
        recon_df.to_parquet(OUTPUT_SERVICING_DIR / "reconciliation_results.parquet", index=False)

        # Update core.loans with latest outstanding balances and servicing status
        updated_loans_df.to_parquet(OUTPUT_SERVICING_DIR / "updated_loans.parquet", index=False)

        summary = {
            "simulation_timestamp": REFERENCE_TIMESTAMP.isoformat(),
            "random_seed": seed,
            "facilities_serviced": len(loans_df),
            "simulation_cycles": cycles,
            "total_scheduled_periods": len(schedules_df),
            "total_accrual_entries": len(accruals_df),
            "total_payments_executed": len(payments_df),
            "total_payment_volume_usd": float(round(payments_df["payment_amount"].sum(), 2)),
            "total_principal_collected_usd": float(round(allocations_df["principal_amount"].sum() + allocations_df["prepayment_amount"].sum(), 2)),
            "total_interest_collected_usd": float(round(allocations_df["interest_amount"].sum(), 2)),
            "total_fees_collected_usd": float(round(allocations_df["fees_amount"].sum(), 2)),
            "gl_total_debit_usd": total_debits,
            "gl_total_credit_usd": total_credits,
            "gl_balanced": True,
            "reconciliation_checks_total": len(recon_df),
            "reconciliation_pass_rate_pct": float(round((pass_count / len(recon_df)) * 100, 2)),
            "intentional_defects_injected": 0,
            "status": "PASSED"
        }

        with open(OUTPUT_SERVICING_DIR / "servicing_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        print("\n" + "=" * 80)
        print(" SERVICING SIMULATION SUMMARY ")
        print("=" * 80)
        print(f"Facilities Serviced           : {summary['facilities_serviced']:,}")
        print(f"Simulation Cycles             : {summary['simulation_cycles']}")
        print(f"Total Scheduled Periods       : {summary['total_scheduled_periods']:,}")
        print(f"Total Payments Executed       : {summary['total_payments_executed']:,}")
        print(f"Total Payment Volume          : ${summary['total_payment_volume_usd']:,.2f}")
        print(f"Principal Collected           : ${summary['total_principal_collected_usd']:,.2f}")
        print(f"Interest Collected            : ${summary['total_interest_collected_usd']:,.2f}")
        print(f"Fees Collected                : ${summary['total_fees_collected_usd']:,.2f}")
        print(f"GL Double-Entry Tied-Out      : BALANCED (${total_debits:,.2f})")
        print(f"Reconciliation Pass Rate      : {summary['reconciliation_pass_rate_pct']}% ({pass_count:,} / {len(recon_df):,})")
        print(f"Intentional Defects Injected  : {summary['intentional_defects_injected']} (Stage 2.3 Clean Baseline)")
        print("=" * 80)

    return (
        schedules_df,
        accruals_df,
        payments_df,
        allocations_df,
        cycle_delinquency_df,
        gl_entries_df,
        gl_lines_df,
        recon_df,
        updated_loans_df
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight Enterprise Servicing Simulation")
    parser.add_argument("--cycles", type=int, default=DEFAULT_SIMULATION_CYCLES, help="Number of cycles to simulate")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help=f"Random seed (default: {DEFAULT_SEED})")
    args = parser.parse_args()

    execute_servicing_simulation(cycles=args.cycles, seed=args.seed)
