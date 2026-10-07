# FinSight Enterprise — Phase 2: External Data Sources Specification
## Stage 2.1: Federal Reserve Economic Data (FRED) Ingestion Architecture

---

### 1. External Data Catalog & Rationale

FinSight Enterprise integrates six authoritative macroeconomic and financial benchmark series from the **Federal Reserve Bank of St. Louis (FRED)**. These series serve as the empirical foundation for floating-rate loan contract pricing, daily interest accruals, time-series forecasting, and macroeconomic scenario stress testing.

| Series ID | Series Name | Reporting Frequency | Original Units | Role in FinSight Enterprise |
| :--- | :--- | :--- | :--- | :--- |
| **`SOFR`** | Secured Overnight Financing Rate | Daily (Business Days) | Percent (Annualized) | **Primary benchmark index** for floating commercial revolving and corporate credit facilities. |
| **`FEDFUNDS`** | Effective Federal Funds Rate | Monthly (Averages) | Percent (Annualized) | Central bank policy target rate; primary regressor in multi-model interest income forecasting. |
| **`DGS10`** | 10-Year Treasury Constant Maturity Yield | Daily (Business Days) | Percent (Annualized) | Long-term benchmark risk-free rate for fixed corporate term loans and 30-year residential mortgages. |
| **`CPIAUCNS`** | Consumer Price Index for All Urban Consumers (All Items) | Monthly | Index ($1982-1984=100$) | Headline consumer inflation index; used for cost inflation and purchasing power stress scenarios. |
| **`UNRATE`** | Civilian Unemployment Rate | Monthly | Percent | Labor market health indicator; critical predictive regressor for delinquency and default surge forecasting. |
| **`DPRIME`** | Bank Prime Loan Rate | Daily (Business Days) | Percent (Annualized) | Commercial bank benchmark for Small & Medium Enterprise (SME) working capital facilities. |

---

### 2. Upstream Acquisition & Fallback Architecture

To ensure **100% automated reproducibility** without hard dependency on proprietary API keys:

1. **Primary Protocol (Official FRED REST API)**:
   - Endpoint: `https://api.stlouisfed.org/fred/series/observations`
   - Parameters: `series_id={ID}&api_key={FRED_API_KEY}&file_type=json`
   - Authentication: API key read from `FRED_API_KEY` in environment.
