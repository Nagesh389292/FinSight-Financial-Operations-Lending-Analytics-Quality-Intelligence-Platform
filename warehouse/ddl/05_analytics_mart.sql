-- ============================================================================
-- FinSight Enterprise — Phase 1: Database DDL
-- Script 05: Dimensional Analytics Mart Schema (analytics - Kimball Star Schema)
-- Dimensions: dim_date, dim_customer, dim_loan, dim_product
-- Facts: fact_loan_performance, fact_payment, fact_financial,
--        fact_test_execution, fact_defect, fact_data_quality
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS analytics;

-- 1. Date Dimension (Calendar & Fiscal Reporting Cycles)
CREATE TABLE IF NOT EXISTS analytics.dim_date (
    date_key                INT             PRIMARY KEY, -- Format: YYYYMMDD (e.g. 20240101)
    full_date               DATE            NOT NULL UNIQUE,
    calendar_year           INT             NOT NULL,
    calendar_quarter        INT             NOT NULL,
    quarter_name            VARCHAR(10)     NOT NULL, -- 'Q1 2024'
    month_number            INT             NOT NULL,
    month_name              VARCHAR(20)     NOT NULL,
    month_short             VARCHAR(3)      NOT NULL,
    year_month              VARCHAR(7)      NOT NULL, -- '2024-01'
    day_of_month            INT             NOT NULL,
    day_of_week             INT             NOT NULL,
    day_name                VARCHAR(15)     NOT NULL,
    is_weekend              BOOLEAN         NOT NULL,
    is_month_end            BOOLEAN         NOT NULL
);

-- 2. Conformed Customer Dimension
CREATE TABLE IF NOT EXISTS analytics.dim_customer (
    customer_key            BIGSERIAL       PRIMARY KEY,
    customer_id             VARCHAR(32)     NOT NULL UNIQUE,
    legal_name              VARCHAR(150)    NOT NULL,
    customer_type           VARCHAR(30)     NOT NULL,
    region                  VARCHAR(20)     NOT NULL,
    segment                 VARCHAR(30)     NOT NULL,
    risk_category           VARCHAR(20)     NOT NULL,
    credit_score            INT             NOT NULL,
    credit_tier             VARCHAR(25)     NOT NULL -- 'Excellent', 'Good', 'Fair', 'Subprime'
);

-- 3. Conformed Product Dimension
CREATE TABLE IF NOT EXISTS analytics.dim_product (
    product_key             BIGSERIAL       PRIMARY KEY,
    product_code            VARCHAR(32)     NOT NULL UNIQUE,
    product_name            VARCHAR(100)    NOT NULL,
    product_family          VARCHAR(30)     NOT NULL,
    rate_type               VARCHAR(20)     NOT NULL,
    interest_method         VARCHAR(20)     NOT NULL,
    default_amortization    VARCHAR(30)     NOT NULL,
    benchmark_index         VARCHAR(20)     NULL
);

-- 4. Conformed Loan Dimension
CREATE TABLE IF NOT EXISTS analytics.dim_loan (
    loan_key                BIGSERIAL       PRIMARY KEY,
    loan_id                 VARCHAR(32)     NOT NULL UNIQUE,
    customer_id             VARCHAR(32)     NOT NULL,
    product_code            VARCHAR(32)     NOT NULL,
    start_date              DATE            NOT NULL,
    maturity_date           DATE            NOT NULL,
    original_principal      NUMERIC(18, 4)  NOT NULL,
    annual_interest_rate    NUMERIC(8, 6)   NOT NULL,
    term_months             INT             NOT NULL,
    rate_type               VARCHAR(20)     NOT NULL,
    interest_method         VARCHAR(20)     NOT NULL
);

-- 5. Fact Table: Monthly Loan Performance Snapshot
CREATE TABLE IF NOT EXISTS analytics.fact_loan_performance (
    performance_key         BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    customer_key            BIGINT          NOT NULL REFERENCES analytics.dim_customer(customer_key),
    product_key             BIGINT          NOT NULL REFERENCES analytics.dim_product(product_key),
    loan_key                BIGINT          NOT NULL REFERENCES analytics.dim_loan(loan_key),
    loan_id                 VARCHAR(32)     NOT NULL,
    status                  VARCHAR(25)     NOT NULL,
    servicing_status        VARCHAR(20)     NOT NULL,
    outstanding_principal   NUMERIC(18, 4)  NOT NULL,
    scheduled_principal     NUMERIC(18, 4)  NOT NULL,
    accrued_interest        NUMERIC(18, 4)  NOT NULL,
    fees_due                NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000,
    total_due               NUMERIC(18, 4)  NOT NULL,
    days_past_due           INT             NOT NULL,
    is_delinquent_30_plus   BOOLEAN         NOT NULL DEFAULT FALSE,
    is_default_90_plus      BOOLEAN         NOT NULL DEFAULT FALSE
);

