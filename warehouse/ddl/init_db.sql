-- ============================================================================
-- FinSight Enterprise — Database Master Initialization Script
-- Executes all schema definitions in strict dependency order
-- ============================================================================

\echo '>>> Initializing Schema 01: Core Operational Tables...'
\i 01_core_schema.sql

\echo '>>> Initializing Schema 02: Finance, Accounting & Reconciliation...'
\i 02_finance_schema.sql

\echo '>>> Initializing Schema 03: Quality Assurance, RTM & Defects...'
\i 03_qa_schema.sql

\echo '>>> Initializing Schema 04: Governance, RBAC & Immutable Audit Logs...'
\i 04_governance_schema.sql

\echo '>>> Initializing Schema 05: Dimensional Analytics Mart (Kimball)...'
\i 05_analytics_mart.sql

\echo '>>> FinSight Enterprise Database Initialized Successfully!'
