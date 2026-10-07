# FinSight Enterprise — Functional Requirements Specification (FRS)

---

### 1. Module FR-LEND: Customer & Loan Management

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-LEND-001** | Customer Registration & Segmentation | `customer_id`, `legal_name`, `segment`, `region_id`, `risk_tier`, `credit_score` | Validate segment in (`COMMERCIAL_CORP`, `COMMERCIAL_SME`, `RETAIL_CONSUMER`, `RETAIL_MORTGAGE`). Validate credit score range $300 - 850$. | Persist to `core.customers`. Return unique customer entity. |
| **FR-LEND-002** | Loan Origination & Contract Terms | `loan_id`, `customer_id`, `product_type`, `principal`, `interest_rate_annual`, `rate_type`, `day_count_convention`, `term_months`, `start_date` | Ensure `principal > 0`. If `rate_type == 'FLOATING'`, link to `benchmark_index` + `spread_bps`. Verify maturity date = `start_date + term_months`. | Persist to `core.loans` in `PENDING` state. |
| **FR-LEND-003** | Loan Disbursement Execution | `loan_id`, `disbursement_date`, `disbursed_amount`, `disbursement_account` | Validate loan is `PENDING`. Disbursed amount must match contractual principal. Transition loan status to `ACTIVE`. | Generate initial ledger entry: Debit `Loans Receivable`, Credit `Cash Clearing`. Set `opening_principal = disbursed_amount`. |

---

### 2. Module FR-SERV: Servicing & Payment Waterfall

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-SERV-001** | Monthly Billing Generation | `loan_id`, `billing_date`, `due_date` | Retrieve start-of-month principal balance, calculate monthly scheduled principal, accrued interest for cycle, and unpaid fees. | Create `core.billing_statements` record with `total_due_amount`. |
| **FR-SERV-002** | Payment Waterfall Processing | `payment_id`, `loan_id`, `payment_date`, `payment_amount` | Apply funds in strict priority sequence: <br>1. Late / Servicing Fees <br>2. Accrued Interest <br>3. Scheduled Principal <br>4. Unscheduled Principal Prepayment | Update `core.payments`, update loan `outstanding_principal`. Return receipt with exact waterfall allocation breakdown. |
| **FR-SERV-003** | Delinquency & DPD Classification | `loan_id`, `evaluation_date` | Compare `evaluation_date` against oldest unpaid bill `due_date`. Compute: $\text{DPD} = \text{evaluation\_date} - \text{due\_date}$. | If $\text{DPD} = 0 \to \text{CURRENT}$; $1-29 \to \text{BUCKET\_1}$; $30-59 \to \text{BUCKET\_2}$; $60-89 \to \text{BUCKET\_3}$; $\ge 90 \to \text{DEFAULT}$. |

---

### 3. Module FR-CALC: Financial Calculation Engine

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-CALC-001** | Daily Accrual (`Actual/360`) | `principal_balance`, `annual_rate`, `accrual_date` | Daily rate = $\frac{\text{annual\_rate}}{360}$. <br>$\text{Daily Accrual} = \text{principal\_balance} \times \frac{\text{annual\_rate}}{360}$. | Round to 4 decimal places internally, accumulate to 2 decimals on posting. |
| **FR-CALC-002** | Daily Accrual (`Actual/365`) | `principal_balance`, `annual_rate`, `accrual_date` | Daily rate = $\frac{\text{annual\_rate}}{365}$ (or 366 in leap year). <br>$\text{Daily Accrual} = \text{principal\_balance} \times \frac{\text{annual\_rate}}{\text{days\_in\_year}}$. | Precision check: zero deviation from baseline bond mathematics. |
| **FR-CALC-003** | Amortization Schedule Engine | `principal`, `annual_rate`, `term_months`, `amortization_type` | If `EQUAL_INSTALLMENT`: <br>$M = P \frac{r(1+r)^n}{(1+r)^n - 1}$ where $r = \frac{\text{annual\_rate}}{12}$. <br>Compute monthly principal and interest components across all periods. | Sum of all scheduled principal payments must equal initial principal exactly ($\pm \$0.00$). |

