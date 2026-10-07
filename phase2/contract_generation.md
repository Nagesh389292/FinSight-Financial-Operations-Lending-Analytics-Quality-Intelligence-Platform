# FinSight Enterprise — Stage 2.2: Deterministic Reference & Contract Generator

## Executive Summary
Stage 2.2 implements a deterministic, rule-governed synthetic loan contract generation engine anchored to authoritative macroeconomic benchmarks (FRED SOFR and Prime Rate) and aligned with FinSight's Phase 1 database schema (`core.customers`, `core.loan_products`, `core.loans`, and `core.loan_terms`).

Following the senior architectural instruction:
1. **Validation Gate First**: We implemented a deterministic 100-loan validation batch first to rigorously prove all business rules, referential integrity constraints, rate logic, and reproducibility.
2. **Production Scale**: Upon passing all validation gates and automated test suites, the engine scaled to **2,500 master loan facilities**, **2,500 customer profiles**, and **2,500 contractual loan terms**.
3. **Clean Contracts Only**: Zero defects were injected in Stage 2.2. All facilities are originated in `CURRENT` servicing status with zero delinquency (`days_past_due = 0`). Controlled defects (`DAY_COUNT_MISMATCH`, `ROUNDING_TRUNCATION`, `WATERFALL_ORDERING`, `LEAP_YEAR_BLINDNESS`) are strictly reserved for Stage 2.4.

---

## 1. Architectural Pipeline

```text
                    FRED Bronze Data (Stage 2.1)
                                │
                     ┌──────────┴──────────┐
                     │                     │
                  SOFR                  DPRIME
                     │                     │
                     └──────────┬──────────┘
                                ▼
                     ┌─────────────────────┐
                     │ Reference Generator │
                     └──────────┬──────────┘
                                │
                    ┌───────────┼────────────┐
                    ▼           ▼            ▼
                Customers   Products     Reference Data
                    │           │
                    └──────┬────┘
                           ▼
                   Contract Generator
                           │
                           ▼
                     core.loans
                           │
                           ▼
                    core.loan_terms
```

---

## 2. Controlled Borrower Profiles (`core.customers`)

Borrower generation enforces **controlled realism** rather than arbitrary random values:
- Fixed Random Seed: `seed = 20261006` ensures bit-for-bit reproducibility.
- Risk Alignment: Credit scores directly dictate risk tier (`PRIME` vs. `SUBPRIME`), eligible loan products, and contractual risk spreads (+50 bps for subprime).
- Segments:
  - `COMMERCIAL`: Corporate entities with annual revenues from $5M to $50M, low DTI, high credit scores, eligible for Revolvers and Commercial Term facilities.
  - `SME`: Small & Medium enterprises with revenues from $250k to $5M, eligible for SME Working Capital and Commercial Term facilities.
  - `RETAIL`: Individual consumers with incomes from $45k to $250k, eligible for Consumer Installment and Residential Mortgages.

---

## 3. Authoritative Loan Products (`core.loan_products`)

The 5 enterprise banking products established in Phase 1:

| Product Code | Product Name | Family | Rate Type | Benchmark | Day-Count Convention | Default Amortization | Term Range |
|---|---|---|---|---|---|---|---|
| `COMM_REV` | Commercial Revolver | COMMERCIAL | FLOATING | SOFR | `ACTUAL/360` | INTEREST_ONLY | 12 – 60 mos |
| `COMM_TERM` | Commercial Term Loan | COMMERCIAL | FLOATING | SOFR | `ACTUAL/360` | AMORTIZING | 24 – 120 mos |
| `SME_WC` | SME Working Capital | SME | FLOATING | DPRIME | `ACTUAL/360` | AMORTIZING | 6 – 36 mos |
| `CONS_INST` | Consumer Installment | RETAIL | FIXED | *NULL* | `ACTUAL/365` | AMORTIZING | 12 – 84 mos |
| `MORT_RES` | Residential Mortgage | RETAIL | FIXED | *NULL* | `30/360` | AMORTIZING | 180 – 360 mos |

