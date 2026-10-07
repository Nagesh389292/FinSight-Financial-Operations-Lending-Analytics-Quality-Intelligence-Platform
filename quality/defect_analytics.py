"""
FinSight Enterprise — Defect Analytics & Lifecycle Intelligence Engine (Phase 3.3)
Aggregates and computes advanced defect telemetry:
- Severity & Priority distributions
- Defect density per 1,000 operations, product family, and customer segment
- Defect lifecycle state transitions, aging brackets, and simulated MTTR
- Root cause breakdown and financial variance exposure analysis
Outputs conformed defect analytics facts to data/generated/qa/.
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from generation.random_state import DeterministicRandomState
from quality.config import BASE_DIR, DEFAULT_SEED, REFERENCE_TIMESTAMP

OUTPUT_QA_DIR = BASE_DIR / "data" / "generated" / "qa"
OUTPUT_QA_DIR.mkdir(parents=True, exist_ok=True)


def compute_defect_analytics(
    defects_df: pd.DataFrame,
    loans_df: pd.DataFrame,
    customers_df: pd.DataFrame,
    products_df: pd.DataFrame,
    total_servicing_operations: int = 29741,
    seed: int = DEFAULT_SEED
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """
    Computes comprehensive defect metrics and simulated lifecycle state transitions.
    Returns:
    - enriched_defects_df: Defects with simulated aging, status, MTTR, product, and segment
    - density_by_product_df: Defect density per product family
    - density_by_segment_df: Defect density per customer segment
    - summary_metrics: High-level analytics summary dictionary
    """
    rng = DeterministicRandomState(seed=seed)

    # Enrich defects with loan, customer, and product metadata
    merged = defects_df.merge(
        loans_df[["loan_id", "customer_id", "product_code"]],
        on="loan_id",
        how="left"
    ).merge(
        customers_df[["customer_id", "segment", "risk_category"]],
        on="customer_id",
        how="left"
    ).merge(
        products_df[["product_code", "product_name", "product_family"]],
        on="product_code",
        how="left"
    )

    enriched_defects = merged.copy()

    # Simulate realistic lifecycle triage progression and aging days
    # (60% Resolved/Closed, 25% In Investigation, 10% Triaged, 5% New)
    statuses = ["VERIFIED_CLOSED", "RESOLVED", "IN_INVESTIGATION", "TRIAGED", "NEW"]
    status_weights = [0.35, 0.25, 0.25, 0.10, 0.05]

    aging_days_list = []
    status_list = []
    mttr_hours_list = []
    resolved_dates = []

    for _ in range(len(enriched_defects)):
        st = rng.choices(statuses, weights=status_weights)[0]
        status_list.append(st)

        if st in ("RESOLVED", "VERIFIED_CLOSED"):
            # Resolved defects have MTTR between 12 and 120 hours (0.5 to 5 days)
            mttr = round(rng.uniform(12.0, 96.0), 1)
            aging = int(mttr / 24) + 1
            res_date = REFERENCE_TIMESTAMP + timedelta(hours=mttr)
        elif st == "IN_INVESTIGATION":
            mttr = None
            aging = rng.randint(2, 10)
            res_date = None
        elif st == "TRIAGED":
            mttr = None
            aging = rng.randint(1, 4)
            res_date = None
        else: # NEW
            mttr = None
            aging = rng.randint(0, 2)
            res_date = None

        mttr_hours_list.append(mttr)
        aging_days_list.append(aging)
        resolved_dates.append(res_date)

    enriched_defects["status"] = status_list
    enriched_defects["days_open"] = aging_days_list
    enriched_defects["mttr_hours"] = mttr_hours_list
    enriched_defects["resolved_at"] = resolved_dates

    # Aging Bracket assignment
    def assign_aging_bracket(days):
        if days <= 7:
            return "0-7 Days"
        elif days <= 14:
            return "8-14 Days"
        elif days <= 30:
            return "15-30 Days"
        else:
            return "30+ Days"

    enriched_defects["aging_bracket"] = enriched_defects["days_open"].apply(assign_aging_bracket)

    # 1. Defect Density by Product Family
    prod_counts = loans_df.merge(products_df, on="product_code")["product_family"].value_counts().reset_index()
    prod_counts.columns = ["product_family", "total_facilities"]

    defect_prod = enriched_defects["product_family"].value_counts().reset_index()
    defect_prod.columns = ["product_family", "defect_count"]

    density_by_product = prod_counts.merge(defect_prod, on="product_family", how="left").fillna(0)
    density_by_product["defect_count"] = density_by_product["defect_count"].astype(int)
    density_by_product["defect_density_pct"] = round((density_by_product["defect_count"] / density_by_product["total_facilities"]) * 100, 2)

    # 2. Defect Density by Customer Segment
    seg_counts = customers_df["segment"].value_counts().reset_index()
    seg_counts.columns = ["segment", "total_customers"]

    defect_seg = enriched_defects["segment"].value_counts().reset_index()
    defect_seg.columns = ["segment", "defect_count"]

    density_by_segment = seg_counts.merge(defect_seg, on="segment", how="left").fillna(0)
    density_by_segment["defect_count"] = density_by_segment["defect_count"].astype(int)
    density_by_segment["defect_density_pct"] = round((density_by_segment["defect_count"] / density_by_segment["total_customers"]) * 100, 2)

    # 3. Overall Summary Telemetry
    total_defects = len(enriched_defects)
    overall_density_per_1000 = round((total_defects / total_servicing_operations) * 1000, 2)
    resolved_mttr_avg = round(float(pd.Series(mttr_hours_list).dropna().mean()), 2)

    summary_metrics = {
        "analysis_timestamp": REFERENCE_TIMESTAMP.isoformat(),
        "total_defects": total_defects,
        "total_servicing_operations": total_servicing_operations,
        "defect_density_per_1000_operations": overall_density_per_1000,
        "severity_distribution": enriched_defects["severity"].value_counts().to_dict(),
        "priority_distribution": enriched_defects["priority"].value_counts().to_dict(),
        "status_distribution": enriched_defects["status"].value_counts().to_dict(),
        "root_cause_distribution": enriched_defects["root_cause_category"].value_counts().to_dict(),
        "aging_bracket_distribution": enriched_defects["aging_bracket"].value_counts().to_dict(),
        "mean_time_to_detect_hours": 0.5, # MTTD under 1 hour via automated daily reconciliation
        "mean_time_to_resolve_hours": resolved_mttr_avg,
        "total_financial_variance_usd": round(float(enriched_defects["variance_amount"].abs().sum()), 2),
        "max_single_variance_usd": round(float(enriched_defects["variance_amount"].abs().max()), 2)
    }

    # Save artifacts
    enriched_defects.to_parquet(OUTPUT_QA_DIR / "defect_analytics_enriched.parquet", index=False)
    density_by_product.to_parquet(OUTPUT_QA_DIR / "defect_density_by_product.parquet", index=False)
    density_by_segment.to_parquet(OUTPUT_QA_DIR / "defect_density_by_segment.parquet", index=False)

    with open(OUTPUT_QA_DIR / "defect_analytics_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_metrics, f, indent=2)

    return enriched_defects, density_by_product, density_by_segment, summary_metrics
