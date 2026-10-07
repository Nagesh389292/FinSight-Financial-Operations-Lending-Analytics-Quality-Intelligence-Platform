# FinSight Enterprise — Source Data Plan & Data Strategy

---

### 1. Data Strategy Principles

FinSight Enterprise enforces a bifurcated data strategy:
1. **Real External Data**: Used for all macroeconomic indicators, benchmark interest rates, and regulatory inflation indices.
2. **Controlled Synthetic Financial Data**: Used for loan-level contracts, borrower profiles, payment transactions, and accounting subledgers.

> **Integrity & Honesty Mandate**: Real bank customer loan records and proprietary core servicing ledgers (such as Finastra Loan IQ databases) are strictly confidential under banking privacy laws (GLBA, GDPR). FinSight does not claim to hold confidential bank records. Instead, our synthetic data is mathematically modeled to simulate real-world lending contracts and includes deliberately injected edge cases to test and certify our Quality Engineering & Reconciliation engine.

---

### 2. Part A: Authoritative Real External Data Sources

All reference rates and macroeconomic series are ingested programmatically via official government and central bank APIs:

| Data Source | Series ID / Endpoint | Frequency | Role in FinSight Enterprise |
| :--- | :--- | :--- | :--- |
| **St. Louis Fed (FRED)** | `SOFR` | Daily / Monthly | Secured Overnight Financing Rate (Benchmark for floating commercial facilities). |
| **St. Louis Fed (FRED)** | `DPRIME` / `MPRIME` | Daily / Monthly | Bank Prime Loan Rate (Benchmark for SME and variable retail facilities). |
| **St. Louis Fed (FRED)** | `FEDFUNDS` | Monthly | Effective Federal Funds Rate (Monetary policy regressor in forecasting). |
| **St. Louis Fed (FRED)** | `DGS10` | Daily / Monthly | 10-Year Treasury Constant Maturity Yield (Yield curve benchmark). |
| **St. Louis Fed (FRED)** | `CPIAUCNS` | Monthly | Consumer Price Index (Inflation driver for scenario stress testing). |
| **St. Louis Fed (FRED)** | `UNRATE` | Monthly | Civilian Unemployment Rate (Key regressor for default probability modeling). |

#### Ingestion & Persistence Architecture:
- Handled by Python ingestion clients in `ingestion/fred/`.
- Ingested raw payloads are validated and persisted to `data/raw/fred/` in immutable Parquet format.
- Cached locally to ensure 100% offline development reproducibility if external network access is constrained.

---

### 3. Part B: Controlled Synthetic Lending & Servicing Data

Synthetic data generation simulates a mid-sized lending institution managing an active portfolio of **2,500+ commercial and consumer credit facilities** across 4 years of operating history.

#### 3.1. Entity Generation Models
1. **Borrower Entities (`core.customers`)**:
   - Realistic legal entities and retail profiles across 4 geographic regions.
   - Distinct customer segments: `COMMERCIAL_CORP`, `COMMERCIAL_SME`, `RETAIL_CONSUMER`, `RETAIL_MORTGAGE`.
   - Credit risk tiers with realistic FICO/internal credit rating distributions.
2. **Loan Facilities (`core.loans`)**:
   - Realistic principal sizes: $10,000 to $15,000,000.
   - Mix of Fixed-Rate and Floating-Rate loans tied to real FRED SOFR / Prime rates.
   - International day-count conventions: `ACTUAL/360`, `ACTUAL/365`, `30/360`.
   - Amortization profiles: Equal installment, fixed principal, interest-only balloon.
3. **Servicing & Payment Streams (`core.payments`, `finance.accruals`)**:
   - Monthly billing schedules across the 48-month operating timeline.
   - Realized payment streams: on-time payments, prepayments, short payments, and missed payments.
   - Dynamic delinquency aging tracking DPD migration across delinquency buckets.

---

### 4. Part C: Controlled Anomaly & Defect Injection Strategy

To prove the efficacy of the **Quality Engineering / Validation Engine** (addressing the Genpact requirement), approximately **2.5% of synthetic loans** are programmatically injected with real-world calculation and servicing defects:

| Defect Code | Defect Scenario | Injection Description | Expected Engine Behavior |
| :--- | :--- | :--- | :--- |
| **DEF-INJ-001** | Day-Count Convention Mismatch | Servicing engine calculates interest using `30/360` on an `ACTUAL/360` contractual commercial facility. | Reconciliation engine flags accrual variance ($>\$0.01$). Logs defect with root cause `DAY_COUNT_MISMATCH`. |
| **DEF-INJ-002** | Penny Rounding Truncation | Calculation truncates decimals instead of Banker's Rounding (`ROUND_HALF_EVEN`), producing cumulative $0.03 - $0.45 penny drift. | Mathematical validation catches variance. QA test `TC-ACCR-002` fails. |
| **DEF-INJ-003** | Waterfall Priority Reversal | Payment application engine applies cash to principal reduction before satisfying outstanding late fees. | Servicing validation fails rule `BRD-CORE-006`. Defect logged as `WATERFALL_ORDERING`. |
| **DEF-INJ-004** | Leap Year Accrual Blindness | Daily interest calculation uses 365 denominator during a leap year (February 29) on an `ACTUAL/ACTUAL` facility. | Boundary test `TC-LEAP-001` triggers assertion failure. |
| **DEF-INJ-005** | Negative Payment / Overflow | System accepts negative payment or prepayment exceeding closing balance. | Data quality rule `DQ-VAL-004` rejects transaction, records validation anomaly. |

This strategy ensures the QA dashboard, reconciliation reports, and defect management workflows display genuine analytical value rather than sterile, all-green dummy data.

---

### 5. Part D: Professional Portfolio Positioning & Interview Narrative

To maintain 100% intellectual honesty and demonstrate seniority during technical interviews:

- **What to say on Resume / GitHub:**
  > *"Built a deterministic lending portfolio simulator with 2,500 synthetic loan contracts anchored to real FRED macroeconomic data, implementing payment servicing, interest accrual, DPD tracking, double-entry accounting and reconciliation."*

- **When asked: "Is your data real?":**
  > *"The macroeconomic inputs are real public FRED observations. Customer, loan and transaction-level data are deterministic synthetic data generated from documented lending rules because real bank-level loan data is confidential. The financial calculations and servicing logic are implemented against those contracts, and the QA layer deliberately injects controlled defects to validate the system."*

