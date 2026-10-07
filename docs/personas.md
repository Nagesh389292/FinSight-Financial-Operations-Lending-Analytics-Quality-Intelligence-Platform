# FinSight Enterprise — Stakeholder Personas & Decision Archetypes

---

### 1. Persona Matrix Overview

FinSight Enterprise serves six distinct stakeholder personas across executive management, lending operations, accounting, quality engineering, business analysis, and platform engineering.

```
                  ┌───────────────────────────────┐
                  │          CFO / CCO            │
                  │   Executive Strategy & Risk   │
                  └──────────────┬────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  Loan Servicing  │   │     Financial    │   │  Quality Arch. / │
│ Operations Lead  │   │  Controller/Acct │   │   QA Lead (QE)   │
└────────┬─────────┘   └────────┬─────────┘   └────────┬─────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
         ┌──────────────────────┴──────────────────────┐
         ▼                                             ▼
┌──────────────────────────────┐              ┌──────────────────────────────┐
│  Business Systems Analyst    │              │  Data Platform SRE &         │
│  (BRD, Traceability, Rules)  │              │  Governance Officer          │
└──────────────────────────────┘              └──────────────────────────────┘
```

---

### 2. Detailed Stakeholder Profiles

#### 2.1. Chief Financial Officer & Chief Credit Officer (CFO / CCO)
- **Primary Goal**: Portfolio profitability, capital adequacy, credit risk mitigation, and strategic growth.
- **Key Pain Points**:
  - Lack of timely visibility into net interest margin (NIM) trends and portfolio delinquency.
  - Inability to dynamically simulate interest rate spikes or macroeconomic recessions.
  - Exposure to audit fines from financial misstatements or accounting variance leakages.
- **Core Questions Answered by FinSight**:
  - *What is our total active loan portfolio value and weighted-average interest yield?*
  - *What is the projected net interest income for the upcoming 3–6 months?*
  - *How would a 100 bps SOFR rate hike or a 2% rise in default rates affect portfolio net income?*
- **Primary Interface**: Power BI Page 1 (Executive Portfolio Overview) & Page 5 (Scenario Stress Planner).

---

#### 2.2. Loan Servicing & Operations Manager
- **Primary Goal**: Flawless loan onboarding, lifecycle servicing, payment execution, and delinquency management.
- **Key Pain Points**:
  - Unclear payment waterfalls (unapplied funds, misallocated principal vs. interest vs. late fees).
  - Difficulty tracking loans transitioning through delinquency buckets (30, 60, 90+ Days Past Due - DPD).
  - Manual, error-prone servicing adjustments and borrower payoff calculations.
- **Core Questions Answered by FinSight**:
  - *Which loans failed payment processing or resulted in short payments this billing cycle?*
  - *How many loans rolled from Current to 30+ DPD this month?*
  - *What is the exact amortization schedule and current closing balance for Loan `L-74829`?*
- **Primary Interface**: FastAPI Servicing Endpoints, Power BI Page 2 (Lending Operations & Servicing).

---

#### 2.3. Financial Controller & Accruals Accounting Lead
- **Primary Goal**: Strict accounting integrity, balance sheet accuracy, General Ledger (GL) balance reconciliation, and compliance with US GAAP / IFRS 9.
- **Key Pain Points**:
  - Daily accrual drift: loan servicing calculations diverging from GL expectation.
  - Inconsistent day-count conventions (`30/360` vs `Actual/360` vs `Actual/365`) applied across facilities.
  - Tedious month-end manual reconciliation spreadsheets that delay closing by days.
- **Core Questions Answered by FinSight**:
  - *Are all processed daily interest and fee accruals within $0.00 variance of expected mathematical models?*
  - *Which loans breached the reconciliation variance threshold ($\ge \$1.00$) this cycle?*
  - *Are our recognized interest income and accrued interest receivable accounts balanced?*
- **Primary Interface**: Power BI Page 3 (Financial Performance & Accrual Reconciliation), Automated Reconciliation Engine.

---

#### 2.4. Lead Quality Engineer & Lending Test Architect (Genpact Alignment)
- **Primary Goal**: Continuous test automation, mathematical calculation certification, regression defense, and defect resolution.
- **Key Pain Points**:
  - Absence of automated regression suites validating complex banking calculation algorithms.
  - Disconnect between business requirements and actual test case assertions.
  - High risk of silent regressions during software releases, core banking patches, or platform migrations.
- **Core Questions Answered by FinSight**:
  - *What is the automated test pass rate across functional, financial, and integration test suites?*
  - *Which test cases failed during nightly regression, and which requirements do they violate?*
  - *What are the open defects, their root causes, and their severity levels?*
- **Primary Interface**: Pytest Test Framework, Web QA & Certification Console, Power BI Page 4 (Quality & Testing Intelligence).

---

#### 2.5. Business / Financial Systems Analyst (Genpact Alignment)
- **Primary Goal**: Translating banking business operations into unambiguous technical requirements, maintaining the Requirements Traceability Matrix (RTM), and validating implementation behavior.
- **Key Pain Points**:
  - Untracked requirement changes leading to gaps in QA test coverage.
  - Vague business rules around loan modifications, grace periods, and compounding methods.
  - Difficulty communicating technical calculation bugs back to business sponsors.
- **Core Questions Answered by FinSight**:
  - *Is every requirement in BRD-CORE, BRD-FIN, and BRD-QA tied to an active, passing test case?*
  - *What business rule governs interest calculation when a borrower makes an unscheduled prepayment?*
  - *What is the historical audit trail for requirement changes and defect resolutions?*
- **Primary Interface**: Requirements Traceability Matrix (RTM), Data Dictionary & Business Rules Repository.

---

#### 2.6. Data Platform SRE & Governance Lead (IQVIA Alignment)
- **Primary Goal**: Platform uptime, data freshness, pipeline reliability, role-based access control (RBAC), and regulatory audit logging.
- **Key Pain Points**:
  - Upstream data feed failures or schema drift causing silent pipeline breaks.
  - Lack of immutable audit trails for unauthorized data overrides or configuration changes.
  - Unclear data ownership and lack of automated alerts when data quality rules fail.
- **Core Questions Answered by FinSight**:
  - *Did all daily ETL, reconciliation, and model training pipelines finish within their scheduled SLAs?*
  - *Are there any data quality anomalies (null primary keys, negative balances, orphaned foreign keys)?*
  - *Who initiated and authorized the latest batch recalculation or configuration update?*
- **Primary Interface**: Power BI Page 6 (Data Quality & Platform Operations), Prometheus/Structured Audit Logs, FastAPI `/health` & `/audit` endpoints.
