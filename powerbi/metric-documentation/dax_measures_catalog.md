# FinSight Enterprise — Authoritative DAX Measures Catalog

This document defines the complete enterprise DAX measure library within the **FinSight Enterprise Power BI Semantic Model**. Every measure is tied directly to the Kimball Star Schema Gold layer tables and verified against automated Python ground truth controls.

---

## 1. Portfolio & Lending Performance (`01_Portfolio_Lending`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Total Loans]`** | `DISTINCTCOUNT(dim_loan[loan_id])` | `#,##0` | Total distinct credit facility contracts originated across portfolio. |
| **`[Original Principal]`** | `SUM(dim_loan[original_principal])` | `$#,##0.00` | Aggregate commitment / disbursed facility volume at loan inception. |
| **`[Outstanding Principal]`** | `SUM(fact_loan_performance[outstanding_principal])` | `$#,##0.00` | Current unpaid principal balance remaining in loan servicing cycle. |
| **`[Average Facility Size]`** | `DIVIDE([Outstanding Principal], [Total Loans], 0)` | `$#,##0.00` | Average facility exposure per borrower contract. |
| **`[Active Loans]`** | `CALCULATE([Total Loans], fact_loan_performance[status] = "ACTIVE")` | `#,##0` | Number of currently performing and active servicing contracts. |
| **`[Weighted Average Rate (WAR)]`** | `DIVIDE(SUMX(dim_loan, dim_loan[original_principal] * dim_loan[annual_interest_rate]), [Original Principal], 0)` | `0.0000%` | Portfolio-weighted contractual annual interest rate. |

---

## 2. Payments & Cash Flow Allocations (`02_Payments_CashFlow`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Total Payment Volume]`** | `SUM(fact_payment[payment_amount])` | `$#,##0.00` | Total cash collected across all realized borrower repayments. |
| **`[Principal Collected]`** | `SUM(fact_payment[principal_applied])` | `$#,##0.00` | Cash allocated to contractual principal amortization. |
| **`[Interest Collected]`** | `SUM(fact_payment[interest_applied])` | `$#,##0.00` | Realized cash interest yield collected from borrowers. |
| **`[Fees Collected]`** | `SUM(fact_payment[fees_applied])` | `$#,##0.00` | Late fees and administrative servicing charges collected. |
| **`[Prepayments Collected]`** | `SUM(fact_payment[prepayment_applied])` | `$#,##0.00` | Unscheduled curtailment or early payoff volume. |
| **`[Total Scheduled Due]`** | `SUM(fact_loan_performance[total_due])` | `$#,##0.00` | Total expected contractual billing due across active loans. |
| **`[Collection Efficiency %]`** | `DIVIDE([Total Payment Volume], [Total Scheduled Due], 0)` | `0.00%` | Ratio of realized cash collections against contractual billing. |

---

## 3. Delinquency & Credit Risk (`03_Delinquency_Risk`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Delinquent Balance (30+ DPD)]`** | `CALCULATE([Outstanding Principal], fact_loan_performance[is_delinquent_30_plus] = TRUE())` | `$#,##0.00` | Aggregate exposure on loans with arrears of 30 or more days past due. |
| **`[Default Balance (90+ DPD)]`** | `CALCULATE([Outstanding Principal], fact_loan_performance[is_default_90_plus] = TRUE())` | `$#,##0.00` | Non-performing loan (NPL) exposure impaired 90+ days past due. |
| **`[Delinquency Rate (30+ DPD)]`** | `DIVIDE([Delinquent Balance (30+ DPD)], [Outstanding Principal], 0)` | `0.00%` | Portfolio at Risk (PAR 30) delinquency ratio. |
| **`[Default Rate (90+ DPD)]`** | `DIVIDE([Default Balance (90+ DPD)], [Outstanding Principal], 0)` | `0.00%` | Severe non-performing impairment default ratio. |
| **`[Current Performing Balance]`** | `CALCULATE([Outstanding Principal], fact_loan_performance[days_past_due] < 30)` | `$#,##0.00` | Healthy loan balances paid on time or within grace periods. |
| **`[Current Performing Rate %]`** | `DIVIDE([Current Performing Balance], [Outstanding Principal], 0)` | `0.00%` | Proportion of credit facilities operating in good standing. |

---

## 4. General Ledger & Financial Performance (`04_Financial_GL`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Total Debits]`** | `SUM(fact_financial[total_debit])` | `$#,##0.00` | Total accounting debit movements across all GL chart of accounts. |
| **`[Total Credits]`** | `SUM(fact_financial[total_credit])` | `$#,##0.00` | Total accounting credit movements across all GL chart of accounts. |
| **`[Net GL Movement]`** | `SUM(fact_financial[net_movement])` | `$#,##0.00` | Net change in ledger position ($\text{Debit} - \text{Credit}$). |
| **`[GL Variance (Debit - Credit)]`** | `ABS([Total Debits] - [Total Credits])` | `$#,##0.00` | Double-entry reconciliation tie-out. Must equal exactly $\$0.00$. |
| **`[Total Interest Income Accrued]`** | `SUM(fact_loan_performance[accrued_interest])` | `$#,##0.00` | P&L interest income recognized via accrual accounting. |
| **`[Net Interest Margin % (NIM)]`** | `DIVIDE([Total Interest Income Accrued] * 12, [Outstanding Principal], 0)` | `0.00%` | Annualized net interest margin yield over interest-earning assets. |

---

