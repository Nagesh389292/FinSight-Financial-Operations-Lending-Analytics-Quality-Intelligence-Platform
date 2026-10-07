# FinSight Enterprise — Business Requirements Document (BRD)
## Lending Operations, Financial Accounting & Quality Intelligence

---

### 1. Document Control & Scope

| Attribute | Specification |
| :--- | :--- |
| **Document ID** | `BRD-FINSIGHT-2026-V2` |
| **Project Name**| FinSight Enterprise |
| **Target Institution** | FinSight Bank (Commercial & Retail Financial Institution) |
| **Target Domain**| Commercial & Consumer Lending, Loan Servicing, Financial Accounting, Quality Engineering (QA), Executive BI & Forecasting, Platform SRE |
| **Target Roles Addressed** | Banking BA / QA Validation (Genpact), Reporting & Financial Analytics (Barclays), Data Platform SRE / Governance (IQVIA), Software Engineering |

---

### 2. Module 1: Lending Domain & Servicing Workflows (BRD-CORE)

#### 2.1. Customer Hierarchy & Risk Profiling
- **BRD-CORE-001**: The system shall maintain distinct customer segments:
  - `COMMERCIAL_CORP`: Corporate credit facilities ($1M – $50M)
  - `COMMERCIAL_SME`: Small & Medium Enterprise loans ($50k – $1M)
  - `RETAIL_CONSUMER`: Personal and auto loans ($5k – $100k)
  - `RETAIL_MORTGAGE`: Residential property mortgages ($100k – $1.5M)
- **BRD-CORE-002**: Every customer shall be assigned a risk category: `PRIME_A`, `PRIME_B`, `NEAR_PRIME`, or `SUBPRIME`, dictating base underwriting risk margins.

#### 2.2. Loan Products & Terms
- **BRD-CORE-003**: The system shall support both **Fixed-Rate** and **Floating-Rate** loans. Floating-rate loans shall be indexed to reference benchmarks (e.g., 30-Day SOFR or Wall Street Journal Prime Rate) plus a contractual credit spread.
- **BRD-CORE-004**: Supported repayment structures shall include:
  - `AMORTIZING_EQUAL_INSTALLMENT`: Fixed monthly payment (principal + interest)
  - `AMORTIZING_FIXED_PRINCIPAL`: Fixed monthly principal reduction plus decaying interest
  - `INTEREST_ONLY_BALLOON`: Monthly interest accrual with full principal due at maturity

#### 2.3. Loan Lifecycle & Servicing Events
- **BRD-CORE-005**: Every loan must progress through strictly validated lifecycle states:
  $$\text{PENDING} \longrightarrow \text{ACTIVE} \longrightarrow \text{DELINQUENT} \longrightarrow \text{PAID\_OFF} \mid \text{DEFAULT\_CHARGED\_OFF}$$
- **BRD-CORE-006 (Payment Waterfall)**: When a borrower payment is processed, the system must apply cash strictly according to the contractual priority waterfall:
  1. Outstanding Late & Servicing Fees
  2. Accrued Unpaid Interest
  3. Scheduled Principal Reduction
  4. Unscheduled Principal Prepayment (if payment > scheduled amount)
- **BRD-CORE-007 (Delinquency & DPD Aging)**: The system shall calculate **Days Past Due (DPD)** daily:
  - `CURRENT`: $0 \text{ DPD}$
  - `BUCKET_1`: $1 - 29 \text{ DPD}$ (Grace / Soft collection)
  - `BUCKET_2`: $30 - 59 \text{ DPD}$ (Notice of default)
  - `BUCKET_3`: $60 - 89 \text{ DPD}$ (Intensive recovery)
  - `DEFAULT`: $90+ \text{ DPD}$ (Non-accrual / Impairment assessment)

---

### 3. Module 2: Financial Calculation Engine & Accounting Rules (BRD-FIN)

#### 3.1. Interest Accrual Day-Count Conventions
- **BRD-FIN-001**: The financial calculation engine must support three standard international day-count conventions:
  - **`ACTUAL/360`** (U.S. Commercial Lending standard):
    $$I_{\text{daily}} = \text{Balance} \times \frac{\text{Annual Rate}}{360}$$
  - **`ACTUAL/365`** (Consumer & UK / Commonwealth standard):
    $$I_{\text{daily}} = \text{Balance} \times \frac{\text{Annual Rate}}{365}$$
  - **`30/360` (Bond Basis / European standard)**: Assumes 30-day months regardless of actual calendar days.
