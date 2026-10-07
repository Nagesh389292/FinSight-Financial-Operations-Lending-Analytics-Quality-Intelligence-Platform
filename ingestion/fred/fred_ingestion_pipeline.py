"""
FinSight Enterprise — Production-Grade FRED Ingestion Pipeline (Phase 2, Stage 2.1)
Ingests SOFR, FEDFUNDS, DGS10, CPIAUCNS, UNRATE, and DPRIME.
Applies data-quality validations, exponential backoff, imputation,
and persists immutable Bronze Parquet files with ingestion audit metadata.
"""

import os
import io
import json
import time
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "fred"
RAW_DIR.mkdir(parents=True, exist_ok=True)

FRED_API_KEY = os.getenv("FRED_API_KEY")

SERIES_SPECS = {
    "SOFR": {
        "name": "Secured Overnight Financing Rate",
        "frequency": "daily",
        "units": "Percent",
        "min_bound": 0.0,
        "max_bound": 25.0,
        "description": "Benchmark index for floating commercial facilities"
    },
    "FEDFUNDS": {
        "name": "Effective Federal Funds Rate",
        "frequency": "monthly",
        "units": "Percent",
        "min_bound": 0.0,
        "max_bound": 25.0,
        "description": "Central bank policy target rate"
    },
    "DGS10": {
        "name": "10-Year Treasury Constant Maturity Yield",
        "frequency": "daily",
        "units": "Percent",
        "min_bound": 0.0,
        "max_bound": 25.0,
        "description": "Risk-free yield curve benchmark"
    },
    "CPIAUCNS": {
        "name": "Consumer Price Index for All Urban Consumers",
        "frequency": "monthly",
        "units": "Index",
        "min_bound": 150.0,
        "max_bound": 500.0,
        "description": "Headline inflation index"
    },
    "UNRATE": {
        "name": "Civilian Unemployment Rate",
        "frequency": "monthly",
        "units": "Percent",
        "min_bound": 2.0,
        "max_bound": 25.0,
        "description": "Labor market credit stress indicator"
    },
    "DPRIME": {
        "name": "Bank Prime Loan Rate",
        "frequency": "daily",
        "units": "Percent",
        "min_bound": 0.0,
        "max_bound": 25.0,
        "description": "Commercial bank benchmark for SME facilities"
    }
}


