"""
FinSight Enterprise — DPD & Delinquency Engine (Stage 2.3.5)
Calculates Days Past Due (DPD) strictly from dates (Due Date vs Payment Date / As-Of Date).
Assigns standard banking delinquency aging buckets and updates loan servicing statuses.
"""

from datetime import date
import pandas as pd
from servicing.config import DPD_BUCKETS, AS_OF_DATE


def calculate_dpd_from_dates(due_date: date, payment_date: date | None, as_of_date: date = AS_OF_DATE) -> int:
    """
    Calculates Days Past Due strictly from date arithmetic.
    - If payment occurred: max(0, (payment_date - due_date).days)
    - If missed / unpaid: max(0, (as_of_date - due_date).days) if as_of_date > due_date else 0
    """
    if payment_date is not None:
        delta = (payment_date - due_date).days
        return max(0, delta)
    else:
        # Unpaid as of evaluation date
        delta = (as_of_date - due_date).days
        return max(0, delta)


def classify_dpd_bucket(dpd: int) -> tuple[str, str, str]:
    """
    Maps DPD to (bucket_name, servicing_status, loan_status).
    """
    if dpd == 0:
        return "CURRENT", "CURRENT", "ACTIVE"
    elif 1 <= dpd <= 29:
        return "BUCKET_1", "GRACE_PERIOD", "ACTIVE"
    elif 30 <= dpd <= 59:
        return "BUCKET_2", "DELINQUENT_30", "DELINQUENT"
    elif 60 <= dpd <= 89:
        return "BUCKET_3", "DELINQUENT_60", "DELINQUENT"
    else:
        return "DEFAULT", "DEFAULT_90_PLUS", "DEFAULT_CHARGED_OFF"


def compute_portfolio_delinquency(
    billing_events_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    as_of_date: date = AS_OF_DATE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Evaluates DPD for every billing cycle and computes the latest servicing status
    and remaining balance for each master loan facility.
    Returns:
    - cycle_delinquency_df: DPD per loan per billing cycle
    - updated_loans_df: Updated core.loans with days_past_due, servicing_status, status, and principal_outstanding
    """
    cycle_records = []

    for _, row in billing_events_df.iterrows():
        loan_id = row["loan_id"]
        period_num = row["period_number"]
        due_date = row["due_date"]
        pmt_date = row["payment_date"]

        dpd = calculate_dpd_from_dates(due_date, pmt_date, as_of_date=as_of_date)
        bucket, servicing_status, loan_status = classify_dpd_bucket(dpd)

        cycle_records.append({
            "loan_id": loan_id,
            "period_number": period_num,
            "due_date": due_date,
            "payment_date": pmt_date,
            "days_past_due": dpd,
            "dpd_bucket": bucket,
            "servicing_status": servicing_status,
            "loan_status": loan_status
        })

    cycle_df = pd.DataFrame(cycle_records)

    # Get latest period per loan
    latest_per_loan = cycle_df.sort_values(["loan_id", "period_number"]).groupby("loan_id").last().reset_index()

    # Get latest closing principal balance per loan from allocations
    if not allocations_df.empty:
        latest_bal = allocations_df.sort_values(["loan_id", "period_number"]).groupby("loan_id")["closing_principal_balance"].last().reset_index()
    else:
        latest_bal = pd.DataFrame(columns=["loan_id", "closing_principal_balance"])

    # Update loans_df
    updated_loans = loans_df.copy()
    updated_loans = updated_loans.drop(columns=["days_past_due", "servicing_status", "status"], errors="ignore")
    updated_loans = updated_loans.merge(
        latest_per_loan[["loan_id", "days_past_due", "servicing_status", "loan_status"]],
        on="loan_id",
        how="left"
    )
    updated_loans["status"] = updated_loans["loan_status"]
    updated_loans.drop(columns=["loan_status"], inplace=True)

    if not latest_bal.empty:
        updated_loans = updated_loans.merge(latest_bal, on="loan_id", how="left")
        updated_loans["principal_outstanding"] = updated_loans["closing_principal_balance"].fillna(updated_loans["principal_outstanding"])
        updated_loans.drop(columns=["closing_principal_balance"], inplace=True)

    return cycle_df, updated_loans
