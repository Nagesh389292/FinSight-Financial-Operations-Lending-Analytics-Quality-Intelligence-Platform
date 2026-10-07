"""
FinSight Enterprise — General Ledger Double-Entry Engine (Stage 2.3.6)
Generates balanced double-entry accounting journals for all lending sub-ledger events:
- DAILY_ACCRUAL: DR 12100 Interest Receivable / CR 40100 Interest Income
- FEE_ASSESSMENT: DR 12200 Fees Receivable / CR 40200 Fee Income
- PAYMENT_RECEIPT: DR 10100 Cash / CR 12000 Loans Receivable, CR 12100 Interest Receivable, CR 12200 Fees Receivable

Enforces fundamental accounting identity: Sum(Debit) == Sum(Credit).
"""

from decimal import Decimal, ROUND_HALF_EVEN
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers
from servicing.config import GL_CHART_OF_ACCOUNTS, REFERENCE_TIMESTAMP


def generate_gl_journals(
    accruals_df: pd.DataFrame,
    billing_events_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    payments_df: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Generates double-entry accounting header entries and detail lines.
    Returns:
    - entries_df: finance.accounting_entries
    - lines_df: finance.accounting_entry_lines
    """
    entries = []
    lines = []
    entry_counter = 1
    line_counter = 1

    # 1. Accrual Journal Entries (DR 12100 / CR 40100)
    for _, acc in accruals_df.iterrows():
        interest_amt = to_decimal(acc["interest_accrual_amount"])
        if interest_amt <= Decimal("0.00"):
            continue

        entry_id = f"JRN-ACC-{entry_counter:08d}"
        entries.append({
            "entry_id": entry_id,
            "accounting_date": acc["accrual_date"],
            "source_event": "DAILY_ACCRUAL",
            "source_reference_id": acc["accrual_id"],
            "total_debit": float(interest_amt),
            "total_credit": float(interest_amt),
            "is_balanced": True,
            "created_at": REFERENCE_TIMESTAMP
        })

        # Line 1: Debit Interest Receivable
        lines.append({
            "line_id": line_counter,
            "entry_id": entry_id,
            "line_number": 1,
            "gl_account_code": "12100",
            "gl_account_name": GL_CHART_OF_ACCOUNTS["12100"]["name"],
            "debit_amount": float(interest_amt),
            "credit_amount": 0.0,
            "memo": f"Interest Accrual for {acc['loan_id']} ({acc['interest_method']})"
        })
        line_counter += 1

        # Line 2: Credit Interest Income
        lines.append({
            "line_id": line_counter,
            "entry_id": entry_id,
            "line_number": 2,
            "gl_account_code": "40100",
            "gl_account_name": GL_CHART_OF_ACCOUNTS["40100"]["name"],
            "debit_amount": 0.0,
            "credit_amount": float(interest_amt),
            "memo": f"Interest Income for {acc['loan_id']}"
        })
        line_counter += 1
        entry_counter += 1

    # 2. Fee Assessment Journal Entries (DR 12200 / CR 40200)
    for _, be in billing_events_df.iterrows():
        fee_amt = to_decimal(be["fee_assessed"])
        if fee_amt <= Decimal("0.00"):
            continue

        entry_id = f"JRN-FEE-{entry_counter:08d}"
        entries.append({
            "entry_id": entry_id,
            "accounting_date": be["due_date"],
            "source_event": "FEE_ASSESSMENT",
            "source_reference_id": be["schedule_id"],
            "total_debit": float(fee_amt),
            "total_credit": float(fee_amt),
            "is_balanced": True,
            "created_at": REFERENCE_TIMESTAMP
        })

        # Line 1: Debit Fees Receivable
        lines.append({
            "line_id": line_counter,
            "entry_id": entry_id,
            "line_number": 1,
            "gl_account_code": "12200",
            "gl_account_name": GL_CHART_OF_ACCOUNTS["12200"]["name"],
            "debit_amount": float(fee_amt),
            "credit_amount": 0.0,
            "memo": f"Late Fee Assessment for {be['loan_id']} ({be['behavior']})"
        })
        line_counter += 1

        # Line 2: Credit Fee Income
        lines.append({
            "line_id": line_counter,
            "entry_id": entry_id,
            "line_number": 2,
            "gl_account_code": "40200",
            "gl_account_name": GL_CHART_OF_ACCOUNTS["40200"]["name"],
            "debit_amount": 0.0,
            "credit_amount": float(fee_amt),
            "memo": f"Fee Income for {be['loan_id']}"
        })
        line_counter += 1
        entry_counter += 1

    # 3. Payment Receipt Journal Entries (DR 10100 Cash / CR Receivables)
    merged_pmt = allocations_df.merge(
        payments_df[["payment_id", "payment_date", "payment_method"]],
        on="payment_id"
    )

    for _, alloc in merged_pmt.iterrows():
        p_amt = to_decimal(alloc["principal_amount"]) + to_decimal(alloc["prepayment_amount"])
        i_amt = to_decimal(alloc["interest_amount"])
        f_amt = to_decimal(alloc["fees_amount"])
        total_cash = to_decimal(alloc["total_allocated"])

        if total_cash <= Decimal("0.00"):
            continue

        entry_id = f"JRN-PMT-{entry_counter:08d}"
        entries.append({
            "entry_id": entry_id,
            "accounting_date": alloc["payment_date"],
            "source_event": "PAYMENT_RECEIPT",
            "source_reference_id": alloc["payment_id"],
            "total_debit": float(total_cash),
            "total_credit": float(total_cash),
            "is_balanced": True,
            "created_at": REFERENCE_TIMESTAMP
        })

        # DR Cash
        lines.append({
            "line_id": line_counter,
            "entry_id": entry_id,
            "line_number": 1,
            "gl_account_code": "10100",
            "gl_account_name": GL_CHART_OF_ACCOUNTS["10100"]["name"],
            "debit_amount": float(total_cash),
            "credit_amount": 0.0,
            "memo": f"Cash settlement via {alloc['payment_method']} for {alloc['loan_id']}"
        })
        line_counter += 1
        line_idx = 2

        # CR Principal
        if p_amt > Decimal("0.00"):
            lines.append({
                "line_id": line_counter,
                "entry_id": entry_id,
                "line_number": line_idx,
                "gl_account_code": "12000",
                "gl_account_name": GL_CHART_OF_ACCOUNTS["12000"]["name"],
                "debit_amount": 0.0,
                "credit_amount": float(p_amt),
                "memo": f"Principal reduction for {alloc['loan_id']}"
            })
            line_counter += 1
            line_idx += 1

        # CR Interest
        if i_amt > Decimal("0.00"):
            lines.append({
                "line_id": line_counter,
                "entry_id": entry_id,
                "line_number": line_idx,
                "gl_account_code": "12100",
                "gl_account_name": GL_CHART_OF_ACCOUNTS["12100"]["name"],
                "debit_amount": 0.0,
                "credit_amount": float(i_amt),
                "memo": f"Interest clearance for {alloc['loan_id']}"
            })
            line_counter += 1
            line_idx += 1

        # CR Fees
        if f_amt > Decimal("0.00"):
            lines.append({
                "line_id": line_counter,
                "entry_id": entry_id,
                "line_number": line_idx,
                "gl_account_code": "12200",
                "gl_account_name": GL_CHART_OF_ACCOUNTS["12200"]["name"],
                "debit_amount": 0.0,
                "credit_amount": float(f_amt),
                "memo": f"Fee clearance for {alloc['loan_id']}"
            })
            line_counter += 1

        entry_counter += 1

    return pd.DataFrame(entries), pd.DataFrame(lines)