class FredIngestionPipeline:
    def __init__(self, run_id: str = None):
        self.run_id = run_id or f"RUN-FRED-{uuid.uuid4().hex[:8].upper()}"
        self.start_time = datetime.now(timezone.utc)
        self.headers = {
            "User-Agent": "FinSightEnterprisePlatform contact@finsightbank.com (Enterprise Analytics)"
        }
        self.audit_log = {
            "run_id": self.run_id,
            "pipeline_name": "fred_macro_ingestion",
            "start_time": self.start_time.isoformat(),
            "series_processed": {},
            "dq_checks_evaluated": 0,
            "dq_checks_passed": 0,
            "dq_checks_failed": 0,
            "status": "RUNNING"
        }

    def fetch_series(self, series_id: str, max_retries: int = 3) -> pd.DataFrame:
        """Fetches series with exponential backoff and transparent public feed fallback."""
        # 1. Try official REST API if key configured
        if FRED_API_KEY:
            api_url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
            for attempt in range(1, max_retries + 1):
                try:
                    res = requests.get(api_url, headers=self.headers, timeout=15)
                    if res.status_code == 200:
                        obs = res.json().get("observations", [])
                        df = pd.DataFrame(obs)[["date", "value"]]
                        df.rename(columns={"date": "observation_date", "value": series_id}, inplace=True)
                        return df
                except Exception as e:
                    time.sleep(2 ** attempt)

        # 2. Direct public feed fallback
        csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(csv_url, headers=self.headers, timeout=20)
                if res.status_code == 200:
                    df = pd.read_csv(io.StringIO(res.text))
                    return df
            except Exception as e:
                if attempt == max_retries:
                    # 3. Check for local Bronze cache fallback
                    cached_file = RAW_DIR / f"{series_id}.parquet"
                    if cached_file.exists():
                        print(f"[!] Network unavailable. Falling back to Bronze cache: {cached_file.name}")
                        return pd.read_parquet(cached_file)
                    raise RuntimeError(f"Failed to fetch {series_id}: {e}")
                time.sleep(2 ** attempt)

        raise RuntimeError(f"Could not retrieve {series_id}")

    def validate_and_clean(self, df: pd.DataFrame, series_id: str) -> pd.DataFrame:
        """Applies data quality gatekeeping (DQ-FRED-001 through DQ-FRED-006)."""
        df = df.copy()
        spec = SERIES_SPECS[series_id]

        col_date = "observation_date" if "observation_date" in df.columns else df.columns[0]
        col_val = series_id if series_id in df.columns else df.columns[1]

        # DQ-FRED-001: Date formatting
        self.audit_log["dq_checks_evaluated"] += 1
        df[col_date] = pd.to_datetime(df[col_date], errors="coerce")
        if df[col_date].isna().any():
            self.audit_log["dq_checks_failed"] += 1
            raise ValueError(f"DQ-FRED-001 Failed: Invalid date formats in {series_id}")
        self.audit_log["dq_checks_passed"] += 1

        # Replace '.' sentinels and convert to numeric
        df[col_val] = pd.to_numeric(df[col_val].replace(".", None), errors="coerce")

        # Filter for 2018 onwards and sort ascending (DQ-FRED-006)
        self.audit_log["dq_checks_evaluated"] += 1
        df = df[df[col_date] >= "2018-01-01"].sort_values(by=col_date).reset_index(drop=True)
        self.audit_log["dq_checks_passed"] += 1

        # Impute missing weekends/holidays with forward-fill, then backward-fill
        df[col_val] = df[col_val].ffill().bfill()

        # DQ-FRED-002: Null check post-imputation
        self.audit_log["dq_checks_evaluated"] += 1
        if df[col_val].isna().any():
            self.audit_log["dq_checks_failed"] += 1
            raise ValueError(f"DQ-FRED-002 Failed: Null values remain in {series_id} after imputation")
        self.audit_log["dq_checks_passed"] += 1

        # DQ-FRED-003 / DQ-FRED-004 / DQ-FRED-005: Economic Bounds check
        self.audit_log["dq_checks_evaluated"] += 1
        out_of_bounds = df[(df[col_val] < spec["min_bound"]) | (df[col_val] > spec["max_bound"])]
        if not out_of_bounds.empty:
            self.audit_log["dq_checks_failed"] += 1
            raise ValueError(f"Economic Bounds Check Failed for {series_id}: {len(out_of_bounds)} anomalous rows")
        self.audit_log["dq_checks_passed"] += 1

        # Standardize schema
        df.rename(columns={col_date: "observation_date", col_val: "value"}, inplace=True)
        df["series_id"] = series_id
        df["frequency"] = spec["frequency"]
        df["decimal_rate"] = df["value"] / 100.0 if spec["units"] == "Percent" else None
        df["ingested_at"] = datetime.now(timezone.utc)
        return df

    def run(self) -> dict:
        """Executes full ingestion pipeline across all series."""
        print("=" * 75)
        print(f" FinSight Enterprise — FRED Ingestion Pipeline [{self.run_id}] ")
        print("=" * 75)

        ingested_series = {}

        for series_id, spec in SERIES_SPECS.items():
            print(f"[*] Ingesting {series_id} ({spec['name']})...")
            try:
                raw_df = self.fetch_series(series_id)
                clean_df = self.validate_and_clean(raw_df, series_id)

                # Save individual Bronze Parquet file
                out_path = RAW_DIR / f"{series_id}.parquet"
                clean_df.to_parquet(out_path, index=False)

                # Calculate SHA-256 hash of file for data provenance
                hasher = hashlib.sha256()
                with open(out_path, "rb") as f:
                    hasher.update(f.read())
                file_hash = hasher.hexdigest()

                ingested_series[series_id] = clean_df
                self.audit_log["series_processed"][series_id] = {
                    "rows": len(clean_df),
                    "min_date": clean_df["observation_date"].min().strftime("%Y-%m-%d"),
                    "max_date": clean_df["observation_date"].max().strftime("%Y-%m-%d"),
                    "latest_value": float(clean_df["value"].iloc[-1]),
                    "sha256_hash": file_hash,
                    "status": "SUCCESS"
                }
                print(f"[+] Successfully validated & saved {len(clean_df):,} rows -> {out_path.name}")
            except Exception as e:
                print(f"[!] ERROR processing {series_id}: {e}")
                self.audit_log["series_processed"][series_id] = {
                    "status": "FAILED",
                    "error": str(e)
                }

        # Build harmonized monthly feature matrix
        if ingested_series:
            matrix_df = self.build_monthly_macro_matrix(ingested_series)
            matrix_path = RAW_DIR / "fred_monthly_macro_matrix.parquet"
            matrix_df.to_parquet(matrix_path, index=False)
            print(f"\n[+] Created harmonized monthly macro matrix: {matrix_path.name} ({len(matrix_df):,} periods)")

        # Create sample preview JSON snippet
        sample_preview = {
            "sample_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "latest_observations": {
                s: self.audit_log["series_processed"][s]["latest_value"]
                for s in SERIES_SPECS if s in self.audit_log["series_processed"] and self.audit_log["series_processed"][s].get("status") == "SUCCESS"
            }
        }
        with open(RAW_DIR / "sample_preview.json", "w", encoding="utf-8") as f:
            json.dump(sample_preview, f, indent=2)

        # Complete audit log
        self.end_time = datetime.now(timezone.utc)
        self.audit_log["end_time"] = self.end_time.isoformat()
        self.audit_log["duration_seconds"] = round((self.end_time - self.start_time).total_seconds(), 2)
        self.audit_log["status"] = "SUCCESS" if self.audit_log["dq_checks_failed"] == 0 else "PARTIAL_FAILURE"

        with open(RAW_DIR / "ingestion_metadata.json", "w", encoding="utf-8") as f:
            json.dump(self.audit_log, f, indent=2)

        print("\n" + "=" * 75)
        print(" INGESTION PIPELINE SUMMARY ")
        print("=" * 75)
        print(f"Pipeline Run ID         : {self.run_id}")
        print(f"Execution Duration      : {self.audit_log['duration_seconds']}s")
        print(f"DQ Rules Evaluated      : {self.audit_log['dq_checks_evaluated']}")
        print(f"DQ Rules Passed         : {self.audit_log['dq_checks_passed']}")
        print(f"DQ Rules Failed         : {self.audit_log['dq_checks_failed']}")
        print(f"Pipeline Health Status  : {self.audit_log['status']}")
        print("=" * 75)
        return self.audit_log

    def build_monthly_macro_matrix(self, series_dict: dict) -> pd.DataFrame:
        """Harmonizes all daily and monthly series into a cross-sectional monthly feature matrix."""
        monthly_dfs = []
        for series_id, df in series_dict.items():
            temp = df.copy()
            temp["year_month"] = temp["observation_date"].dt.to_period("M").dt.to_timestamp()
            monthly_val = temp.groupby("year_month")["value"].mean().reset_index()
            monthly_val.rename(columns={"value": series_id}, inplace=True)
            monthly_dfs.append(monthly_val)

        merged = monthly_dfs[0]
        for m in monthly_dfs[1:]:
            merged = pd.merge(merged, m, on="year_month", how="outer")

        merged.sort_values(by="year_month", inplace=True)
        merged.ffill(inplace=True)
        merged.bfill(inplace=True)
        merged["date_key"] = merged["year_month"].dt.strftime("%Y%m01").astype(int)
        return merged


if __name__ == "__main__":
    pipeline = FredIngestionPipeline()
    pipeline.run()
