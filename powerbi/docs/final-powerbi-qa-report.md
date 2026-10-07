# FinSight Enterprise — Power BI Final QA Audit Report

**Document ID:** `FINSIGHT-PBI-QA-FINAL-001`  
**Execution Timestamp:** `2026-10-07 23:37:00 IST`  
**Project File:** `powerbi/FinSight_Enterprise.pbip`  
**Target Power BI Desktop Version:** `2.157.1354.0` (64-bit)  
**Tabular Compatibility Level:** `1606`  
**Overall Validation Status:** **PASS**

---

## Executive Summary

This report documents the final automated Quality Assurance (QA) audit for the **FinSight Enterprise Power BI Project (`.pbip`)**. The project is an end-to-end automated business intelligence system that renders an enterprise-grade commercial and retail lending analytics platform across 6 report pages and 48 visual containers.

The audit independently verifies that:
1. The native PBIP project structure strictly conforms to Microsoft Fabric and Power BI Desktop specifications.
2. The semantic model (`model.bim`) operates at CompatibilityLevel `1606`, preventing engine downgrade faults.
3. All 11 Kimball star schema tables, 13 relationships, and 55 DAX measures load and bind cleanly.
4. All 48 visuals have populated query projections and field references without empty placeholders.
5. All 28 authoritative business control totals reconcile with **0.00 variance** against the underlying Gold Parquet facts.
6. Both the targeted semantic model test suite (9 tests) and the repository-wide test suite (60 tests) pass with a 100% success rate.

---

## 1. PBIP Structural Validation

| File / Component | Expected Specification | Actual State | Status |
|---|---|---|:---:|
| `FinSight_Enterprise.pbip` | Fabric PBIP 1.0 schema; `enableAutoRecovery: true`; no `enableAutoAuth` | Conforms; clean settings object; no deprecated flags | **PASS** |
| `FinSight_Enterprise.Dataset/definition.pbism` | Single modern Fabric semantic model manifest | Exists; version 4.2 / 1.0 conforming | **PASS** |
| `FinSight_Enterprise.Dataset/definition.pbidataset` | Obsolete legacy manifest | **Absent** (Strictly excluded to prevent dual-format collision) | **PASS** |
| `FinSight_Enterprise.Report/definition.pbir` | Relative dataset reference (`byPath` to `../FinSight_Enterprise.Dataset`) | Exists; version 4.0; valid `byPath` pointer | **PASS** |
| `FinSight_Enterprise.Report/report.json` | 6 sections; 48 visual containers; valid JSON syntax | 6 pages; 48 containers; 0 syntax errors | **PASS** |
| `FinSight_Enterprise.Dataset/model.bim` | CompatibilityLevel `1606`; TOM JSON layout | Level `1606`; TOM structure loaded by Analysis Services | **PASS** |
| `FinSight_Enterprise.Dataset/.pbi/cache.abf` | Clean runtime cache | Cache cleared on build; zero downgrade locks | **PASS** |

---

## 2. Semantic Model Validation

The semantic model implements a high-performance **Kimball Star Schema** over 10 Gold Parquet analytical datasets and 1 centralized DAX calculation table:

### 2.1 Table Structure (11 Business Tables)
* **Dimensions (4):**
  * `dim_date`: 3,288 calendar days spanning historical and projection windows (Grain: Calendar Date).
  * `dim_customer`: 2,500 commercial and retail borrowers with risk grades, credit scores, and customer segments.
  * `dim_product`: 5 lending product categories (Mortgage, Commercial SME, Auto, Personal, Revolving Line).
  * `dim_loan`: 2,500 loan facilities with interest rate types, day count conventions, and commitment amounts.
