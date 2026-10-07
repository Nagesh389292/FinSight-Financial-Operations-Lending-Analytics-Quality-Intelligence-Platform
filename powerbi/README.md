# FinSight Enterprise — Power BI Business Intelligence Suite

The **FinSight Enterprise Power BI Suite** is a 6-page interactive business intelligence product designed for executive decision-makers, lending operations leads, financial controllers, and quality engineering managers. 

It consumes the conformed **Gold Kimball Star Schema** warehouse layer produced by the FinSight data platform (`data/processed/analytics/`).

---

## 1. Executive Reporting Architecture

```text
┌────────────────────────────────────────────────────────────────────────┐
│                   Power BI Executive Reporting Suite                   │
├─────────────────┬──────────────────┬─────────────────┬─────────────────┤
│ Page 1:         │ Page 2:          │ Page 3:         │ Page 4:         │
│ Executive       │ Lending          │ Financial       │ Forecast        │
│ Overview        │ Performance      │ Performance     │ & Scenario      │
├─────────────────┴──────────────────┼─────────────────┴─────────────────┤
│ Page 5:                            │ Page 6:                           │
│ QA & Defect Intelligence           │ Data Quality, SRE & Operations    │
└────────────────────────────────────┴───────────────────────────────────┘
```

---

## 2. Semantic Model Architecture (Kimball Star Schema)

```text
                             ┌──────────────┐
                             │   dim_date   │
                             └──────┬───────┘
                                    │
    ┌──────────────────────┬────────┼────────┬─────────────────────┐
    │                      │        │        │                     │
    ▼                      ▼        ▼        ▼                     ▼
┌──────────────┐   ┌─────────────┐  │  ┌──────────────┐   ┌──────────────────┐
│ dim_customer │   │ dim_product │  │  │   dim_loan   │   │ fact_data_quality│
└──────┬───────┘   └──────┬──────┘  │  └──────┬───────┘   └──────────────────┘
       │                  │         │         │
       └──────────────┬───┴─────────┼─────────┴──────────────┐
                      ▼             ▼                        ▼
        ┌────────────────────────┐  ┌──────────────┐  ┌─────────────┐
        │ fact_loan_performance  │  │ fact_payment │  │ fact_defect │
        │ (15,000 Snapshots)     │  │ (14,741 Txns)│  │ (600 Records│
        └────────────────────────┘  └──────────────┘  └─────────────┘
                                           │
                                           ▼
                                 ┌──────────────────┐
                                 │  fact_financial  │
                                 │ (4,984 GL Lines) │
                                 └──────────────────┘
```

### Fact Table Grains:
1. **`fact_loan_performance`**: Periodic Snapshot — One record per loan facility per monthly billing cycle (`loan_key` + `date_key`).
2. **`fact_payment`**: Transaction Fact — One record per cash payment received and waterfall allocation (`payment_key`).
3. **`fact_financial`**: Periodic Snapshot — One record per GL account code per date per product line (`financial_key`).
4. **`fact_test_execution`**: Accumulating Snapshot — One record per QA test run execution per category (`qa_fact_key`).
5. **`fact_defect`**: Accumulating Snapshot — One record per detected calculation variance / defect (`defect_key`).
6. **`fact_data_quality`**: Periodic Snapshot — One record per DQ quality dimension evaluation run (`dq_fact_key`).

---

## 3. Ground Truth DAX Reconciliation Tie-Out

Every DAX measure has been verified against the underlying Gold Parquet tables through an automated validation suite (`python powerbi/validate_dax_measures.py`):