---

### 4. Module FR-REC: Financial Reconciliation Engine

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-REC-001** | Scheduled vs. Actual Principal Reconciliation | `loan_id`, `cycle_id`, `expected_principal_reduction`, `actual_principal_reduction` | Compute: <br>$\Delta_{\text{principal}} = \text{actual} - \text{expected}$. | If $|\Delta| \le 0.01$, status = `PASS`. Else `FAIL`. Persist to `finance.reconciliations`. |
| **FR-REC-002** | Expected vs. Actual Interest Accrual Reconciliation | `loan_id`, `cycle_id`, `expected_interest_accrued`, `processed_interest_accrued` | Compute: <br>$\Delta_{\text{interest}} = \text{processed} - \text{expected}$. | If $|\Delta| \le 0.01$, status = `PASS`. If $|\Delta| > 0.01$, flag as `ACCRUAL_MISMATCH`, trigger defect creation. |
| **FR-REC-003** | Subledger-to-GL Balance Reconciliation | `as_of_date`, `servicing_total_balance`, `gl_account_balance` | Reconcile sum of all active loan balances against General Ledger asset account `1100-LOANS-RECEIVABLE`. | Variance must be $\$0.00$. Any discrepancy triggers an accounting hold. |

---

### 5. Module FR-QA: Quality Engineering & Traceability Subsystem

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-QA-001** | Requirements Traceability Matrix Engine | `brd_requirements`, `test_scenarios`, `test_cases` | Cross-join requirements to test catalog. Detect any requirement lacking test coverage or any orphan test case. | Output complete RTM map with coverage percentage ($\text{Target} = 100\%$). |
| **FR-QA-002** | Automated Test Execution Runner | `test_suite_name` (e.g., `financial_accruals`, `payment_waterfall`) | Execute designated Pytest test modules. Capture execution duration, status (`PASSED`, `FAILED`, `ERROR`), and failure diagnostics. | Store test results in `qa.test_executions`. Update live test dashboard. |
| **FR-QA-003** | Automated Defect Generation on Test Failure | `failed_test_case_id`, `assertion_error_payload`, `expected_value`, `actual_value` | Parse test failure context, extract linked requirement ID, assign severity based on variance size, create defect record. | Persist in `qa.defects` with status `NEW`. Generate unique defect tracking key. |

---

### 6. Module FR-FC & FR-SCEN: Forecasting & Scenario Engines

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-FC-001** | Multi-Model Forecasting Tournament | Historical monthly origination, balance, interest income series + FRED macro regressors | Train candidate models: ARIMA, Holt-Winters, XGBoost across 12-month backtesting split. Compute MAE, RMSE, sMAPE. | Select Champion model per metric. Generate 3–6 month point forecasts + 80% & 95% confidence intervals. |
| **FR-SCEN-001**| Financial Stress Sensitivity Simulator | Baseline portfolio state + vector of stress inputs (`rate_shift_bps`, `origination_delta_pct`, `default_shift_pct`) | Re-evaluate interest income, portfolio runoff, and credit loss provisions across active portfolio under stressed parameters. | Return side-by-side P&L and Balance Sheet impact matrix (`Baseline` vs `Stressed`). |

---

### 7. Module FR-GOV: Security, RBAC & Audit Trails

| Requirement ID | Name | Input Specification | Processing Logic | Output / Validation Rules |
| :--- | :--- | :--- | :--- | :--- |
| **FR-GOV-001** | Role-Based Access Authorization | `auth_token`, `requested_endpoint`, `http_method` | Verify JWT token signature, extract `user_role` in (`ANALYST`, `QA_ENGINEER`, `FINANCE_CONTROLLER`, `ADMIN`, `AUDITOR`), enforce endpoint ACL. | Allow execution or return HTTP 403 Forbidden. |
| **FR-GOV-002** | Immutable Audit Trail Logging | `user_id`, `action`, `entity_type`, `entity_id`, `payload_before`, `payload_after` | Construct structured log with SHA-256 state hashes, server timestamp, and client IP. | Append-only insert to `governance.audit_logs`. Prohibit update or delete operations on audit table. |