---

## 4. Contract Rate & Day-Count Convention Logic

### 4.1 Interest Rate Composition
1. **Floating-Rate Contracts**:
   $$\text{Contract Rate} = \text{Benchmark Rate (SOFR / DPRIME)} + \text{Contractual Margin Spread} + \text{Risk Adjustment}$$
   - Benchmark rate is ingested from real FRED macroeconomic series (e.g., SOFR ~4.30%, Prime ~8.00%).
   - Contractual margin: e.g., SOFR + 225 bps, DPRIME + 175 bps.
2. **Fixed-Rate Contracts**:
   $$\text{Contract Rate} = \text{Fixed Base Rate} + \text{Risk Adjustment}$$
   - Benchmark is strictly set to `NULL`.

### 4.2 Explicit Day-Count Conventions
To support high-precision financial reconciliation and later QA defect detection, conventions are explicitly defined per product:
- **Actual/360**: $\text{Daily Accrual} = P \times R \times \frac{1}{360}$ (Commercial Revolvers, Commercial Term, SME Working Capital).
- **Actual/365**: $\text{Daily Accrual} = P \times R \times \frac{1}{365}$ (Consumer Installment).
- **30/360 (Bond Basis)**: $\text{Monthly Accrual} = P \times R \times \frac{30}{360}$ (Residential Mortgages).

---

## 5. Automated Validation Gates & Test Suite

All generated batches must pass through programmatic validation gates (`generation/validators.py`) before persistence:

1. **Referential Integrity**:
   - Every `loan.customer_id` maps to an existing record in `customers`.
   - Every `loan.product_code` maps to an existing record in `loan_products`.
   - Every `loan_term.loan_id` maps 1:1 to an existing record in `loans`.
2. **Financial Bounds**:
   - `principal_original > 0` and within product-specific `[min_principal, max_principal]`.
   - `interest_rate_annual > 0` and within realistic enterprise lending bounds (3.0% – 25.0%).
   - `term_months > 0` and `maturity_date > start_date`.
3. **Rate & Day-Count Logic**:
   - `FIXED` rate contracts must have `benchmark_index IS NULL`.
   - `FLOATING` rate contracts must have `benchmark_index IN ('SOFR', 'DPRIME')` and `margin_spread_bps > 0`.
   - `interest_method` must strictly belong to `{'ACTUAL/360', 'ACTUAL/365', '30/360'}`.
4. **Reproducibility Test**:
   - Executing generation twice with seed `20261006` produces exact bit-for-bit identical DataFrames across all columns and rows (`test_generation_reproducibility` PASSED).

---

## 6. Generation Summary (Production Batch: 2,500 Contracts)

```json
{
  "random_seed": 20261006,
  "loan_count": 2500,
  "customer_count": 2500,
  "product_count": 5,
  "floating_loans_count": 837,
  "fixed_loans_count": 1663,
  "total_portfolio_principal_usd": 4083242991.87,
  "avg_interest_rate_pct": 7.9765,
  "validation_status": "PASSED",
  "injected_defects_count": 0
}
```

### Parquet Storage Artifacts
Generated files saved in `data/generated/contracts/`:
- `customers.parquet` (2,500 records, 70.1 KB)
- `loans.parquet` (2,500 records, 100.2 KB)
- `loan_terms.parquet` (2,500 records, 49.3 KB)
- `generation_summary.json` (Audit metadata)

---

## 7. Test Suite Status
- Total Passing Tests: **31 / 31 passed**
  - Database Schema & DDL: 5/5
  - QA Financial Calculations & Waterfalls: 9/9
  - QA Reconciliation Engine: 4/4
  - FRED Economic Ingestion: 5/5
  - Deterministic Contract Generation & Integrity: 8/8
