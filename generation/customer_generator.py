"""
FinSight Enterprise — Deterministic Customer & Borrower Profile Generator
Generates realistic corporate and retail borrower profiles adhering to underwriting constraints.
"""

from datetime import datetime, timezone
import pandas as pd
from generation.config import REGIONS, CUSTOMER_SEGMENTS, REFERENCE_TIMESTAMP
from generation.random_state import DeterministicRandomState

CORP_NAMES_PREFIX = ["Meridian", "Pinnacle", "Aegis", "Vanguard", "Summit", "Sterling", "Apex", "Nexus", "Atlas", "Titan"]
CORP_NAMES_SUFFIX = ["Logistics LLC", "Industries Inc", "Holdings Corp", "Enterprises LLC", "Technologies Corp", "Global Capital LLC"]

RETAIL_FIRST = ["Alexander", "Charlotte", "Daniel", "Emma", "Henry", "Isabella", "James", "Mia", "Oliver", "Sophia", "William", "Ava"]
RETAIL_LAST = ["Anderson", "Bennett", "Campbell", "Davis", "Edwards", "Foster", "Garcia", "Harris", "Johnson", "Miller", "Taylor", "Wilson"]


def generate_customers(count: int, rng: DeterministicRandomState) -> pd.DataFrame:
    """Generates `count` deterministic customer records."""
    customers = []
    seg_keys = list(CUSTOMER_SEGMENTS.keys())
    seg_weights = [0.20, 0.25, 0.35, 0.20] # 20% Corp, 25% SME, 35% Retail Installment, 20% Mortgage

    for i in range(1, count + 1):
        cust_id = f"CUST-{i:05d}"
        seg_key = rng.choices(seg_keys, weights=seg_weights, k=1)[0]
        spec = CUSTOMER_SEGMENTS[seg_key]
        region = rng.choice(REGIONS)

        # Credit Score & Tier Assignment
        score_raw = rng.gauss(mu=(spec["min_credit_score"] + spec["max_credit_score"]) / 2, sigma=35)
        credit_score = int(max(spec["min_credit_score"], min(spec["max_credit_score"], score_raw)))

        if credit_score >= 740:
            risk_category = "PRIME_A"
        elif credit_score >= 680:
            risk_category = "PRIME_B"
        elif credit_score >= 620:
            risk_category = "NEAR_PRIME"
        else:
            risk_category = "SUBPRIME"

        # Annual Income & DTI
        income = round(rng.uniform(spec["min_income"], spec["max_income"]), 2)
        dti = round(rng.uniform(0.1800, 0.4400), 4)

        # Legal Name
        if "COMMERCIAL" in spec["customer_type"]:
            legal_name = f"{rng.choice(CORP_NAMES_PREFIX)} {rng.choice(CORP_NAMES_SUFFIX)}"
        else:
            legal_name = f"{rng.choice(RETAIL_FIRST)} {rng.choice(RETAIL_LAST)}"

        customers.append({
            "customer_id": cust_id,
            "legal_name": legal_name,
            "customer_type": spec["customer_type"],
            "region": region,
            "segment": spec["segment"],
            "risk_category": risk_category,
            "credit_score": credit_score,
            "annual_income": income,
            "debt_to_income_ratio": dti,
            "created_at": REFERENCE_TIMESTAMP,
            "updated_at": REFERENCE_TIMESTAMP
        })

    return pd.DataFrame(customers)