-- 6. Fact Table: Realized Payments Stream
CREATE TABLE IF NOT EXISTS analytics.fact_payment (
    payment_key             BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    customer_key            BIGINT          NOT NULL REFERENCES analytics.dim_customer(customer_key),
    product_key             BIGINT          NOT NULL REFERENCES analytics.dim_product(product_key),
    loan_key                BIGINT          NOT NULL REFERENCES analytics.dim_loan(loan_key),
    payment_id              VARCHAR(36)     NOT NULL,
    payment_amount          NUMERIC(18, 4)  NOT NULL,
    principal_applied       NUMERIC(18, 4)  NOT NULL,
    interest_applied        NUMERIC(18, 4)  NOT NULL,
    fees_applied            NUMERIC(18, 4)  NOT NULL,
    prepayment_applied      NUMERIC(18, 4)  NOT NULL,
    closing_principal_balance NUMERIC(18, 4) NOT NULL
);

-- 7. Fact Table: Financial & General Ledger Performance
CREATE TABLE IF NOT EXISTS analytics.fact_financial (
    financial_key           BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    product_key             BIGINT          NOT NULL REFERENCES analytics.dim_product(product_key),
    gl_account_code         VARCHAR(20)     NOT NULL,
    total_debit             NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000,
    total_credit            NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000,
    net_movement            NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000,
    ending_balance          NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000
);

-- 8. Fact Table: QA & Test Execution Intelligence
CREATE TABLE IF NOT EXISTS analytics.fact_test_execution (
    qa_fact_key             BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    run_id                  VARCHAR(64)     NOT NULL,
    test_category           VARCHAR(30)     NOT NULL,
    total_tests_executed    INT             NOT NULL,
    tests_passed            INT             NOT NULL,
    tests_failed            INT             NOT NULL,
    tests_skipped           INT             NOT NULL DEFAULT 0,
    pass_rate_pct           NUMERIC(5, 2)   NOT NULL,
    execution_duration_sec  NUMERIC(8, 2)   NOT NULL
);

-- 9. Fact Table: Defect Intelligence & Triage
CREATE TABLE IF NOT EXISTS analytics.fact_defect (
    defect_key              BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    defect_id               VARCHAR(32)     NOT NULL,
    severity                VARCHAR(15)     NOT NULL,
    priority                VARCHAR(15)     NOT NULL,
    status                  VARCHAR(25)     NOT NULL,
    root_cause_category     VARCHAR(50)     NULL,
    variance_amount         NUMERIC(18, 4)  NULL,
    days_open               INT             NOT NULL DEFAULT 0
);

-- 10. Fact Table: Data Quality SLI Scorecard
CREATE TABLE IF NOT EXISTS analytics.fact_data_quality (
    dq_fact_key             BIGSERIAL       PRIMARY KEY,
    date_key                INT             NOT NULL REFERENCES analytics.dim_date(date_key),
    check_category          VARCHAR(30)     NOT NULL,
    total_rules_evaluated   INT             NOT NULL,
    rules_passed            INT             NOT NULL,
    rules_failed            INT             NOT NULL,
    overall_compliance_pct  NUMERIC(5, 2)   NOT NULL
);

-- Performance Indexes on Fact Tables
CREATE INDEX IF NOT EXISTS idx_fact_perf_date_cust ON analytics.fact_loan_performance(date_key, customer_key);
CREATE INDEX IF NOT EXISTS idx_fact_perf_prod_stat ON analytics.fact_loan_performance(product_key, status);
CREATE INDEX IF NOT EXISTS idx_fact_pmt_date_loan ON analytics.fact_payment(date_key, loan_key);
CREATE INDEX IF NOT EXISTS idx_fact_fin_date_gl ON analytics.fact_financial(date_key, gl_account_code);
CREATE INDEX IF NOT EXISTS idx_fact_qa_date_cat ON analytics.fact_test_execution(date_key, test_category);
CREATE INDEX IF NOT EXISTS idx_fact_def_date_sev ON analytics.fact_defect(date_key, severity);
CREATE INDEX IF NOT EXISTS idx_fact_dq_date_cat ON analytics.fact_data_quality(date_key, check_category);
