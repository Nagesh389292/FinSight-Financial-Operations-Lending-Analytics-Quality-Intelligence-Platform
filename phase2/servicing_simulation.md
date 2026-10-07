# FinSight Enterprise — Stage 2.3: Servicing Simulation Engine

## Executive Summary
Stage 2.3 establishes the **authoritative lending servicing simulation baseline** for FinSight Enterprise. In accordance with the project roadmap, Stage 2.3 operates strictly on the clean loan contracts produced in Stage 2.2, executing the full operational lifecycle:
1. **Contractual Schedule Generation**
2. **Multi-Convention Daily/Period Accruals**
3. **Controlled Servicing Payment Execution**
4. **Waterfall Cash Allocation**
5. **Date-Driven DPD & Aging Classification**
6. **Double-Entry General Ledger Accounting**
7. **Dual-Path Financial Reconciliation**

Crucially, **zero intentional defects were injected in Stage 2.3**. This establishes the 100% verified clean baseline against which Stage 2.4 will inject controlled defects (`DAY_COUNT_MISMATCH`, `ROUNDING_TRUNCATION`, `WATERFALL_ORDERING`, `LEAP_YEAR_BLINDNESS`) to prove the QA and reconciliation engine.

---

## 1. Architectural Pipeline & Boundary Freeze

```text
                 2.2 COMPLETE
              Clean Loan Contracts
                       │
                       ▼
              ┌─────────────────┐
              │ 2.3 SERVICING   │
              │     ENGINE      │
              └────────┬────────┘
                       │
       ┌───────────────┼────────────────┐
       ▼               ▼                ▼
 Payment Schedule   Daily Accrual    Billing
       │               │                │
       └───────────────┼────────────────┘
                       ▼
                Payment Execution
                       │
                       ▼
                Payment Waterfall
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       Loan Sub-ledger       DPD/Aging
             │                   │
             └─────────┬─────────┘
                       ▼
                 GL Journals
                       │
                       ▼
               Reconciliation
                       │
                       ▼
                  PASS / FAIL
```

---

## 2. Component Implementation & Business Rules

### 2.3.1 Contractual Schedule Engine (`servicing/schedule_engine.py`)
- **Inputs**: `core.loans` and `core.loan_terms` (2,500 facilities).
- **Function**: Prior to any payment simulation, generates periodic billing schedules for each facility across 6 simulated monthly cycles (15,000 scheduled periods).
- **Formulas**:
  - `INTEREST_ONLY_BALLOON`: Scheduled principal = $0.00 until maturity; interest on opening balance.
  - `AMORTIZING_FIXED_PRINCIPAL`: Fixed monthly principal $P_{\text{orig}} / \text{term\_months}$; interest on remaining balance.
  - `AMORTIZING_EQUAL_INSTALLMENT`: Constant periodic payment formula $PMT = P \times \frac{r(1+r)^n}{(1+r)^n - 1}$.
- **Invariant**:
  $$\text{total\_amount\_due} = \text{scheduled\_principal} + \text{scheduled\_interest} + \text{fees}$$
  $$\text{closing\_principal} = \text{opening\_principal} - \text{scheduled\_principal}$$

### 2.3.2 Daily Accrual Engine (`servicing/accrual_engine.py`)
- **Conventions Supported**:
  - `ACTUAL/360`: $\text{Interest} = P \times R \times \frac{\text{Actual Days}}{360}$
  - `ACTUAL/365`: $\text{Interest} = P \times R \times \frac{\text{Actual Days}}{365}$ (ISDA Actual/365 Fixed standard)
  - `30/360`: $\text{Interest} = P \times \frac{R}{12}$ (Standard 30-day month / 360-day year)
- **Explainability**: Every accrual record stores `loan_id`, `accrual_date`, `opening_balance`, `annual_rate`, `day_count_convention`, `day_count`, `day_fraction`, `interest_amount`, `fee_amount`, and `closing_balance`.

### 2.3.3 Payment Execution Simulation (`servicing/payment_execution.py`)
- Simulates realistic borrower servicing behaviors using deterministic seed `20261006`:
  - `ON_TIME` (~82%): Paid on due date, full scheduled amount.
  - `LATE` (~8%): Paid 5–45 days late; contractual late fee assessed ($5\%$ of payment due, minimum $\$25.00$).
  - `EARLY` (~5%): Paid 2–10 days early with additional unscheduled principal prepayment ($10\%–25\%$).
  - `PARTIAL` (~3%): Partial cash payment ($50\%–85\%$ of due amount).
  - `MISSED` (~2%): Zero cash received; late fee assessed; triggers delinquency aging.
- Output: 14,741 payment receipts ($351,574,751.19 total volume).

### 2.3.4 Payment Waterfall Engine (`servicing/waterfall_engine.py`)
- Enforces explicit BRD allocation priority:
  $$\text{Payment} \longrightarrow \text{Fees Due} \longrightarrow \text{Interest Due} \longrightarrow \text{Scheduled Principal} \longrightarrow \text{Prepayment}$$