| Measure Name | Display Folder | Power BI DAX Expression | Verified Ground Truth | Status |
|---|---|---|---|---|
| **`[Total Loans]`** | `01_Portfolio_Lending` | `DISTINCTCOUNT(dim_loan[loan_id])` | **2,500** | ✅ PASS |
| **`[Original Principal]`** | `01_Portfolio_Lending` | `SUM(dim_loan[original_principal])` | **$4,083,242,991.87** | ✅ PASS |
| **`[Outstanding Principal]`** | `01_Portfolio_Lending` | `SUM(fact_loan_performance[outstanding_principal])` | **$3,902,427,287.56** | ✅ PASS |
| **`[Active Loans]`** | `01_Portfolio_Lending` | `CALCULATE([Total Loans], status = "ACTIVE")` | **2,395** | ✅ PASS |
| **`[Weighted Average Rate (WAR)]`**| `01_Portfolio_Lending` | `DIVIDE(SUMX(dim_loan, P * R), [Original Principal])` | **6.86%** | ✅ PASS |
| **`[Total Payment Volume]`** | `02_Payments_CashFlow` | `SUM(fact_payment[payment_amount])` | **$351,574,751.19** | ✅ PASS |
| **`[Principal Collected]`** | `02_Payments_CashFlow` | `SUM(fact_payment[principal_applied])` | **$211,429,149.52** | ✅ PASS |
| **`[Interest Collected]`** | `02_Payments_CashFlow` | `SUM(fact_payment[interest_applied])` | **$135,101,426.82** | ✅ PASS |
| **`[Fees Collected]`** | `02_Payments_CashFlow` | `SUM(fact_payment[fees_applied])` | **$1,484,002.80** | ✅ PASS |
| **`[Prepayments Collected]`** | `02_Payments_CashFlow` | `SUM(fact_payment[prepayment_applied])` | **$3,560,172.05** | ✅ PASS |
| **`[Delinquent Balance (30+ DPD)]`**| `03_Delinquency_Risk` | `CALCULATE([Outstanding Principal], DPD >= 30)` | **$143,707,050.71** | ✅ PASS |
| **`[Delinquency Rate (30+ DPD)]`** | `03_Delinquency_Risk` | `DIVIDE([Delinquent Balance 30+], [Outstanding Principal])` | **3.68%** | ✅ PASS |
| **`[Total Debits]`** | `04_Financial_GL` | `SUM(fact_financial[total_debit])` | **$491,300,436.35** | ✅ PASS |
| **`[Total Credits]`** | `04_Financial_GL` | `SUM(fact_financial[total_credit])` | **$491,300,436.35** | ✅ PASS |
| **`[GL Debit-Credit Variance]`** | `04_Financial_GL` | `ABS([Total Debits] - [Total Credits])` | **$0.00** | ✅ PASS |
| **`[Total Defects]`** | `05_QA_Defects` | `COUNTROWS(fact_defect)` | **600** | ✅ PASS |
| **`[Defect Density per 1k Ops]`**| `05_QA_Defects` | `DIVIDE([Total Defects], 29741) * 1000` | **20.17** | ✅ PASS |
| **`[Defect Injection Rate %]`** | `05_QA_Defects` | `DIVIDE([Total Defects], 29741) * 100` | **2.02%** | ✅ PASS |
| **`[Total Financial Variance]`** | `05_QA_Defects` | `SUM(fact_defect[variance_amount])` | **$901,738.50** | ✅ PASS |
| **`[Overall DQ Compliance %]`** | `06_DataQuality_SRE` | `DIVIDE([Rules Passed], [Total Rules]) * 100` | **100.00%** | ✅ PASS |

---

## 4. How to Connect Power BI to FinSight Enterprise