- **BRD-FIN-002**: Interest shall accrue daily on the start-of-day outstanding principal balance and be posted to the `Accrued Interest Receivable` GL account monthly or on payment dates.

#### 3.2. Financial Balance Calculations
- **BRD-FIN-003**: The closing principal balance for any billing cycle $t$ must adhere to:
  $$\text{Closing Balance}_t = \text{Opening Balance}_t + \text{Disbursements}_t - \text{Principal Repaid}_t - \text{Charge-offs}_t$$
- **BRD-FIN-004**: Double-entry general ledger journal entries must be created for every financial event:
  - *Disbursement*: Debit `Loans Receivable`, Credit `Cash/Disbursement Clearing`
  - *Daily Accrual*: Debit `Accrued Interest Receivable`, Credit `Interest Income`
  - *Payment Receipt*: Debit `Cash`, Credit `Accrued Interest Receivable` & Credit `Loans Receivable`

#### 3.3. Financial Reconciliation Engine (Expected vs. Actual)
- **BRD-FIN-005**: For every loan cycle, the system must execute an automated mathematical reconciliation comparing:
  $$\text{Expected Value (Mathematical Truth Model)} \quad \text{vs.} \quad \text{Processed Value (Operational Servicing)}$$
  across six core financial attributes:
  1. Scheduled Principal Repayment
  2. Accrued Interest
  3. Late Fees Assessed
  4. Closing Principal Balance
  5. Total Payment Received
  6. GL Subledger Balance vs. Servicing Master Balance
- **BRD-FIN-006 (Tolerance & Status)**:
  - If $|\text{Variance}| \le \$0.01$, Reconciliation Status = **PASS**
  - If $|\text{Variance}| > \$0.01$, Reconciliation Status = **FAIL**
  - All FAIL records must automatically trigger a reconciliation alert and defect candidate.

---

### 4. Module 3: Quality Engineering, Test Strategy & Validation Subsystem (BRD-QA)

#### 4.1. Requirements Traceability Matrix (RTM)
- **BRD-QA-001**: Every business requirement (`BRD-*`) must map to at least one **Test Scenario**, which in turn maps to one or more automated **Test Cases** (`TC-*`), executed via automated Pytest suites.
- **BRD-QA-002**: Unmapped requirements or test cases without requirement associations shall be flagged as **Traceability Gaps** in the QA Console.

#### 4.2. Test Taxonomy & Automation Scope
- **BRD-QA-003**: The test automation framework must support:
  1. **Functional Tests**: Loan onboarding validation, loan modification, status transitions, payment waterfall priority.
  2. **Mathematical / Financial Calculation Tests**: Exact penny-level verification of day-count accruals, compounding, amortization schedules, and payoffs.
  3. **Boundary & Negative Tests**: Zero-interest loans, leap-year calculations, negative payments, prepayment exceeding principal balance, post-maturity accrual freezes.
  4. **Data Quality Tests**: Uniqueness of loan IDs, non-negative balances, foreign key integrity, missing customer attributes.
  5. **Integration / End-to-End Tests**: Complete flow from origination $\to$ disbursement $\to$ daily accrual $\to$ payment receipt $\to$ GL journal generation $\to$ reporting mart refresh.
  6. **Regression Certification Suites**: Automated test suite executed against code releases to verify zero regression.

#### 4.3. Defect Management & Resolution Workflow
- **BRD-QA-004**: When any automated test case fails, the system shall programmatically capture and log a **Defect Record**:
  - `defect_id`: Unique identifier (e.g., `DEF-2026-0041`)
  - `requirement_id`: Violated business requirement (`BRD-FIN-001`)
  - `test_case_id`: Failed test case identifier (`TC-ACCR-003`)
  - `severity`: `CRITICAL` (financial discrepancy $\ge \$100$), `MAJOR` (discrepancy $\$0.02 - \$99.99$ or logic failure), `MINOR` (cosmetic/formatting)
  - `expected_result` vs. `actual_result`
  - `root_cause_category`: `CALCULATION_ROUNDING`, `DAY_COUNT_MISMATCH`, `WATERFALL_ORDERING`, `DATA_CORRUPTION`, `UNEXPECTED_NULL`
  - `status`: `NEW`, `TRIAGED`, `RESOLVED`, `VERIFIED_CLOSED`

