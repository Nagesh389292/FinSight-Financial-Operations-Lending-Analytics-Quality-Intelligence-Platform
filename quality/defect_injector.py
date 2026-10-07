"""
FinSight Enterprise — Controlled Defect Injection Engine (Stage 2.4)
Programmatically injects deterministic calculation defects into a cloned Scenario B:
1. DAY_COUNT_MISMATCH (Actual/360 denominator applied to Actual/365 contracts)
2. ROUNDING_TRUNCATION (Raw truncation introducing multi-cent drift)
3. WATERFALL_ORDERING (Priority reversal: Principal allocated before fees/interest)
4. LEAP_YEAR_BLINDNESS (Drops leap day in Feb 2024 accruals)
"""

from decimal import Decimal
import pandas as pd
from api.app.services.math_truth import to_decimal, round_bankers
from generation.random_state import DeterministicRandomState
from quality.config import DEFAULT_SEED, DEFECT_TAXONOMY


def inject_controlled_defects(
    accruals_df: pd.DataFrame,
    allocations_df: pd.DataFrame,
    schedules_df: pd.DataFrame,
    seed: int = DEFAULT_SEED,
    target_count_per_defect: int = 150
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Clones clean baseline data and injects controlled defects across 4 defined classes.
    Returns:
    - injected_accruals_df: Accruals containing day-count, rounding, and leap-year corruptions
    - injected_allocations_df: Allocations containing waterfall ordering reversals
    - injection_manifest_df: Audit log of every injected defect
    """
    rng = DeterministicRandomState(seed=seed)

    inj_accruals = accruals_df.copy()
    inj_allocations = allocations_df.copy()
    manifest_records = []

    # -------------------------------------------------------------------------
    # 1. Defect Category: DAY_COUNT_MISMATCH
    # Contract says Actual/365; corrupted engine divides by 360 (inflating interest)
    # -------------------------------------------------------------------------
    eligible_365 = inj_accruals[inj_accruals["interest_method"] == "ACTUAL/365"].index.tolist()
    chosen_daycount = rng.sample(eligible_365, min(target_count_per_defect, len(eligible_365)))

    for idx in chosen_daycount:
        row = inj_accruals.loc[idx]
        p = to_decimal(row["start_principal_balance"])
        r = to_decimal(row["interest_rate_annual"])
        days = int(row["day_count"])
        orig_interest = to_decimal(row["interest_accrual_amount"])

        # Corrupted calculation using Actual/360
        corrupted_interest = round_bankers(p * (r / Decimal("360")) * Decimal(str(days)))
        variance = corrupted_interest - orig_interest

        inj_accruals.loc[idx, "interest_accrual_amount"] = float(corrupted_interest)

        manifest_records.append({
            "loan_id": row["loan_id"],
            "period_number": row["period_number"],
            "target_table": "finance.interest_accruals",
            "target_key": row["accrual_id"],
            "defect_type": "DAY_COUNT_MISMATCH",
            "original_value": float(orig_interest),
            "corrupted_value": float(corrupted_interest),
            "injected_variance": float(variance),
            "description": "Actual/360 denominator (360) applied to Actual/365 facility"
        })

    # -------------------------------------------------------------------------
    # 2. Defect Category: LEAP_YEAR_BLINDNESS
    # Ignores leap day (Feb 29, 2024), dropping 1 day of accrual
    # -------------------------------------------------------------------------
    dates = pd.to_datetime(inj_accruals["accrual_date"])
    leap_eligible = inj_accruals[(dates.dt.year == 2024) & (dates.dt.month.isin([2, 3]))].index.tolist()
    # Exclude already mutated rows
    leap_eligible = [i for i in leap_eligible if i not in chosen_daycount]
    chosen_leap = rng.sample(leap_eligible, min(target_count_per_defect, len(leap_eligible)))

    for idx in chosen_leap:
        row = inj_accruals.loc[idx]
        p = to_decimal(row["start_principal_balance"])
        r = to_decimal(row["interest_rate_annual"])
        days = int(row["day_count"])
        conv = row["interest_method"]
        orig_interest = to_decimal(row["interest_accrual_amount"])

        # Drop 1 day (treating 29 days as 28 days)
        corrupted_days = max(1, days - 1)
        divisor = Decimal("360") if conv == "ACTUAL/360" else Decimal("365")
        corrupted_interest = round_bankers(p * (r / divisor) * Decimal(str(corrupted_days)))
        variance = corrupted_interest - orig_interest

        inj_accruals.loc[idx, "interest_accrual_amount"] = float(corrupted_interest)

        manifest_records.append({
            "loan_id": row["loan_id"],
            "period_number": row["period_number"],
            "target_table": "finance.interest_accruals",
            "target_key": row["accrual_id"],
            "defect_type": "LEAP_YEAR_BLINDNESS",
            "original_value": float(orig_interest),
            "corrupted_value": float(corrupted_interest),
            "injected_variance": float(variance),
            "description": "Dropped leap day (Feb 29, 2024), understating accrued interest by 1 day"
        })

    # -------------------------------------------------------------------------
    # 3. Defect Category: ROUNDING_TRUNCATION
    # Drops Banker's Rounding; truncates fractional decimals producing multi-cent drift
    # -------------------------------------------------------------------------
    available_indices = [i for i in inj_accruals.index if i not in chosen_daycount and i not in chosen_leap]
    chosen_rounding = rng.sample(available_indices, min(target_count_per_defect, len(available_indices)))

    for idx in chosen_rounding:
        row = inj_accruals.loc[idx]
        orig_interest = to_decimal(row["interest_accrual_amount"])

        # Truncate cents and subtract 3 to 7 cents of drift
        cents_drift = Decimal(str(rng.randint(3, 7))) / Decimal("100")
        corrupted_interest = max(Decimal("0.01"), orig_interest - cents_drift)
        variance = corrupted_interest - orig_interest

        inj_accruals.loc[idx, "interest_accrual_amount"] = float(corrupted_interest)

        manifest_records.append({
            "loan_id": row["loan_id"],
            "period_number": row["period_number"],
            "target_table": "finance.interest_accruals",
            "target_key": row["accrual_id"],
            "defect_type": "ROUNDING_TRUNCATION",
            "original_value": float(orig_interest),
            "corrupted_value": float(corrupted_interest),
            "injected_variance": float(variance),
            "description": f"Truncated precision drift of {float(cents_drift)} USD"
        })

    # -------------------------------------------------------------------------
    # 4. Defect Category: WATERFALL_ORDERING
    # Reverses priority: Principal applied before fees and interest
    # -------------------------------------------------------------------------
    merged_alloc = inj_allocations.merge(
        schedules_df[["loan_id", "period_number", "scheduled_principal", "scheduled_interest"]],
        on=["loan_id", "period_number"]
    )
    # Eligible rows have interest or fees due and positive payment
    wf_eligible = merged_alloc[
        (merged_alloc["interest_amount"] > 0) &
        (merged_alloc["principal_amount"] > 0)
    ].index.tolist()

    chosen_waterfall = rng.sample(wf_eligible, min(target_count_per_defect, len(wf_eligible)))

    for idx in chosen_waterfall:
        row = merged_alloc.loc[idx]
        payment_id = row["payment_id"]
        total_paid = to_decimal(row["total_allocated"])
        sched_p = to_decimal(row["scheduled_principal"])
        orig_p_alloc = to_decimal(row["principal_amount"])
        orig_i_alloc = to_decimal(row["interest_amount"])
        orig_f_alloc = to_decimal(row["fees_amount"])

        # Corrupted waterfall: Cash is misdirected to principal before interest and fees!
        # The entire interest amount is improperly credited to principal instead of accrued interest
        corrupt_p_alloc = min(total_paid, sched_p + orig_i_alloc)
        rem = total_paid - corrupt_p_alloc
        corrupt_i_alloc = Decimal("0.00")
        corrupt_f_alloc = Decimal("0.00")
        corrupt_prep = rem

        # Find corresponding row in inj_allocations
        alloc_idx = inj_allocations[inj_allocations["payment_id"] == payment_id].index[0]

        inj_allocations.loc[alloc_idx, "principal_amount"] = float(corrupt_p_alloc)
        inj_allocations.loc[alloc_idx, "interest_amount"] = float(corrupt_i_alloc)
        inj_allocations.loc[alloc_idx, "fees_amount"] = float(corrupt_f_alloc)
        inj_allocations.loc[alloc_idx, "prepayment_amount"] = float(corrupt_prep)

        variance = corrupt_p_alloc - orig_p_alloc

        manifest_records.append({
            "loan_id": row["loan_id"],
            "period_number": row["period_number"],
            "target_table": "finance.payment_allocations",
            "target_key": str(row["allocation_id"]),
            "defect_type": "WATERFALL_ORDERING",
            "original_value": float(orig_p_alloc),
            "corrupted_value": float(corrupt_p_alloc),
            "injected_variance": float(variance),
            "description": "Principal allocated before satisfying accrued interest and fees"
        })

    manifest_df = pd.DataFrame(manifest_records)
    return inj_accruals, inj_allocations, manifest_df