### Method A: Direct Parquet / CSV Import (Zero Setup)
1. Open **Power BI Desktop**.
2. Click **Get Data** $\to$ **Folder** (or **Parquet**).
3. Select path: `c:\Users\NAGESH REDDY\Desktop\Pro\data\processed\analytics\`.
4. Load the 10 conformed tables:
   - `dim_date.parquet`
   - `dim_customer.parquet`
   - `dim_product.parquet`
   - `dim_loan.parquet`
   - `fact_loan_performance.parquet`
   - `fact_payment.parquet`
   - `fact_financial.parquet`
   - `fact_test_execution.parquet`
   - `fact_defect.parquet`
   - `fact_data_quality.parquet`
5. Relationships will automatically auto-detect as defined in [`powerbi/semantic_model.json`](semantic_model.json).
6. Copy measures from [`powerbi/dax_measures.dax`](dax_measures.dax).

### Method B: PostgreSQL Direct Query
1. Open **Power BI Desktop** $\to$ **Get Data** $\to$ **PostgreSQL database**.
2. Server: `localhost:5432`, Database: `finsight_db`.
3. Select tables under schema `analytics`.

---

## 5. Detailed 6-Page Report Blueprint

### Page 1: Executive Overview (CFO / CCO Cockpit)
- **KPI Banner**: Closing Portfolio Balance ($3.90B), Total Payment Volume ($351.57M), Interest Collected ($135.10M), Delinquency Rate (3.68%), Active Loans (2,395), Weighted Average Rate (6.86%).
- **Visual 1 (Area Chart)**: Monthly Cash Collections vs Interest Yield Trend over time.
- **Visual 2 (Bar Chart)**: Outstanding Balance by Product Family (CRE, Mortgage, SME, Consumer Credit).
- **Visual 3 (Donut Chart)**: Credit Risk Portfolio Health Status (Performing 96.32% vs Delinquent 3.68%).
- **Visual 4 (Matrix)**: Borrower Segment Financial Performance Summary.

### Page 2: Lending Performance (Servicing & Risk)
- **KPI Banner**: Originated Commitment ($4.08B), Average Facility Size ($1.56M), Delinquent Exposure ($143.71M), Impaired Exposure ($12.45M).
- **Visual 1 (Column Chart)**: Delinquency Aging Buckets (Current vs 30–59 vs 60–89 vs 90+ DPD).
- **Visual 2 (Bar Chart)**: Loan Facilities and Volume by Customer Segment.
- **Visual 3 (Table)**: Facility Contract Master Register & Servicing State.

### Page 3: Financial Performance (P&L & Accounting)
- **KPI Banner**: Gross Cash Collections ($351.57M), Principal Amortized ($211.43M), Interest Collected ($135.10M), Fees Collected ($1.48M), GL Variance ($0.00).
- **Visual 1 (Waterfall Chart)**: Contractual Cash Waterfall Allocation ($351.57M Inflow $\to$ Principal $\to$ Interest $\to$ Fees $\to$ Prepayments).
- **Visual 2 (Line & Clustered Column)**: Monthly General Ledger Activity: Debits vs Credits.
- **Visual 3 (Table)**: General Ledger Trial Balance & Tie-Out (Zero-Variance Enforcement).

### Page 4: Forecast & Scenario (Stress Testing)
- **KPI Banner**: Baseline 12M Portfolio Forecast ($3.92B), +200bps Rate Shock Balance ($3.75B), 2x Delinquency Spike ($287.41M), Stressed Loss Exposure ($129.33M at 45% LGD).
- **Visual 1 (Line Chart)**: Portfolio Balance Projections: Baseline vs Rate Shock vs Delinquency Spike.
- **Visual 2 (Sensitivity Card)**: Macroeconomic Scenario Assumptions & Sensitivity Matrix.

### Page 5: QA & Defects (Genpact Lending QA)
- **KPI Banner**: Injected Defects Detected (600), Critical P1 Defects (150), Major P2 Defects (300), Defect Density (20.17 / 1k Ops), Injection Rate (2.02%), Total Variance Exposure ($901.7K).
- **Visual 1 (Bar Chart)**: Detected Defects by Root Cause Category (Day-Count Mismatch, Leap-Year Blindness, Rounding Truncation, Waterfall Ordering).
- **Visual 2 (Donut Chart)**: Defect Lifecycle Triage Progression (Verified Closed, Resolved, In Investigation, Triaged, New).
- **Visual 3 (Table)**: Automated QA Defect Extraction Register & RTM Mapping.

### Page 6: Data Quality & Operations (Platform SRE)
- **KPI Banner**: Platform Quality Health (100.00%), Rules Evaluated (22), Rules Passed (22), Audited Records (167,175), SHA-256 Audit Events (200).
- **Visual 1 (Bar Chart)**: Compliance Rate by Enterprise Data Quality Dimension (Completeness, Validity, Uniqueness, Referential Integrity, Financial Conservation).
- **Visual 2 (Column Chart)**: Automated QA Test Execution Pass Rate by Category.
- **Visual 3 (Table)**: Enterprise Data Quality SLI Audit Scorecard.