---

### 5. Module 4: BI Reporting, Forecasting & Scenario Analytics (BRD-BI)

#### 5.1. Executive & Managerial Power BI Suite
- **BRD-BI-001**: The platform must deliver a 6-page interactive Power BI reporting suite:
  - **Page 1 — Executive Portfolio Overview**: Total Active Portfolio, Net Interest Income (NII), Net Interest Margin (NIM), Weighted Average Rate (WAR), Delinquency Rate, Portfolio Growth vs Target.
  - **Page 2 — Lending Operations & Servicing Health**: Origination trends, Product Mix, Regional distribution, DPD Aging Buckets (Current, 30, 60, 90+), Repayment velocity.
  - **Page 3 — Financial Performance & Accruals**: P&L statement, Interest income by product, Fee income, Provision for loan losses, Balance Sheet subledger integrity.
  - **Page 4 — Expected vs. Actual Reconciliation**: Interactive audit grid of processed vs. expected amounts, variance waterfall, failed reconciliation drill-down.
  - **Page 5 — QA & Testing Intelligence**: Automated test execution telemetry, Pass/Fail rate trends, Open defects by severity and root cause, Requirements coverage matrix.
  - **Page 6 — Data Quality & Platform SRE**: Data freshness latency, dbt test assertions, API uptime, pipeline execution runtimes, audit log feed.

#### 5.2. Predictive Forecasting Engine
- **BRD-BI-002**: The system shall forecast:
  - Monthly Loan Originations ($ Volume and Count)
  - Portfolio Outstanding Balance (3–6 month rolling horizon)
  - Projected Monthly Net Interest Income
  - Delinquency / Default Volume Trajectory
- **BRD-BI-003**: The forecasting engine must evaluate a competitive tournament across **ARIMA/SARIMA**, **Holt-Winters ETS**, and **XGBoost / Gradient Boosting** (incorporating FRED benchmark rates), reporting MAE, RMSE, and sMAPE.

#### 5.3. Financial Scenario & Stress Planning
- **BRD-BI-004**: The platform shall provide parametric sensitivity modeling across 4 macroeconomic stress levers:
  - Interest Benchmark Rate Shock ($\pm 50 \text{ to } \pm 300 \text{ bps}$)
  - Loan Origination Volume Delta ($\pm 5\% \text{ to } \pm 25\%$)
  - Credit Default / Impairment Shock ($+0.5\% \text{ to } +4.0\%$)
  - Operational & Servicing Cost Inflation ($\pm 2\% \text{ to } \pm 10\%$)
- Dynamically recalculating Projected Interest Income, Expected Credit Losses (ECL), and Net Margin.

---

### 6. Module 5: Platform SRE, Governance & Security (BRD-OPS)

#### 6.1. Role-Based Access Control (RBAC)
- **BRD-OPS-001**: The system must enforce strict role authorization:
  - `ANALYST`: Read-only access to dimensional marts, forecasting endpoints, and Power BI.
  - `QA_ENGINEER`: Execute test suites, view RTM, inspect reconciliation failures, log/manage defects.
  - `FINANCE_CONTROLLER`: Authorize accounting journal adjustments, review reconciliation variances.
  - `ADMIN`: Manage configurations, pipeline schedules, user provisioning.
  - `AUDITOR`: Immutable access to audit trails, data dictionaries, and regulatory logs.

#### 6.2. Audit Trail & Non-Repudiation
- **BRD-OPS-002**: Every financial modification, test override, or configuration change must produce an immutable audit log entry:
  `audit_id`, `user_id`, `role`, `timestamp_utc`, `action_type`, `entity_type`, `entity_id`, `pre_state_hash`, `post_state_hash`, `execution_status`.

#### 6.3. Platform Monitoring & Telemetry
- **BRD-OPS-003**: Ingestion pipelines, reconciliation batch runs, and dbt transformation jobs must publish structured execution telemetry (`run_id`, `duration_ms`, `records_processed`, `status`, `error_stack`).
