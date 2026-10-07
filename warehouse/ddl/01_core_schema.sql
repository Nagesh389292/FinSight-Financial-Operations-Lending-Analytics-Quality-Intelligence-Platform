-- ============================================================================
-- FinSight Enterprise — Phase 1: Database DDL
-- Script 01: Core Operational Schema (core)
-- Tables: customers, loan_products, loans, loan_terms
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS core;

-- 1. Customers Master Table
CREATE TABLE IF NOT EXISTS core.customers (
    customer_id             VARCHAR(32)     PRIMARY KEY,
    legal_name              VARCHAR(150)    NOT NULL,
    customer_type           VARCHAR(30)     NOT NULL CHECK (customer_type IN ('COMMERCIAL_CORP', 'COMMERCIAL_SME', 'RETAIL_CONSUMER', 'RETAIL_MORTGAGE')),
    region                  VARCHAR(20)     NOT NULL CHECK (region IN ('NORTHEAST', 'MIDWEST', 'SOUTH', 'WEST')),
    segment                 VARCHAR(30)     NOT NULL CHECK (segment IN ('CORPORATE', 'MID_MARKET', 'SMALL_BUSINESS', 'PRIME_RETAIL', 'NEAR_PRIME_RETAIL')),
    risk_category           VARCHAR(20)     NOT NULL CHECK (risk_category IN ('PRIME_A', 'PRIME_B', 'NEAR_PRIME', 'SUBPRIME')),
    credit_score            INT             NOT NULL CHECK (credit_score BETWEEN 300 AND 850),
    annual_income           NUMERIC(15, 2)  NOT NULL CHECK (annual_income >= 0),
    debt_to_income_ratio    NUMERIC(6, 4)   NOT NULL CHECK (debt_to_income_ratio >= 0),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Loan Products Reference Table
CREATE TABLE IF NOT EXISTS core.loan_products (
    product_code            VARCHAR(32)     PRIMARY KEY,
    product_name            VARCHAR(100)    NOT NULL,
    product_family          VARCHAR(30)     NOT NULL CHECK (product_family IN ('COMMERCIAL_LENDING', 'SME_LENDING', 'CONSUMER_CREDIT', 'RESIDENTIAL_MORTGAGE')),
    rate_type               VARCHAR(20)     NOT NULL CHECK (rate_type IN ('FIXED', 'FLOATING')),
    interest_method         VARCHAR(20)     NOT NULL CHECK (interest_method IN ('ACTUAL/360', 'ACTUAL/365', '30/360')),
    default_amortization    VARCHAR(30)     NOT NULL CHECK (default_amortization IN ('EQUAL_INSTALLMENT', 'FIXED_PRINCIPAL', 'INTEREST_ONLY_BALLOON')),
    benchmark_index         VARCHAR(20)     NULL, -- e.g., 'SOFR', 'DPRIME'
    base_spread_bps         INT             NOT NULL DEFAULT 250 CHECK (base_spread_bps >= 0),
    min_term_months         INT             NOT NULL DEFAULT 6 CHECK (min_term_months > 0),
    max_term_months         INT             NOT NULL DEFAULT 360 CHECK (max_term_months >= min_term_months),
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Loan Master Facilities Table
CREATE TABLE IF NOT EXISTS core.loans (
    loan_id                 VARCHAR(32)     PRIMARY KEY,
    customer_id             VARCHAR(32)     NOT NULL REFERENCES core.customers(customer_id),
    product_code            VARCHAR(32)     NOT NULL REFERENCES core.loan_products(product_code),
    status                  VARCHAR(25)     NOT NULL CHECK (status IN ('PENDING', 'ACTIVE', 'DELINQUENT', 'PAID_OFF', 'DEFAULT_CHARGED_OFF')),
    principal_original      NUMERIC(18, 4)  NOT NULL CHECK (principal_original > 0),
    principal_outstanding   NUMERIC(18, 4)  NOT NULL CHECK (principal_outstanding >= 0),
    interest_rate_annual    NUMERIC(8, 6)   NOT NULL CHECK (interest_rate_annual >= 0), -- e.g. 0.065000 = 6.50%
    term_months             INT             NOT NULL CHECK (term_months > 0),
    start_date              DATE            NOT NULL,
    maturity_date           DATE            NOT NULL CHECK (maturity_date > start_date),
    days_past_due           INT             NOT NULL DEFAULT 0 CHECK (days_past_due >= 0),
    servicing_status        VARCHAR(20)     NOT NULL DEFAULT 'CURRENT' CHECK (servicing_status IN ('CURRENT', 'GRACE_PERIOD', 'DELINQUENT_30', 'DELINQUENT_60', 'DEFAULT_90_PLUS')),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Loan Terms Detail Table
CREATE TABLE IF NOT EXISTS core.loan_terms (
    term_id                 VARCHAR(36)     PRIMARY KEY,
    loan_id                 VARCHAR(32)     NOT NULL UNIQUE REFERENCES core.loans(loan_id) ON DELETE CASCADE,
    rate_type               VARCHAR(20)     NOT NULL CHECK (rate_type IN ('FIXED', 'FLOATING')),
    interest_method         VARCHAR(20)     NOT NULL CHECK (interest_method IN ('ACTUAL/360', 'ACTUAL/365', '30/360')),
    amortization_schedule   VARCHAR(30)     NOT NULL CHECK (amortization_schedule IN ('EQUAL_INSTALLMENT', 'FIXED_PRINCIPAL', 'INTEREST_ONLY_BALLOON')),
    benchmark_index         VARCHAR(20)     NULL,
    margin_spread_bps       INT             NOT NULL DEFAULT 0,
    payment_frequency       VARCHAR(20)     NOT NULL DEFAULT 'MONTHLY' CHECK (payment_frequency IN ('MONTHLY', 'QUARTERLY', 'ANNUAL')),
    grace_period_days       INT             NOT NULL DEFAULT 15 CHECK (grace_period_days >= 0),
    late_fee_rate_pct       NUMERIC(5, 4)   NOT NULL DEFAULT 0.0500 CHECK (late_fee_rate_pct >= 0),
    effective_date          DATE            NOT NULL,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_core_cust_region_seg ON core.customers(region, segment);
CREATE INDEX IF NOT EXISTS idx_core_loans_cust ON core.loans(customer_id);
CREATE INDEX IF NOT EXISTS idx_core_loans_prod ON core.loans(product_code);
CREATE INDEX IF NOT EXISTS idx_core_loans_status_dpd ON core.loans(status, days_past_due);
CREATE INDEX IF NOT EXISTS idx_core_terms_loan ON core.loan_terms(loan_id);