2. **Deterministic Public Feed Protocol (Zero-Key Fallback)**:
   - Endpoint: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={ID}`
   - Header Requirement: Standard User-Agent (`FinSightEnterprisePlatform contact@finsightbank.com`).
   - Advantage: Executes autonomously on any fresh environment without requiring user registration.
3. **Resilience & Retry Policy**:
   - Up to 3 attempts with exponential backoff: $t_{\text{wait}} = 2^{\text{attempt}}$ seconds.
   - HTTP timeout set to 20 seconds.
   - If upstream network is unreachable, fallback cleanly to existing Bronze Parquet cache in `data/raw/fred/`.

---

### 3. Date Ranges & Temporal Alignment

- **Historical Horizon**: `2018-01-01` to present.
- **Why 2018?** SOFR was formally published by the Federal Reserve Bank of New York beginning April 2018 as the official replacement for USD LIBOR. Commencing in 2018 provides complete historical coverage of SOFR throughout the low-rate regime (2018–2021) and the subsequent monetary tightening cycle (2022–2024).
- **Temporal Alignment**:
  - Daily series are captured at single-day grain.
  - Monthly series are captured at Month-Start grain (`YYYY-MM-01`).
  - A harmonized monthly feature matrix (`fred_monthly_macro_matrix.parquet`) calculates the monthly mean of daily observations for unified modeling in downstream analytical marts.

---

### 4. Missing-Value Handling & Imputation Rules

Financial markets close on weekends, holidays, and unforeseen market disruptions. This introduces gaps in daily time-series:

1. **Sentinel Text Replacement**:
   - FRED represents missing observations or uncollected dates as `.` (period).
   - Ingestion rule: All `.` values are cast to `NaN` before numeric parsing.
2. **Business Day & Weekend Imputation**:
   - Daily loan servicing requires an interest rate for every single calendar day (including Saturdays, Sundays, and bank holidays like Memorial Day or Thanksgiving).
   - Ingestion rule: Forward-fill (`ffill`) the last observed business day rate across intervening weekends and holidays.
   - Boundary condition: Backward-fill (`bfill`) any missing values at the beginning of the series.
3. **Zero / Negative Rate Handling**:
   - Benchmark rates are validated to ensure $\text{Rate} \ge 0.00\%$. In the event of anomalous negative anomalies, flag a data quality warning.

---

### 5. Units & Mathematical Transformation Rules

| Raw Attribute | Ingested Unit | Transformed Unit | Mathematical Formula | Usage |
| :--- | :--- | :--- | :--- | :--- |
| `SOFR`, `DPRIME`, `FEDFUNDS`, `DGS10` | Percent (e.g. `5.33`) | Decimal Rate (e.g. `0.053300`) | $r = \frac{\text{value}}{100.0}$ | Direct contract pricing |
| Daily Rate (`Actual/360`) | Decimal Rate | Daily Accrual Factor | $f_{360} = \frac{r}{360}$ | Daily interest accrual |
| Daily Rate (`Actual/365`) | Decimal Rate | Daily Accrual Factor | $f_{365} = \frac{r}{365}$ | Consumer credit accrual |
| `CPIAUCNS` | Index Value | YoY Inflation % | $\pi_{\text{YoY}} = \frac{\text{CPI}_t - \text{CPI}_{t-12}}{\text{CPI}_{t-12}} \times 100$ | Macro stress scenarios |
| `UNRATE` | Percent (e.g. `4.2`) | Unemployment % | $\text{Rate as-is}$ | Default surge regressions |

---

### 6. Storage Tiering & Governance Metadata

Ingested files are stored under `data/raw/fred/` with immutable Bronze tier conventions:

```
data/raw/fred/
├── SOFR.parquet                  # Daily observations (2018-present)
├── DPRIME.parquet                # Daily bank prime rates (2018-present)
├── FEDFUNDS.parquet              # Monthly Federal Funds rates (2018-present)
├── DGS10.parquet                 # Daily 10-year Treasury yields (2018-present)
├── CPIAUCNS.parquet              # Monthly CPI inflation index (2018-present)
├── UNRATE.parquet                # Monthly civilian unemployment rates (2018-present)
├── fred_monthly_macro_matrix.parquet # Harmonized cross-sectional monthly feature matrix
└── ingestion_metadata.json       # Audit telemetry (run timestamp, row counts, hash, status)
```

---

### 7. Automated Data Quality (DQ) Gatekeeping Rules

Before ingested data is promoted from Bronze to Silver or used in loan generation:

| DQ Rule Code | Target Series | Validation Constraint | Severity | Action on Failure |
| :--- | :--- | :--- | :--- | :--- |
| **`DQ-FRED-001`** | All Series | Date column format strictly `YYYY-MM-DD` | CRITICAL | Abort ingestion run |
| **`DQ-FRED-002`** | All Series | No null values after imputation | CRITICAL | Abort ingestion run |
| **`DQ-FRED-003`** | `SOFR`, `DPRIME`, `FEDFUNDS`, `DGS10` | $0.00\% \le \text{Rate} \le 25.00\%$ | CRITICAL | Raise anomaly alarm |
| **`DQ-FRED-004`** | `CPIAUCNS` | $150.0 \le \text{CPI} \le 500.0$ | HIGH | Raise anomaly alarm |
| **`DQ-FRED-005`** | `UNRATE` | $2.0\% \le \text{UNRATE} \le 25.0\%$ | HIGH | Raise anomaly alarm |
| **`DQ-FRED-006`** | All Series | Strict ascending chronological order | CRITICAL | Re-sort by observation date |