* **Facts (6):**
  * `fact_loan_performance`: 15,000 monthly facility snapshots tracking DPD, delinquency status, and principal balances.
  * `fact_payment`: 14,741 cash flow transactions allocating payments across principal, interest, fees, and prepayments.
  * `fact_financial`: 4,984 double-entry General Ledger journal lines with balanced debit and credit legs.
  * `fact_defect`: 600 controlled QA defect occurrences categorized by severity, root cause, and variance exposure.
  * `fact_test_execution`: Automated testing execution runs across financial calculations, functional lifecycles, and reconciliation.
  * `fact_data_quality`: Enterprise data quality evaluations across 22 business governance rules.
* **Calculation Table (1):**
  * `_Measures`: Centralized storage for 55 DAX measures across 8 enterprise metric domains.

### 2.2 Relationship Integrity (13 Star-Schema Relationships)
* All 13 business relationships are configured as **One-to-Many (`1:N`)**, **Active (`isActive = true`)**, and use standard TMSL **`crossFilteringBehavior = "oneDirection"`** (from dimension to fact).
* Zero relationships utilize the prohibited `singleDirection` enum.
* Analysis Services successfully loaded all 13 relationships without topological cycles or ambiguity errors.

---

## 3. Report Visual Validation

All 6 report pages were audited across their constituent visual containers:

| Page # | Page Name | Visual Count | Visual Types | Binding Health |
|:---:|---|:---:|---|:---:|
| **1** | **Executive Overview** | 10 | 4 KPI Cards, 1 Area Chart, 1 Donut Chart, 1 Bar Chart, 1 Matrix, 1 Table, 1 Header Textbox | 100% Populated |
| **2** | **Lending Performance** | 7 | 3 KPI Cards, 1 Clustered Column, 1 Line Chart, 1 Donut Chart, 1 Facility Table | 100% Populated |
| **3** | **Financial Performance** | 8 | 4 KPI Cards, 1 Waterfall/Bar Chart, 1 Line Chart, 1 GL Balance Table, 1 Textbox | 100% Populated |
| **4** | **Forecast & Scenario** | 6 | 3 KPI Cards, 1 Multi-Line Scenario Chart, 1 Sensitivity Matrix, 1 Governance Textbox | 100% Populated |
| **5** | **QA & Defects** | 9 | 4 KPI Cards, 1 Severity Donut, 1 Trend Bar Chart, 1 Defect Drilldown Table, 2 Textboxes | 100% Populated |
| **6** | **Data Quality & Operations** | 8 | 4 KPI Cards, 1 Compliance Gauge/Card, 1 Rules Matrix, 1 Test Execution Log, 1 Textbox | 100% Populated |
| **Total** | **6 Pages** | **48 Visuals** | **Full Visual Hierarchy** | **0 Placeholders** |

* **Zero Placeholder Warnings:** No visual contains `"Select or drag fields"` placeholder states.
* **Query Ref Conformance:** Every `singleVisual.projections` query reference matches an exact `Select` expression in its accompanying `prototypeQuery`.
* **Entity Verification:** 100% of referenced measures exist in `_Measures` and 100% of referenced columns exist in the underlying Kimball star schema.

---

## 4. Business Control-Total Reconciliation

Every reported metric was independently reconciled between the DAX measure formulation and the underlying Gold Star Schema Parquet datasets (`data/processed/analytics/`):