- **Strict Conservation Invariant**:
  $$\text{Total Allocated} = \text{Fees Allocation} + \text{Interest Allocation} + \text{Principal Allocation} + \text{Prepayment Allocation} \equiv \text{Payment Amount}$$
- 100% of the 14,741 waterfall allocations satisfy this conservation identity down to the exact cent.

### 2.3.5 DPD & Delinquency Aging Engine (`servicing/dpd_engine.py`)
- Calculated strictly from date arithmetic:
  $$\text{DPD} = \begin{cases} \max(0, (\text{Payment Date} - \text{Due Date}).\text{days}) & \text{if paid} \\ \max(0, (\text{As-Of Date} - \text{Due Date}).\text{days}) & \text{if unpaid} \end{cases}$$
- Regulatory Aging Classification:
  - `CURRENT` (DPD = 0): 13,517 cycle periods
  - `BUCKET_1` (1–29 DPD): 758 cycle periods
  - `BUCKET_2` (30–59 DPD): 468 cycle periods
  - `BUCKET_3` (60–89 DPD): 3 cycle periods
  - `DEFAULT` (90+ DPD): 254 cycle periods

### 2.3.6 General Ledger Double-Entry Engine (`servicing/gl_engine.py`)
- Automatically generates balanced double-entry accounting entries for every subledger event:
  - `DAILY_ACCRUAL`: DR 12100 (Interest Receivable) / CR 40100 (Interest Income)
  - `FEE_ASSESSMENT`: DR 12200 (Fees Receivable) / CR 40200 (Fee Income)
  - `PAYMENT_RECEIPT`: DR 10100 (Cash) / CR 12000 (Loans Receivable), CR 12100 (Interest Receivable), CR 12200 (Fees Receivable)
- **Fundamental Invariant**:
  $$\sum \text{Debits} = \$491,300,436.35 \equiv \sum \text{Credits} = \$491,300,436.35 \quad (\text{BALANCED})$$

### 2.3.7 Financial Reconciliation Engine (`servicing/reconciliation_engine.py`)
- Implements ADR-003 dual-path financial validation:
  1. `INTEREST_ACCRUAL`: Operational accruals vs. `MathematicalTruthEngine` benchmark ($15,000$ checks)
  2. `PRINCIPAL_REDUCTION`: Operational principal allocations vs. contractual waterfall truth ($14,741$ checks)
  3. `GL_SUBLEDGER_TIE_OUT`: Subledger principal collections vs. GL Account 12000 credits ($1$ tie-out check)
- **Results**: **29,742 / 29,742 checks passed (100.0% Pass Rate)** with zero failures.

---

## 3. Stage 2.3 Acceptance Gates Verification

| Gate | Target | Result | Status |
|---|---:|---:|:---:|
| **Schedule Generation** | 100% valid | 15,000 / 15,000 periods valid | ✅ PASS |
| **Accrual Calculation** | 100% rule-compliant | ACTUAL/360, ACTUAL/365, 30/360 matched | ✅ PASS |
| **Payment Conservation** | 100% | $\sum \text{Allocations} = \text{Payment}$ (14,741 / 14,741) | ✅ PASS |
| **Waterfall Allocation** | 100% | Fees $\rightarrow$ Interest $\rightarrow$ Principal $\rightarrow$ Prepayment | ✅ PASS |
| **DPD Calculation** | From dates | Strict date arithmetic verified | ✅ PASS |
| **GL Double-Entry Balance** | $\Sigma \text{DR} = \Sigma \text{CR}$ | DR \$491,300,436.35 == CR \$491,300,436.35 | ✅ PASS |
| **Reconciliation Consistency** | 100% pass | 29,742 / 29,742 checks passed | ✅ PASS |
| **Intentional Defects** | 0 at this stage | 0 defects (Clean baseline established) | ✅ PASS |
| **Reproducibility Test** | Bit-for-bit | Run A == Run B verified | ✅ PASS |
| **Automated Test Suite** | All pass | **39 / 39 tests passed** | ✅ PASS |

---

## 4. Persisted Parquet Artifacts

Stored in `data/generated/servicing/`:
- `payment_schedules.parquet` (15,000 records, 630 KB)
- `interest_accruals.parquet` (15,000 records, 594 KB)
- `payments.parquet` (14,741 records, 427 KB)
- `payment_allocations.parquet` (14,741 records, 595 KB)
- `delinquency_cycles.parquet` (15,000 records, 87 KB)
- `accounting_entries.parquet` (31,224 records, 800 KB)
- `accounting_entry_lines.parquet` (76,943 records, 1.54 MB)
- `reconciliation_results.parquet` (29,742 records, 663 KB)
- `updated_loans.parquet` (2,500 records, 102 KB)
- `servicing_summary.json` (Audit summary metadata)
