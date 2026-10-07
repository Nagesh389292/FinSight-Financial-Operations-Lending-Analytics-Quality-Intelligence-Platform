"""
FinSight Enterprise — FRED Macroeconomic & Benchmark Rates Ingestion Client
Ingests SOFR, Prime Rate, Fed Funds, 10-Year Yield, CPI, and Unemployment Rate.
Persists immutable Bronze raw snapshots to data/raw/fred/ in Parquet format.
"""

import os
import io
import time
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

SERIES_CATALOG = {
    "SOFR": {
        "name": "Secured Overnight Financing Rate",
        "frequency": "daily",
        "description": "Benchmark rate for floating-rate commercial loans"
    },
    "DPRIME": {
        "name": "Bank Prime Loan Rate",
        "frequency": "daily",
        "description": "Benchmark rate for commercial SME and variable retail credit"
    },
    "FEDFUNDS": {
        "name": "Effective Federal Funds Rate",
        "frequency": "monthly",
        "description": "Monetary policy benchmark rate"
    },
    "DGS10": {
        "name": "10-Year Treasury Constant Maturity Yield",
        "frequency": "daily",
        "description": "Long-term risk-free rate for mortgage and term credit pricing"
    },
    "CPIAUCNS": {
        "name": "Consumer Price Index for All Urban Consumers",
        "frequency": "monthly",
        "description": "Headline inflation index for macroeconomic scenario stress testing"
    },
    "UNRATE": {
        "name": "Civilian Unemployment Rate",
        "frequency": "monthly",
        "description": "Key macroeconomic regressor for credit default modeling"
    }
}


def fetch_fred_series(series_id: str, max_retries: int = 3) -> pd.DataFrame:
    """
    Fetches time-series observations from FRED.
    Supports official REST API with API key, with transparent fallback
    to official public CSV download feed if no key is configured.
    """
    headers = {
        "User-Agent": "FinSightEnterprisePlatform contact@finsightbank.com (Research & Analytics)"
    }
    
    # Method 1: Official REST API if key provided
    if FRED_API_KEY:
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={FRED_API_KEY}&file_type=json"
        for attempt in range(1, max_retries + 1):
            try:
                res = requests.get(url, headers=headers, timeout=15)
                if res.status_code == 200:
                    data = res.json().get("observations", [])
                    df = pd.DataFrame(data)[["date", "value"]]
                    df.rename(columns={"date": "observation_date", "value": series_id}, inplace=True)
                    return df
            except Exception as e:
                if attempt == max_retries:
                    print(f"[!] REST API failed for {series_id}: {e}. Trying fallback feed...")
                time.sleep(2)

    # Method 2: Official direct public CSV feed
    csv_url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    for attempt in range(1, max_retries + 1):
        try:
            res = requests.get(csv_url, headers=headers, timeout=20)
            if res.status_code == 200:
                df = pd.read_csv(io.StringIO(res.text))
                return df
            else:
                print(f"[!] Attempt {attempt}: Received HTTP {res.status_code} for {series_id}")
        except Exception as e:
            if attempt == max_retries:
                raise RuntimeError(f"Failed to fetch series {series_id} after {max_retries} attempts: {e}")
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Could not retrieve FRED series: {series_id}")


def clean_and_standardize_series(df: pd.DataFrame, series_id: str) -> pd.DataFrame:
    """Cleans numeric values, parses dates, and formats columns."""
    df = df.copy()
    col_date = "observation_date" if "observation_date" in df.columns else "DATE"
    col_val = series_id if series_id in df.columns else df.columns[1]

    df[col_date] = pd.to_datetime(df[col_date])
    # Replace FRED missing values marked as '.' with NaN
    df[col_val] = pd.to_numeric(df[col_val].replace(".", None), errors="coerce")
    
    # Sort and filter from 2018 onwards for clean contemporary modeling
    df = df[df[col_date] >= "2018-01-01"].sort_values(by=col_date).reset_index(drop=True)
    df.rename(columns={col_date: "observation_date", col_val: "value"}, inplace=True)
    df["series_id"] = series_id
    df["ingested_at"] = datetime.now(timezone.utc)
    return df


def ingest_all_macro_series():
    """Ingests all configured series and saves them to Bronze Parquet storage."""
    print("=" * 70)
    print(" FinSight Enterprise — Ingesting Authoritative FRED Macroeconomic Data ")
    print("=" * 70)
    
    results = {}
    summary = []

    for series_id, meta in SERIES_CATALOG.items():
        print(f"[*] Ingesting {series_id} ({meta['name']})...")
        try:
            raw_df = fetch_fred_series(series_id)
            clean_df = clean_and_standardize_series(raw_df, series_id)
            
            output_file = RAW_DIR / f"{series_id}.parquet"
            clean_df.to_parquet(output_file, index=False)
            
            results[series_id] = clean_df
            summary.append({
                "Series": series_id,
                "Name": meta["name"],
                "Rows": len(clean_df),
                "Min Date": clean_df["observation_date"].min().strftime("%Y-%m-%d"),
                "Max Date": clean_df["observation_date"].max().strftime("%Y-%m-%d"),
                "Latest Value": clean_df.dropna(subset=["value"])["value"].iloc[-1],
                "Status": "SUCCESS"
            })
            print(f"[+] Saved {len(clean_df)} observations to {output_file.name}")
        except Exception as e:
            print(f"[!] Failed to ingest {series_id}: {e}")
            summary.append({
                "Series": series_id,
                "Name": meta["name"],
                "Rows": 0,
                "Status": f"FAILED: {e}"
            })

    # Save a combined monthly macro feature set
    if results:
        combined_df = build_monthly_macro_feature_matrix(results)
        combined_path = RAW_DIR / "fred_monthly_macro_matrix.parquet"
        combined_df.to_parquet(combined_path, index=False)
        print(f"\n[+] Created harmonized monthly macro feature matrix: {combined_path.name}")

    summary_df = pd.DataFrame(summary)
    print("\n" + "=" * 70)
    print(" INGESTION SUMMARY ")
    print("=" * 70)
    print(summary_df.to_string(index=False))
    return results


def build_monthly_macro_feature_matrix(series_dict: dict) -> pd.DataFrame:
    """Harmonizes daily and monthly series into a single month-end feature matrix."""
    monthly_dfs = []
    
    for series_id, df in series_dict.items():
        temp = df.copy()
        temp["year_month"] = temp["observation_date"].dt.to_period("M").dt.to_timestamp()
        # For daily series, compute monthly average; for monthly series, take latest observation
        monthly_val = temp.groupby("year_month")["value"].mean().reset_index()
        monthly_val.rename(columns={"value": series_id}, inplace=True)
        monthly_dfs.append(monthly_val)

    # Merge all on year_month
    matrix = monthly_dfs[0]
    for m in monthly_dfs[1:]:
        matrix = pd.merge(matrix, m, on="year_month", how="outer")

    matrix.sort_values(by="year_month", inplace=True)
    matrix.ffill(inplace=True) # Forward fill missing values
    matrix.bfill(inplace=True)
    matrix["date_key"] = matrix["year_month"].dt.strftime("%Y%m01").astype(int)
    return matrix


if __name__ == "__main__":
    ingest_all_macro_series()
