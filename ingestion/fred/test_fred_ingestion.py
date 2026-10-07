"""
FinSight Enterprise — Automated Tests for FRED Macro Ingestion Pipeline
Validates data presence, economic bounds, no nulls, and audit telemetry.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "fred"

SERIES_LIST = ["SOFR", "FEDFUNDS", "DGS10", "CPIAUCNS", "UNRATE", "DPRIME"]


def test_series_parquet_files_exist_and_non_empty():
    """Verify all individual series Parquet files and the combined matrix exist."""
    for series in SERIES_LIST:
        pfile = RAW_DIR / f"{series}.parquet"
        assert pfile.exists(), f"Missing Parquet file for {series}"
        assert pfile.stat().st_size > 0, f"Empty Parquet file for {series}"

    matrix_file = RAW_DIR / "fred_monthly_macro_matrix.parquet"
    assert matrix_file.exists()
    assert matrix_file.stat().st_size > 0


def test_economic_bounds_and_validity():
    """Validates that real macro rates stay within empirical banking sanity bounds."""
    # 1. SOFR (Secured Overnight Financing Rate)
    sofr_df = pd.read_parquet(RAW_DIR / "SOFR.parquet")
    assert sofr_df["value"].min() >= 0.0
    assert sofr_df["value"].max() <= 20.0
    assert "decimal_rate" in sofr_df.columns
    assert (sofr_df["decimal_rate"] == sofr_df["value"] / 100.0).all()

    # 2. Fed Funds
    ff_df = pd.read_parquet(RAW_DIR / "FEDFUNDS.parquet")
    assert ff_df["value"].min() >= 0.0
    assert ff_df["value"].max() <= 20.0

    # 3. CPI
    cpi_df = pd.read_parquet(RAW_DIR / "CPIAUCNS.parquet")
    assert cpi_df["value"].min() >= 200.0
    assert cpi_df["value"].max() <= 450.0

    # 4. Unemployment
    un_df = pd.read_parquet(RAW_DIR / "UNRATE.parquet")
    assert un_df["value"].min() >= 2.0
    assert un_df["value"].max() <= 20.0


def test_no_null_values_after_imputation():
    """Ensures zero missing observation values in Bronze layer."""
    for series in SERIES_LIST:
        df = pd.read_parquet(RAW_DIR / f"{series}.parquet")
        assert df["value"].isna().sum() == 0, f"Found unexpected null values in {series}"
        assert df["observation_date"].isna().sum() == 0


def test_chronological_ordering():
    """Ensures dates are monotonically increasing."""
    for series in SERIES_LIST:
        df = pd.read_parquet(RAW_DIR / f"{series}.parquet")
        assert df["observation_date"].is_monotonic_increasing, f"{series} is not strictly chronological"


def test_ingestion_metadata_audit_log():
    """Verifies ingestion telemetry artifact."""
    meta_path = RAW_DIR / "ingestion_metadata.json"
    assert meta_path.exists()
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    assert meta["status"] == "SUCCESS"
    assert meta["dq_checks_failed"] == 0
    assert meta["dq_checks_passed"] >= 24
    assert len(meta["series_processed"]) == len(SERIES_LIST)
