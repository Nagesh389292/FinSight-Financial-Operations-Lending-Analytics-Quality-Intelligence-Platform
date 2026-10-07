-- ============================================================================
-- FinSight Enterprise — Phase 1: Database DDL
-- Script 04: Governance, Security & Observability Schema (governance)
-- Tables: roles, permissions, users, audit_log, data_quality_results
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS governance;

-- 1. Roles Catalog Table
CREATE TABLE IF NOT EXISTS governance.roles (
    role_id                 VARCHAR(30)     PRIMARY KEY,
    role_name               VARCHAR(50)     NOT NULL UNIQUE,
    description             TEXT            NOT NULL,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Granular Permissions Catalog Table
CREATE TABLE IF NOT EXISTS governance.permissions (
    permission_id           VARCHAR(50)     PRIMARY KEY,
    permission_name         VARCHAR(100)    NOT NULL,
    module                  VARCHAR(30)     NOT NULL, -- 'CORE', 'FINANCE', 'QA', 'ANALYTICS', 'GOVERNANCE'
    description             TEXT            NOT NULL
);

-- Role-Permission Mapping Table
CREATE TABLE IF NOT EXISTS governance.role_permissions (
    role_id                 VARCHAR(30)     NOT NULL REFERENCES governance.roles(role_id) ON DELETE CASCADE,
    permission_id           VARCHAR(50)     NOT NULL REFERENCES governance.permissions(permission_id) ON DELETE CASCADE,
    granted_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (role_id, permission_id)
);

-- 3. Platform Users Master Table
CREATE TABLE IF NOT EXISTS governance.users (
    user_id                 VARCHAR(36)     PRIMARY KEY,
    username                VARCHAR(50)     NOT NULL UNIQUE,
    email                   VARCHAR(100)    NOT NULL UNIQUE,
    full_name               VARCHAR(150)    NOT NULL,
    role_id                 VARCHAR(30)     NOT NULL REFERENCES governance.roles(role_id),
    department              VARCHAR(50)     NOT NULL,
    is_active               BOOLEAN         NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Immutable Append-Only Audit Log Table
CREATE TABLE IF NOT EXISTS governance.audit_log (
    audit_id                BIGSERIAL       PRIMARY KEY,
    user_id                 VARCHAR(36)     NOT NULL,
    role_id                 VARCHAR(30)     NOT NULL,
    action_type             VARCHAR(50)     NOT NULL, -- 'LOAN_ORIGINATED', 'PAYMENT_PROCESSED', 'RECON_OVERRIDE', 'DEFECT_TRIAGED', 'DQ_RUN'
    entity_type             VARCHAR(50)     NOT NULL, -- 'LOAN', 'PAYMENT', 'RECONCILIATION', 'DEFECT', 'DATA_QUALITY'
    entity_id               VARCHAR(64)     NOT NULL,
    pre_state_hash          VARCHAR(64)     NULL, -- SHA-256 hash of entity before modification
    post_state_hash         VARCHAR(64)     NOT NULL, -- SHA-256 hash of entity after modification
    change_payload          JSONB           NOT NULL,
    client_ip               VARCHAR(45)     NOT NULL DEFAULT '127.0.0.1',
    timestamp_utc           TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Data Quality Test Results (SRE & Governance Scorecards)
CREATE TABLE IF NOT EXISTS governance.data_quality_results (
    dq_result_id            BIGSERIAL       PRIMARY KEY,
    check_name              VARCHAR(100)    NOT NULL,
    check_category          VARCHAR(30)     NOT NULL CHECK (check_category IN ('COMPLETENESS', 'VALIDITY', 'UNIQUENESS', 'REFERENTIAL_INTEGRITY', 'FRESHNESS')),
    target_schema           VARCHAR(30)     NOT NULL,
    target_table            VARCHAR(50)     NOT NULL,
    target_column           VARCHAR(50)     NULL,
    status                  VARCHAR(15)     NOT NULL CHECK (status IN ('PASSED', 'FAILED', 'WARNING')),
    records_evaluated       INT             NOT NULL CHECK (records_evaluated >= 0),
    failing_records_count   INT             NOT NULL DEFAULT 0 CHECK (failing_records_count >= 0),
    pass_rate_pct           NUMERIC(5, 2)   NOT NULL CHECK (pass_rate_pct BETWEEN 0 AND 100),
    error_sample            JSONB           NULL,
    evaluated_at            TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Performance Indexes
CREATE INDEX IF NOT EXISTS idx_gov_users_role ON governance.users(role_id);
CREATE INDEX IF NOT EXISTS idx_gov_audit_entity ON governance.audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_gov_audit_timestamp ON governance.audit_log(timestamp_utc);
CREATE INDEX IF NOT EXISTS idx_gov_dq_status_cat ON governance.data_quality_results(status, check_category);