| # | Domain / Metric Name | Authoritative Control | Computed Gold Value | Variance | Status |
|:---:|---|---:|---:|---:|:---:|
| 1 | **Total Loans** | `2,500` | `2,500` | `0.00` | **MATCH** |
| 2 | **Original Principal** | `$4,083,242,991.87` | `$4,083,242,991.87` | `$0.00` | **MATCH** |
| 3 | **Closing Outstanding Principal** | `$3,902,427,287.56` | `$3,902,427,287.56` | `$0.00` | **MATCH** |
| 4 | **Active Loans** | `2,395` | `2,395` | `0.00` | **MATCH** |
| 5 | **Average Facility Size** | `$1,560,970.92` | `$1,560,970.92` | `$0.00` | **MATCH** |
| 6 | **Weighted Average Rate (WAR)** | `6.86%` | `6.86%` | `0.00%` | **MATCH** |
| 7 | **Total Payment Volume** | `$351,574,751.19` | `$351,574,751.19` | `$0.00` | **MATCH** |
| 8 | **Principal Collected** | `$211,429,149.52` | `$211,429,149.52` | `$0.00` | **MATCH** |
| 9 | **Interest Collected** | `$135,101,426.82` | `$135,101,426.82` | `$0.00` | **MATCH** |
| 10 | **Fees Collected** | `$1,484,002.80` | `$1,484,002.80` | `$0.00` | **MATCH** |
| 11 | **Prepayments Collected** | `$3,560,172.05` | `$3,560,172.05` | `$0.00` | **MATCH** |
| 12 | **Delinquent Balance (30+ DPD)** | `$143,707,050.71` | `$143,707,050.71` | `$0.00` | **MATCH** |
| 13 | **Portfolio at Risk (PAR 30)** | `3.68%` | `3.68%` | `0.00%` | **MATCH** |
| 14 | **Current Performing Balance** | `$3,758,720,236.85` | `$3,758,720,236.85` | `$0.00` | **MATCH** |
| 15 | **Total Debits** | `$491,300,436.35` | `$491,300,436.35` | `$0.00` | **MATCH** |
| 16 | **Total Credits** | `$491,300,436.35` | `$491,300,436.35` | `$0.00` | **MATCH** |
| 17 | **GL Debit-Credit Variance** | `$0.00` | `$0.00` | `$0.00` | **MATCH** |
| 18 | **Total Injected QA Defects** | `600` | `600` | `0.00` | **MATCH** |
| 19 | **Critical Defects** | `150` | `150` | `0.00` | **MATCH** |
| 20 | **Major Defects** | `300` | `300` | `0.00` | **MATCH** |
| 21 | **Minor Defects** | `150` | `150` | `0.00` | **MATCH** |
| 22 | **Defect Density per 1k Ops** | `20.17` | `20.17` | `0.00` | **MATCH** |
| 23 | **Defect Injection Rate %** | `2.02%` | `2.02%` | `0.00%` | **MATCH** |
| 24 | **Financial Exposure from Defects** | `$901,738.50` | `$901,738.50` | `$0.00` | **MATCH** |
| 25 | **Total DQ Rules Evaluated** | `22` | `22` | `0.00` | **MATCH** |
| 26 | **DQ Rules Passed** | `22` | `22` | `0.00` | **MATCH** |
| 27 | **DQ Rules Failed** | `0` | `0` | `0.00` | **MATCH** |
| 28 | **Overall DQ Compliance %** | `100.0%` | `100.0%` | `0.00%` | **MATCH** |

---

## 5. Automated Test Suite Execution

### 5.1 Power BI Semantic Model Suite
`pytest powerbi/tests/test_powerbi_semantic_model.py -v`
```text
test_semantic_model_json_schema                                 PASSED [ 11%]
test_dax_measure_file_completeness                              PASSED [ 22%]
test_dax_measure_ground_truth_reconciliation                    PASSED [ 33%]
test_generated_pbip_project_artifacts                           PASSED [ 44%]
test_semantic_model_mutual_exclusivity_rejection                PASSED [ 55%]
test_relationship_cross_filtering_behavior_regression           PASSED [ 66%]
test_report_visual_queries_and_projections_populated            PASSED [ 77%]
test_report_visual_placeholder_rejection_regression             PASSED [ 88%]
test_semantic_model_compatibility_level_downgrade_rejection     PASSED [100%]
============================== 9 passed in 1.10s ==============================
```