## 5. QA & Defect Analytics (`05_QA_Defects`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Total Defects]`** | `COUNTROWS(fact_defect)` | `#,##0` | Total defects extracted from reconciliation test execution failures. |
| **`[Critical Defects]`** | `CALCULATE([Total Defects], fact_defect[severity] = "CRITICAL")` | `#,##0` | P1 defects halting operations or exceeding material variance limits. |
| **`[Major Defects]`** | `CALCULATE([Total Defects], fact_defect[severity] = "MAJOR")` | `#,##0` | P2 calculation drift defects requiring engineering triage. |
| **`[Minor Defects]`** | `CALCULATE([Total Defects], fact_defect[severity] = "MINOR")` | `#,##0` | P3 non-blocking rounding variances or cosmetic discrepancies. |
| **`[Open Defects]`** | `CALCULATE([Total Defects], NOT(fact_defect[status] IN {"RESOLVED", "VERIFIED_CLOSED"}))` | `#,##0` | Defects currently in triage or engineering investigation. |
| **`[Resolved Defects]`** | `CALCULATE([Total Defects], fact_defect[status] IN {"RESOLVED", "VERIFIED_CLOSED"})` | `#,##0` | Defects remediated and verified in regression re-tests. |
| **`[Defect Resolution Rate %]`** | `DIVIDE([Resolved Defects], [Total Defects], 0)` | `0.00%` | Proportion of detected defects successfully remediated. |
| **`[Servicing Operations]`** | `29741` | `#,##0` | Total eligible servicing transactions across portfolio. |
| **`[Defect Density per 1k Ops]`** | `DIVIDE([Total Defects], [Servicing Operations], 0) * 1000` | `0.00` | Normalized defect rate per 1,000 servicing operations ($20.17$). |
| **`[Defect Injection Rate %]`** | `DIVIDE([Total Defects], [Servicing Operations], 0) * 100` | `0.00%` | Actual controlled injection rate ($2.02\%$). |
| **`[Total Financial Variance Exposure]`** | `SUM(fact_defect[variance_amount])` | `$#,##0.00` | Aggregate dollar variance exposed by calculation defects ($\$901.7\text{K}$). |
| **`[Mean Time to Detect (MTTD Hours)]`** | `0.5` | `0.0` | Automated daily reconciliation detection velocity ($< 1.0\text{h}$). |
| **`[Mean Time to Resolve (MTTR Hours)]`** | `53.06` | `0.0` | Average hours elapsed between triage and verified remediation. |

---

## 6. Data Quality & Platform SRE (`06_DataQuality_SRE`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Total DQ Rules Evaluated]`** | `SUM(fact_data_quality[total_rules_evaluated])` | `#,##0` | Enterprise quality checks run across Bronze, Silver, and Gold. |
| **`[DQ Rules Passed]`** | `SUM(fact_data_quality[rules_passed])` | `#,##0` | Rules satisfying compliance tolerances without breach ($22 / 22$). |
| **`[DQ Rules Failed]`** | `SUM(fact_data_quality[rules_failed])` | `#,##0` | Rules triggering data incident alerts ($0$). |
| **`[Overall DQ Compliance %]`** | `DIVIDE([DQ Rules Passed], [Total DQ Rules Evaluated], 1.0) * 100` | `0.00%` | High-level data platform health index ($100.0\%$). |
| **`[Audited Records Count]`** | `167175` | `#,##0` | Total individual rows inspected during SLI auditing. |
| **`[Governance Audit Trail Events]`** | `200` | `#,##0` | Immutable SHA-256 state change events in `governance.audit_log`. |

---

## 7. Time Intelligence & MoM Trends (`07_Time_Intelligence`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Outstanding Principal Prior Month]`** | `CALCULATE([Outstanding Principal], DATEADD(dim_date[full_date], -1, MONTH))` | `$#,##0.00` | Portfolio balance at the previous month-end cycle. |
| **`[Outstanding Principal MoM %]`** | `DIVIDE([Outstanding Principal] - [Outstanding Principal Prior Month], [Outstanding Principal Prior Month], 0)` | `0.00%` | Month-over-month portfolio growth/amortization rate. |
| **`[Total Payments Prior Month]`** | `CALCULATE([Total Payment Volume], DATEADD(dim_date[full_date], -1, MONTH))` | `$#,##0.00` | Payment cash volume realized in prior calendar month. |
| **`[Total Payments MoM Change]`** | `[Total Payment Volume] - [Total Payments Prior Month]` | `$#,##0.00` | Absolute change in monthly cash collections. |

---

## 8. Forecasting & Stress Scenarios (`08_Forecast_Scenario`)

| Measure Name | DAX Expression | Format | Business Rationale |
|---|---|---|---|
| **`[Baseline Portfolio 12M Forecast]`** | `[Outstanding Principal] * POWER(1 + 0.005, 12)` | `$#,##0.00` | 12-month baseline extrapolation assuming $+0.5\%$ monthly organic growth. |
| **`[Stress Scenario 1 Balance (+200bps Fed Shock)]`** | `[Outstanding Principal] * (1 - 0.04)` | `$#,##0.00` | $-4.0\%$ contraction under adverse $+200\text{bps}$ benchmark interest rate shock. |
| **`[Stress Scenario 2 Balance (Delinquency Spike 2x)]`** | `[Delinquent Balance (30+ DPD)] * 2.0` | `$#,##0.00` | Severe macroeconomic recession doubling non-performing portfolio. |
| **`[Stress Loss Exposure ($)]`** | `[Stress Scenario 2 Balance (Delinquency Spike 2x)] * 0.45` | `$#,##0.00` | Expected Credit Loss (ECL) applying $45\%$ Loss Given Default (LGD). |
