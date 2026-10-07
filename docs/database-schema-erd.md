# FinSight Enterprise — Database Schema Specification & Entity Relationship Diagrams (ERD)

---

### 1. High-Level Schema Architecture

FinSight Enterprise organizes its database into five logical schemas adhering to a dual OLTP (3NF Operational) and OLAP (Kimball Star Schema) architecture:

```mermaid
graph TD
    subgraph S_CORE["core Schema (OLTP Master Entities)"]
        CUST["core.customers"]
        PROD["core.loan_products"]
        LOANS["core.loans"]
        TERMS["core.loan_terms"]
    end

    subgraph S_FIN["finance Schema (OLTP Transactions & Accruals)"]
        PMT["finance.payments"]
        ALLOC["finance.payment_allocations"]
        ACCR["finance.interest_accruals"]
        ENT["finance.accounting_entries"]
        LINES["finance.accounting_entry_lines"]
        REC["finance.reconciliation_results"]
    end

    subgraph S_QA["qa Schema (Quality Engineering & RTM)"]
        REQ["qa.requirements"]
        RULES["qa.business_rules"]
        TC["qa.test_cases"]
        EXEC["qa.test_executions"]
        DEF["qa.defects"]
        RTM["qa.requirement_test_mapping"]
    end

    subgraph S_GOV["governance Schema (Security & Auditability)"]
        ROLES["governance.roles"]
        PERMS["governance.permissions"]
        USERS["governance.users"]
        AUDIT["governance.audit_log"]
        DQ["governance.data_quality_results"]
    end

    subgraph S_ANALYTICS["analytics Schema (OLAP Kimball Star Schema)"]
        D_DATE["analytics.dim_date"]
        D_CUST["analytics.dim_customer"]
        D_PROD["analytics.dim_product"]
        D_LOAN["analytics.dim_loan"]
        F_PERF["analytics.fact_loan_performance"]
        F_PMT["analytics.fact_payment"]
        F_FIN["analytics.fact_financial"]
        F_QA["analytics.fact_test_execution"]
        F_DEF["analytics.fact_defect"]
        F_DQ["analytics.fact_data_quality"]
    end

    CUST --> LOANS
    PROD --> LOANS
    LOANS --> TERMS
    LOANS --> PMT
    PMT --> ALLOC
    LOANS --> ACCR
    LOANS --> REC

    REQ --> RULES
    RULES --> TC
    TC --> EXEC
    RULES --> DEF
    REQ & TC --> RTM

    ROLES --> USERS
    PERMS --> ROLES

    D_DATE & D_CUST & D_PROD & D_LOAN --> F_PERF
    D_DATE & D_CUST & D_PROD & D_LOAN --> F_PMT
    D_DATE & D_PROD --> F_FIN
    D_DATE --> F_QA & F_DEF & F_DQ
```

---

### 2. Operational Schema ERD (`core` & `finance`)

```mermaid
erDiagram
    customers ||--o{ loans : "originates"
    loan_products ||--o{ loans : "governs"
    loans ||--|| loan_terms : "defines terms"
    loans ||--o{ payments : "receives"
    payments ||--|{ payment_allocations : "breaks down"
    loans ||--o{ interest_accruals : "accrues daily"
    loans ||--o{ reconciliation_results : "audited by"
    accounting_entries ||--|{ accounting_entry_lines : "contains"

    customers {
        varchar customer_id PK
        varchar legal_name
        varchar customer_type
        varchar region
        varchar segment
        varchar risk_category
        int credit_score
        numeric annual_income
        numeric debt_to_income_ratio
    }

    loan_products {
        varchar product_code PK
        varchar product_name
        varchar product_family
        varchar rate_type
        varchar interest_method
        varchar default_amortization
        varchar benchmark_index
        int base_spread_bps
    }

    loans {
        varchar loan_id PK
        varchar customer_id FK
        varchar product_code FK
        varchar status
        numeric principal_original
        numeric principal_outstanding
        numeric interest_rate_annual
        int term_months
        date start_date
        date maturity_date
        int days_past_due
        varchar servicing_status
    }

    loan_terms {
        varchar term_id PK
        varchar loan_id FK
        varchar rate_type
        varchar interest_method
        varchar amortization_schedule
        varchar benchmark_index
        int margin_spread_bps
        int grace_period_days
    }

    payments {
        varchar payment_id PK
        varchar loan_id FK
        date payment_date
        numeric payment_amount
        varchar payment_method
        varchar status
    }

    payment_allocations {
        bigserial allocation_id PK
        varchar payment_id FK
        varchar loan_id FK
        numeric principal_amount
        numeric interest_amount
        numeric fees_amount
        numeric prepayment_amount
        numeric total_allocated
        numeric closing_principal_balance
    }

    interest_accruals {
        bigserial accrual_id PK
        varchar loan_id FK
        date accrual_date
        numeric start_principal_balance
        numeric interest_rate_annual
        varchar interest_method
        numeric interest_accrual_amount
        numeric cumulative_unpaid_interest
    }

    reconciliation_results {
        varchar reconciliation_id PK
        varchar loan_id FK
        date cycle_date
        varchar reconciliation_type
        numeric expected_amount
        numeric actual_amount
        numeric variance_amount
        varchar status
        varchar root_cause_category
    }
```

