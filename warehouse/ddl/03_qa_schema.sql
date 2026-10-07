-- ============================================================================
-- FinSight Enterprise — Phase 1: Database DDL
-- Script 03: Quality Assurance & Testing Schema (qa)
-- Tables: requirements, business_rules, test_cases, test_executions,
--         defects, requirement_test_mapping
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS qa;

-- 1. Requirements Repository (BRD Core)
CREATE TABLE IF NOT EXISTS qa.requirements (
    requirement_id          VARCHAR(32)     PRIMARY KEY,
    module                  VARCHAR(30)     NOT NULL CHECK (module IN ('CORE_SERVICING', 'FINANCIAL_CALC', 'RECONCILIATION', 'QUALITY_ENGINEERING', 'BI_FORECASTING', 'SRE_GOVERNANCE')),
    title                   VARCHAR(150)    NOT NULL,
    description             TEXT            NOT NULL,
    business_owner          VARCHAR(100)    NOT NULL,
    priority                VARCHAR(15)     NOT NULL CHECK (priority IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    status                  VARCHAR(20)     NOT NULL DEFAULT 'APPROVED' CHECK (status IN ('DRAFT', 'APPROVED', 'IMPLEMENTED', 'VERIFIED')),
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Business Rules Catalog Table
CREATE TABLE IF NOT EXISTS qa.business_rules (
    rule_id                 VARCHAR(32)     PRIMARY KEY,
    requirement_id          VARCHAR(32)     NOT NULL REFERENCES qa.requirements(requirement_id),
    rule_name               VARCHAR(150)    NOT NULL,
    domain                  VARCHAR(50)     NOT NULL, -- 'INTEREST_ACCRUAL', 'WATERFALL_ALLOCATION', 'DELINQUENCY_BUCKETING', 'AMORTIZATION'
    rule_statement          TEXT            NOT NULL,
    tolerance_spec          VARCHAR(50)     NOT NULL DEFAULT 'ZERO_TOLERANCE',
    effective_date          DATE            NOT NULL,
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Test Cases Catalog Table
CREATE TABLE IF NOT EXISTS qa.test_cases (
    test_case_id            VARCHAR(32)     PRIMARY KEY,
    rule_id                 VARCHAR(32)     NOT NULL REFERENCES qa.business_rules(rule_id),
    test_category           VARCHAR(30)     NOT NULL CHECK (test_category IN ('FUNCTIONAL', 'FINANCIAL_CALC', 'RECONCILIATION', 'BOUNDARY_EDGE', 'DATA_QUALITY', 'INTEGRATION', 'REGRESSION')),
    test_name               VARCHAR(150)    NOT NULL,
    description             TEXT            NOT NULL,
    target_component        VARCHAR(50)     NOT NULL,
    expected_outcome        TEXT            NOT NULL,
    is_automated            BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Test Executions Telemetry Table
CREATE TABLE IF NOT EXISTS qa.test_executions (
    execution_id            BIGSERIAL       PRIMARY KEY,
    run_id                  VARCHAR(64)     NOT NULL,
    test_case_id            VARCHAR(32)     NOT NULL REFERENCES qa.test_cases(test_case_id),
    status                  VARCHAR(15)     NOT NULL CHECK (status IN ('PASSED', 'FAILED', 'ERROR', 'SKIPPED')),
    duration_ms             NUMERIC(9, 2)   NOT NULL,
    assertion_message       TEXT            NULL,
    executed_by             VARCHAR(50)     NOT NULL DEFAULT 'pytest-runner',
    executed_at             TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Defect Management Table
CREATE TABLE IF NOT EXISTS qa.defects (
    defect_id               VARCHAR(32)     PRIMARY KEY,
    test_case_id            VARCHAR(32)     NULL REFERENCES qa.test_cases(test_case_id),
    rule_id                 VARCHAR(32)     NULL REFERENCES qa.business_rules(rule_id),
    title                   VARCHAR(150)    NOT NULL,
    severity                VARCHAR(15)     NOT NULL CHECK (severity IN ('CRITICAL', 'MAJOR', 'MINOR')),
    priority                VARCHAR(15)     NOT NULL CHECK (priority IN ('P1', 'P2', 'P3', 'P4')),
    status                  VARCHAR(25)     NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'TRIAGED', 'IN_INVESTIGATION', 'RESOLVED', 'VERIFIED_CLOSED')),
    variance_amount         NUMERIC(18, 4)  NULL,
    root_cause_category     VARCHAR(50)     NULL, -- 'DAY_COUNT_MISMATCH', 'ROUNDING_TRUNCATION', 'WATERFALL_ORDERING', 'DATA_CORRUPTION'
    root_cause_analysis     TEXT            NULL,
    resolution_summary      TEXT            NULL,
    assigned_to             VARCHAR(100)    NULL,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at             TIMESTAMP WITH TIME ZONE NULL
);

-- 6. Requirements to Test Case Traceability Mapping (RTM) Table
CREATE TABLE IF NOT EXISTS qa.requirement_test_mapping (
    mapping_id              BIGSERIAL       PRIMARY KEY,
    requirement_id          VARCHAR(32)     NOT NULL REFERENCES qa.requirements(requirement_id),
    rule_id                 VARCHAR(32)     NOT NULL REFERENCES qa.business_rules(rule_id),
    test_case_id            VARCHAR(32)     NOT NULL REFERENCES qa.test_cases(test_case_id),
    coverage_type           VARCHAR(30)     NOT NULL DEFAULT 'PRIMARY_VALIDATION',
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_rtm_req_test UNIQUE (requirement_id, test_case_id)
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_qa_rules_req ON qa.business_rules(requirement_id);
CREATE INDEX IF NOT EXISTS idx_qa_tc_rule ON qa.test_cases(rule_id);
CREATE INDEX IF NOT EXISTS idx_qa_exec_run_tc ON qa.test_executions(run_id, test_case_id);
CREATE INDEX IF NOT EXISTS idx_qa_defects_status_sev ON qa.defects(status, severity);
CREATE INDEX IF NOT EXISTS idx_qa_rtm_req ON qa.requirement_test_mapping(requirement_id);