### 5.2 Full Repository Test Suite
`pytest` across warehouse, QA, servicing, generation, ingestion, quality, and powerbi:
```text
warehouse\tests\test_database_schema.py .....                            [  8%]
testing_qa\financial_calculations\test_accruals_math.py .....            [ 16%]
testing_qa\functional\test_loan_lifecycle.py ....                        [ 23%]
testing_qa\reconciliation\test_reconciliation_engine.py ....             [ 30%]
ingestion\fred\test_fred_ingestion.py .....                              [ 38%]
generation\test_generation.py ........                                   [ 51%]
servicing\test_servicing.py ........                                     [ 65%]
quality\tests\test_defect_injection.py .......                           [ 76%]
quality\tests\test_phase3.py .....                                       [ 85%]
powerbi\tests\test_powerbi_semantic_model.py .........                   [100%]
============================= 60 passed in 52.74s =============================
```

---

## 6. Data Provenance & Architectural Boundaries

To maintain rigorous analytical governance and integrity, the data elements in FinSight Enterprise are categorized by origin:

1. **Real Macroeconomic Data (FRED API):**
   * Sourced directly from the Federal Reserve Bank of St. Louis (FRED) API.
   * Key indicators: US Consumer Price Index (CPI), Unemployment Rate, Effective Federal Funds Rate, Real GDP, 10-Year Treasury Yield, and 30-Year Mortgage Rate.
   * Represents actual US macroeconomic historical time series.
2. **Statistically Modeled Lending & Borrower Data (Synthetic):**
   * 2,500 borrower profiles and loan facilities generated through parametric statistical distributions conforming to standard banking credit characteristics (prime, near-prime, commercial SME).
   * **Explicit Disclosure:** Does NOT represent real bank customer personally identifiable information (PII) or confidential financial records.
3. **Calculated Servicing & Financial Ledger Data:**
   * 14,741 payment transactions and 4,984 General Ledger double-entry postings generated via strict financial accounting rules (standard amortization equations, daily accruals, and cash flow allocation hierarchies).
4. **Intentionally Injected QA Testing Defects:**
   * 600 synthetic defect instances intentionally introduced in Phase 3 to evaluate reconciliation controls, automated regression testing, and data governance detection capabilities.
   * Includes interest calculation roundings, fee timing anomalies, and statement variance exposure ($901,738.50).

---

## 7. Known Limitations & Operational Boundary

1. **Development & Prototyping Environment:**
   * This project is structured as an automated desktop PBIP portfolio project for validation and engineering demonstration; it is **not** deployed to a live multi-tenant Power BI Service cloud tenant.
2. **Local Storage Coupling:**
   * The Tabular M expressions import Gold data from local file system paths (`C:/Users/.../data/processed/analytics/*.parquet`). Deploying to cloud Fabric would require migrating these partitions to OneLake Delta tables or Azure Data Lake Storage (ADLS Gen2).
3. **Auto Date/Time Hierarchy:**
   * Power BI Desktop automatically creates internal `LocalDateTable_*` helper tables unless globally disabled in Power BI Desktop options. These tables do not interfere with the Kimball star schema or DAX measures.

---

## 8. Final QA Determination

| Requirement | Audit Result | Status |
|---|---|:---:|
| PBIP Project Opens in Power BI Desktop | Opens without error; engine loads `<ddl200:CompatibilityLevel>1606</ddl200:CompatibilityLevel>` | **PASS** |
| Semantic Model Loads Cleanly | 11 core tables + 13 relationships loaded into Analysis Services Tabular | **PASS** |
| 6 Report Pages Exist | All 6 business pages configured and present | **PASS** |
| 48 Visuals Populated | All 48 visual containers have complete projection and query bindings | **PASS** |
| Control Totals Reconciled | 28 / 28 financial and risk control metrics reconcile with 0.00 variance | **PASS** |
| Test Suites Passing | 9 / 9 Power BI tests pass; 60 / 60 repository tests pass | **PASS** |
| **Overall Status** | **ALL VALIDATION GATES SATISFIED** | **PASS** |
