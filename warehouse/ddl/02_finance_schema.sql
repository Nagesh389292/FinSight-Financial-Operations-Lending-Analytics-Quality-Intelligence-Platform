-- ============================================================================
-- FinSight Enterprise — Phase 1: Database DDL
-- Script 02: Finance, Accounting & Reconciliation Schema (finance)
-- Tables: payments, payment_allocations, interest_accruals,
--         accounting_entries, accounting_entry_lines, reconciliation_results
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS finance;

-- 1. Payments Transaction Master Table
CREATE TABLE IF NOT EXISTS finance.payments (
    payment_id              VARCHAR(36)     PRIMARY KEY,
    loan_id                 VARCHAR(32)     NOT NULL REFERENCES core.loans(loan_id),
    payment_date            DATE            NOT NULL,
    payment_amount          NUMERIC(18, 4)  NOT NULL CHECK (payment_amount > 0),
    payment_method          VARCHAR(30)     NOT NULL DEFAULT 'ACH' CHECK (payment_method IN ('ACH', 'WIRE', 'LOCKBOX', 'INTERNAL_TRANSFER')),
    status                  VARCHAR(20)     NOT NULL DEFAULT 'PROCESSED' CHECK (status IN ('RECEIVED', 'PROCESSED', 'REVERSED', 'FAILED')),
    reference_number        VARCHAR(64)     NOT NULL,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Payment Allocations Waterfall Breakdown Table
CREATE TABLE IF NOT EXISTS finance.payment_allocations (
    allocation_id           BIGSERIAL       PRIMARY KEY,
    payment_id              VARCHAR(36)     NOT NULL REFERENCES finance.payments(payment_id) ON DELETE CASCADE,
    loan_id                 VARCHAR(32)     NOT NULL REFERENCES core.loans(loan_id),
    principal_amount        NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (principal_amount >= 0),
    interest_amount         NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (interest_amount >= 0),
    fees_amount             NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (fees_amount >= 0),
    prepayment_amount       NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (prepayment_amount >= 0),
    total_allocated         NUMERIC(18, 4)  NOT NULL CHECK (total_allocated > 0),
    closing_principal_balance NUMERIC(18, 4) NOT NULL CHECK (closing_principal_balance >= 0),
    allocation_timestamp    TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_allocation_sum CHECK (total_allocated = (principal_amount + interest_amount + fees_amount + prepayment_amount))
);

-- 3. Daily Interest & Fee Accruals Table
CREATE TABLE IF NOT EXISTS finance.interest_accruals (
    accrual_id              BIGSERIAL       PRIMARY KEY,
    loan_id                 VARCHAR(32)     NOT NULL REFERENCES core.loans(loan_id),
    accrual_date            DATE            NOT NULL,
    start_principal_balance NUMERIC(18, 4)  NOT NULL CHECK (start_principal_balance >= 0),
    interest_rate_annual    NUMERIC(8, 6)   NOT NULL CHECK (interest_rate_annual >= 0),
    interest_method         VARCHAR(20)     NOT NULL CHECK (interest_method IN ('ACTUAL/360', 'ACTUAL/365', '30/360')),
    day_fraction            NUMERIC(10, 8)  NOT NULL,
    interest_accrual_amount NUMERIC(18, 4)  NOT NULL CHECK (interest_accrual_amount >= 0),
    fee_accrual_amount      NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (fee_accrual_amount >= 0),
    cumulative_unpaid_interest NUMERIC(18, 4) NOT NULL DEFAULT 0.0000 CHECK (cumulative_unpaid_interest >= 0),
    is_posted_to_gl         BOOLEAN         NOT NULL DEFAULT FALSE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_finance_loan_accrual UNIQUE (loan_id, accrual_date)
);

-- 4. Double-Entry Accounting Entries Header Table
CREATE TABLE IF NOT EXISTS finance.accounting_entries (
    entry_id                VARCHAR(36)     PRIMARY KEY,
    accounting_date         DATE            NOT NULL,
    source_event            VARCHAR(30)     NOT NULL CHECK (source_event IN ('DISBURSEMENT', 'DAILY_ACCRUAL', 'PAYMENT_RECEIPT', 'FEE_ASSESSMENT', 'REVERSAL', 'CHARGE_OFF')),
    source_reference_id     VARCHAR(64)     NOT NULL, -- linked payment_id, accrual_id, or loan_id
    total_debit             NUMERIC(18, 4)  NOT NULL CHECK (total_debit >= 0),
    total_credit            NUMERIC(18, 4)  NOT NULL CHECK (total_credit >= 0),
    is_balanced             BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_balanced_entry CHECK (total_debit = total_credit)
);

-- 5. Accounting Entry Detail Lines Table
CREATE TABLE IF NOT EXISTS finance.accounting_entry_lines (
    line_id                 BIGSERIAL       PRIMARY KEY,
    entry_id                VARCHAR(36)     NOT NULL REFERENCES finance.accounting_entries(entry_id) ON DELETE CASCADE,
    line_number             INT             NOT NULL,
    gl_account_code         VARCHAR(20)     NOT NULL,
    gl_account_name         VARCHAR(100)    NOT NULL,
    debit_amount            NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (debit_amount >= 0),
    credit_amount           NUMERIC(18, 4)  NOT NULL DEFAULT 0.0000 CHECK (credit_amount >= 0),
    memo                    VARCHAR(255)    NULL,
    CONSTRAINT chk_single_side CHECK ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
);

-- 6. Financial Reconciliation Results Table (Expected vs. Processed)
CREATE TABLE IF NOT EXISTS finance.reconciliation_results (
    reconciliation_id       VARCHAR(40)     PRIMARY KEY,
    loan_id                 VARCHAR(32)     NOT NULL REFERENCES core.loans(loan_id),
    cycle_date              DATE            NOT NULL,
    reconciliation_type     VARCHAR(40)     NOT NULL CHECK (reconciliation_type IN ('INTEREST_ACCRUAL', 'PRINCIPAL_REDUCTION', 'CLOSING_BALANCE', 'FEE_ASSESSMENT', 'GL_SUBLEDGER_TIE_OUT')),
    expected_amount         NUMERIC(18, 4)  NOT NULL,
    actual_amount           NUMERIC(18, 4)  NOT NULL,
    variance_amount         NUMERIC(18, 4)  NOT NULL,
    tolerance_threshold     NUMERIC(6, 4)   NOT NULL DEFAULT 0.0100,
    status                  VARCHAR(15)     NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    root_cause_category     VARCHAR(50)     NULL, -- 'DAY_COUNT_MISMATCH', 'ROUNDING_TRUNCATION', 'WATERFALL_ORDERING', 'DATA_CORRUPTION'
    notes                   TEXT            NULL,
    reconciled_at           TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_fin_pmt_loan_date ON finance.payments(loan_id, payment_date);
CREATE INDEX IF NOT EXISTS idx_fin_alloc_payment ON finance.payment_allocations(payment_id);
CREATE INDEX IF NOT EXISTS idx_fin_accrual_loan_date ON finance.interest_accruals(loan_id, accrual_date);
CREATE INDEX IF NOT EXISTS idx_fin_entries_date_src ON finance.accounting_entries(accounting_date, source_event);
CREATE INDEX IF NOT EXISTS idx_fin_lines_entry ON finance.accounting_entry_lines(entry_id);
CREATE INDEX IF NOT EXISTS idx_fin_recon_status_type ON finance.reconciliation_results(status, reconciliation_type);