---

### 3. Quality Assurance & RTM Schema ERD (`qa`)

```mermaid
erDiagram
    requirements ||--o{ business_rules : "translates to"
    business_rules ||--o{ test_cases : "tested by"
    test_cases ||--o{ test_executions : "executes"
    requirements ||--o{ requirement_test_mapping : "mapped in RTM"
    test_cases ||--o{ requirement_test_mapping : "mapped in RTM"
    business_rules ||--o{ defects : "violates"
    test_cases ||--o{ defects : "identified by"

    requirements {
        varchar requirement_id PK
        varchar module
        varchar title
        text description
        varchar business_owner
        varchar priority
        varchar status
    }

    business_rules {
        varchar rule_id PK
        varchar requirement_id FK
        varchar rule_name
        varchar domain
        text rule_statement
        varchar tolerance_spec
    }

    test_cases {
        varchar test_case_id PK
        varchar rule_id FK
        varchar test_category
        varchar test_name
        varchar target_component
        boolean is_automated
    }

    test_executions {
        bigserial execution_id PK
        varchar run_id
        varchar test_case_id FK
        varchar status
        numeric duration_ms
        text assertion_message
    }

    defects {
        varchar defect_id PK
        varchar test_case_id FK
        varchar rule_id FK
        varchar title
        varchar severity
        varchar priority
        varchar status
        numeric variance_amount
        varchar root_cause_category
    }

    requirement_test_mapping {
        bigserial mapping_id PK
        varchar requirement_id FK
        varchar rule_id FK
        varchar test_case_id FK
        varchar coverage_type
    }
```

---

### 4. Dimensional Star Schema ERD (`analytics`)

```mermaid
erDiagram
    dim_date ||--o{ fact_loan_performance : "snapshots on"
    dim_customer ||--o{ fact_loan_performance : "borrows"
    dim_product ||--o{ fact_loan_performance : "categorizes"
    dim_loan ||--o{ fact_loan_performance : "tracks"
    dim_date ||--o{ fact_payment : "received on"
    dim_loan ||--o{ fact_payment : "paid towards"
    dim_date ||--o{ fact_test_execution : "tested on"
    dim_date ||--o{ fact_defect : "logged on"
    dim_date ||--o{ fact_data_quality : "evaluated on"

    dim_date {
        int date_key PK
        date full_date
        int calendar_year
        int calendar_quarter
        varchar quarter_name
        int month_number
        varchar month_name
        varchar year_month
    }

    dim_customer {
        bigserial customer_key PK
        varchar customer_id
        varchar legal_name
        varchar customer_type
        varchar region
        varchar segment
        varchar credit_tier
    }

    dim_product {
        bigserial product_key PK
        varchar product_code
        varchar product_name
        varchar product_family
        varchar rate_type
        varchar interest_method
    }

    dim_loan {
        bigserial loan_key PK
        varchar loan_id
        numeric original_principal
        numeric annual_interest_rate
        int term_months
    }

    fact_loan_performance {
        bigserial performance_key PK
        int date_key FK
        bigint customer_key FK
        bigint product_key FK
        bigint loan_key FK
        varchar loan_id
        varchar status
        numeric outstanding_principal
        numeric accrued_interest
        int days_past_due
        boolean is_delinquent_30_plus
        boolean is_default_90_plus
    }

    fact_payment {
        bigserial payment_key PK
        int date_key FK
        bigint customer_key FK
        bigint product_key FK
        bigint loan_key FK
        numeric payment_amount
        numeric principal_applied
        numeric interest_applied
    }

    fact_test_execution {
        bigserial qa_fact_key PK
        int date_key FK
        varchar run_id
        varchar test_category
        int total_tests_executed
        int tests_passed
        int tests_failed
        numeric pass_rate_pct
    }

    fact_defect {
        bigserial defect_key PK
        int date_key FK
        varchar defect_id
        varchar severity
        varchar priority
        varchar status
        varchar root_cause_category
        numeric variance_amount
    }

    fact_data_quality {
        bigserial dq_fact_key PK
        int date_key FK
        varchar check_category
        int total_rules_evaluated
        int rules_passed
        numeric overall_compliance_pct
    }
```

---

### 5. Data Integrity & Constraint Rules

1. **Exact Currency Representation**: All monetary values use `NUMERIC(18, 4)` to guarantee exact decimal arithmetic and eliminate IEEE 754 floating-point rounding errors.
2. **Balanced Double-Entry Accounting**: `finance.accounting_entries` enforces `total_debit = total_credit` via check constraint.
3. **Cash Conservation in Payment Waterfall**: `finance.payment_allocations` strictly enforces `total_allocated = (principal_amount + interest_amount + fees_amount + prepayment_amount)`.
4. **Credit Score Bounds**: `core.customers` check constraint guarantees `credit_score BETWEEN 300 AND 850`.
5. **Requirements to Test Traceability**: Unique constraint on `qa.requirement_test_mapping(requirement_id, test_case_id)` enforces non-duplicate RTM mapping.
