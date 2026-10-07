-- ============================================================================
-- FinSight Enterprise — Phase 1: Reference & Configuration Seed Data
-- Pure reference data: Roles, Permissions, Products, BRD Requirements, Business Rules, Test Cases
-- (NO LOANS OR DEFECTS - Those are generated programmatically in Phase 2)
-- ============================================================================

-- 1. Governance: Roles Catalog
INSERT INTO governance.roles (role_id, role_name, description)
VALUES 
    ('ROLE_ANALYST', 'Business & Financial Analyst', 'Read-only access to analytical marts, forecasting models, and executive Power BI'),
    ('ROLE_QA_ENG', 'Quality Engineer', 'Execute automated test suites, inspect reconciliations, and manage defects'),
    ('ROLE_CONTROLLER', 'Financial Controller', 'Supervise daily accruals, accounting journals, and reconciliation tie-outs'),
    ('ROLE_ADMIN', 'Platform Administrator', 'Full platform administrative control, pipeline scheduling, and user provisioning'),
    ('ROLE_AUDITOR', 'Internal & External Auditor', 'Immutable read-only access to audit logs, data dictionaries, and regulatory trails')
ON CONFLICT (role_id) DO UPDATE SET description = EXCLUDED.description;

-- 2. Governance: Granular Permissions
INSERT INTO governance.permissions (permission_id, permission_name, module, description)
VALUES
    ('PERM_LOAN_READ', 'Read Loan Records', 'CORE', 'View borrower accounts and facility contracts'),
    ('PERM_LOAN_WRITE', 'Originate & Modify Loans', 'CORE', 'Create loan contracts and apply servicing adjustments'),
    ('PERM_PAYMENT_EXEC', 'Process Payments', 'FINANCE', 'Apply payments through contractual waterfall'),
    ('PERM_ACCRUAL_CALC', 'Trigger Accrual Calculation', 'FINANCE', 'Execute daily interest and fee accrual runs'),
    ('PERM_RECON_VIEW', 'View Reconciliations', 'FINANCE', 'Inspect mathematical expected vs actual variances'),
    ('PERM_QA_RUN_TESTS', 'Execute Test Suites', 'QA', 'Trigger automated Pytest regression and certification suites'),
    ('PERM_DEFECT_MANAGE', 'Triage & Close Defects', 'QA', 'Update defect lifecycle, severity, and root causes'),
    ('PERM_ANALYTICS_READ', 'Query Analytical Marts', 'ANALYTICS', 'Read-only access to Star Schema dimensional tables'),
    ('PERM_AUDIT_VIEW', 'Inspect Audit Trails', 'GOVERNANCE', 'Access immutable SHA-256 audit log streams')
ON CONFLICT (permission_id) DO NOTHING;

-- Map Admin to all permissions
INSERT INTO governance.role_permissions (role_id, permission_id)
SELECT 'ROLE_ADMIN', permission_id FROM governance.permissions
ON CONFLICT DO NOTHING;

-- Map QA Engineer permissions
INSERT INTO governance.role_permissions (role_id, permission_id)
VALUES 
    ('ROLE_QA_ENG', 'PERM_LOAN_READ'),
    ('ROLE_QA_ENG', 'PERM_RECON_VIEW'),
    ('ROLE_QA_ENG', 'PERM_QA_RUN_TESTS'),
    ('ROLE_QA_ENG', 'PERM_DEFECT_MANAGE'),
    ('ROLE_QA_ENG', 'PERM_ANALYTICS_READ')
ON CONFLICT DO NOTHING;

-- Map Financial Controller permissions
INSERT INTO governance.role_permissions (role_id, permission_id)
VALUES 
    ('ROLE_CONTROLLER', 'PERM_LOAN_READ'),
    ('ROLE_CONTROLLER', 'PERM_PAYMENT_EXEC'),
    ('ROLE_CONTROLLER', 'PERM_ACCRUAL_CALC'),
    ('ROLE_CONTROLLER', 'PERM_RECON_VIEW'),
    ('ROLE_CONTROLLER', 'PERM_ANALYTICS_READ')
ON CONFLICT DO NOTHING;

-- 3. Core: Standard Loan Products Reference
INSERT INTO core.loan_products (product_code, product_name, product_family, rate_type, interest_method, default_amortization, benchmark_index, base_spread_bps, min_term_months, max_term_months)
VALUES
    ('PROD-COMM-REV', 'Commercial Revolving Credit Facility', 'COMMERCIAL_LENDING', 'FLOATING', 'ACTUAL/360', 'INTEREST_ONLY_BALLOON', 'SOFR', 275, 12, 60),
    ('PROD-COMM-TERM', 'Corporate Term Loan Facility', 'COMMERCIAL_LENDING', 'FIXED', 'ACTUAL/360', 'EQUAL_INSTALLMENT', NULL, 350, 12, 120),
    ('PROD-SME-WC', 'SME Working Capital Line', 'SME_LENDING', 'FLOATING', 'ACTUAL/360', 'FIXED_PRINCIPAL', 'DPRIME', 225, 6, 36),
    ('PROD-RET-INST', 'Consumer Fixed Installment Loan', 'CONSUMER_CREDIT', 'FIXED', 'ACTUAL/365', 'EQUAL_INSTALLMENT', NULL, 550, 12, 60),
    ('PROD-MORT-30', '30-Year Residential Fixed Mortgage', 'RESIDENTIAL_MORTGAGE', 'FIXED', '30/360', 'EQUAL_INSTALLMENT', NULL, 300, 120, 360)
ON CONFLICT (product_code) DO NOTHING;

-- 4. QA: Business Requirements Catalog
INSERT INTO qa.requirements (requirement_id, module, title, description, business_owner, priority)
VALUES 
    ('BRD-CORE-001', 'CORE_SERVICING', 'Customer Segmentation & Risk Underwriting', 'Partition borrowers across 4 segments with verified credit score bounds (300-850)', 'Credit Underwriting', 'HIGH'),
    ('BRD-CORE-003', 'CORE_SERVICING', 'Floating Rate Benchmark Indexing', 'Floating facilities must link rate to reference index (SOFR/Prime) plus margin spread', 'Treasury & ALM', 'CRITICAL'),
    ('BRD-CORE-005', 'CORE_SERVICING', 'Strict Loan Lifecycle State Machine', 'Loans progress strictly: PENDING -> ACTIVE -> DELINQUENT -> PAID_OFF / DEFAULT', 'Servicing Operations', 'CRITICAL'),
    ('BRD-CORE-006', 'CORE_SERVICING', 'Contractual Payment Priority Waterfall', 'Payment application order: Fees -> Accrued Interest -> Scheduled Principal -> Prepayment', 'Servicing Operations', 'CRITICAL'),
    ('BRD-CORE-007', 'CORE_SERVICING', 'Daily Delinquency & DPD Aging Classification', 'DPD must be evaluated daily with transition into buckets (0, 1-29, 30-59, 60-89, 90+)', 'Credit Collections', 'HIGH'),
    ('BRD-FIN-001', 'FINANCIAL_CALC', 'Multi-Convention Interest Accrual Math', 'Support exact daily calculation for Actual/360, Actual/365, and 30/360 conventions', 'Financial Controller', 'CRITICAL'),
    ('BRD-FIN-003', 'FINANCIAL_CALC', 'Balance Conservation & Amortization Integrity', 'Closing balance = opening balance + disbursements - principal repayments', 'Financial Controller', 'CRITICAL'),
    ('BRD-FIN-004', 'FINANCIAL_CALC', 'Double-Entry General Ledger Integrity', 'Every transaction must generate balanced debit and credit accounting entries', 'Accounting Operations', 'CRITICAL'),
    ('BRD-FIN-005', 'RECONCILIATION', 'Automated Expected vs Actual Financial Recon', 'Automate daily comparison of processed values against independent mathematical truth', 'Lead QA / Auditor', 'CRITICAL'),
    ('BRD-FIN-006', 'RECONCILIATION', 'Penny Tolerance ($0.01) Enforcement', 'Variance > $0.01 must flag FAIL, trigger alert, and generate defect candidate', 'Financial Controller', 'CRITICAL'),
    ('BRD-QA-001', 'QUALITY_ENGINEERING', '100% Requirements Traceability (RTM)', 'Every BRD requirement must map to active test cases; zero unmapped gaps permitted', 'Lead QA Engineer', 'HIGH'),
    ('BRD-QA-003', 'QUALITY_ENGINEERING', 'Multi-Taxonomy Automated Test Suite', 'Implement automated functional, mathematical, boundary, and regression tests', 'Lead QA Engineer', 'CRITICAL'),
    ('BRD-QA-004', 'QUALITY_ENGINEERING', 'Automated Defect Extraction on Test Failure', 'Programmatically capture failed assertions, calculate variance, and log defect record', 'Lead QA Engineer', 'HIGH'),
    ('BRD-BI-001', 'BI_FORECASTING', 'Executive 6-Page Power BI Suite', 'Deliver 6 specialized views for Executive, Operations, Accounting, Recon, QA, and SRE', 'Head of BI', 'HIGH'),
    ('BRD-OPS-001', 'SRE_GOVERNANCE', 'Role-Based Access Control (RBAC)', 'Enforce 5 distinct user roles with strict endpoint permissions', 'Security Architect', 'HIGH'),
    ('BRD-OPS-002', 'SRE_GOVERNANCE', 'Cryptographic Immutable Audit Trails', 'Store SHA-256 state hashes and user context in append-only audit log table', 'Chief Compliance Officer', 'CRITICAL'),
    ('BRD-OPS-003', 'SRE_GOVERNANCE', 'Data Platform Telemetry & Freshness SLIs', 'Track pipeline duration, records processed, and data quality check pass rates', 'Platform SRE Lead', 'HIGH')
ON CONFLICT (requirement_id) DO NOTHING;

-- 5. QA: Business Rules Catalog
INSERT INTO qa.business_rules (rule_id, requirement_id, rule_name, domain, rule_statement, tolerance_spec, effective_date)
VALUES
    ('RULE-ACCR-001', 'BRD-FIN-001', 'Actual/360 Daily Interest Rule', 'INTEREST_ACCRUAL', 'Daily interest = Principal * (Annual Rate / 360). Banker rounding applied.', 'MAX_0_01_USD', '2022-01-01'),
    ('RULE-ACCR-002', 'BRD-FIN-001', 'Actual/365 Daily Interest Rule', 'INTEREST_ACCRUAL', 'Daily interest = Principal * (Annual Rate / 365). Leap year uses 366 for Actual/Actual.', 'MAX_0_01_USD', '2022-01-01'),
    ('RULE-ACCR-003', 'BRD-FIN-001', '30/360 Monthly Accrual Rule', 'INTEREST_ACCRUAL', 'Monthly interest = Principal * (Annual Rate / 12). Assumes 30-day uniform month.', 'MAX_0_01_USD', '2022-01-01'),
    ('RULE-WATERFALL-001', 'BRD-CORE-006', 'Priority Cash Allocation Rule', 'WATERFALL_ALLOCATION', 'Funds applied strictly: 1. Fees, 2. Interest, 3. Scheduled Principal, 4. Prepayment.', 'ZERO_TOLERANCE', '2022-01-01'),
    ('RULE-DPD-001', 'BRD-CORE-007', 'Delinquency Aging Rule', 'DELINQUENCY_BUCKETING', 'Days past due = Evaluation Date - Oldest Due Date. 0=Current, 1-29=B1, 30-59=B2, 60-89=B3, 90+=Default.', 'ZERO_TOLERANCE', '2022-01-01'),
    ('RULE-RECON-001', 'BRD-FIN-005', 'Accrual Tie-Out Variance Rule', 'INTEREST_ACCRUAL', 'Absolute difference between processed interest and mathematical truth must be <= $0.01.', 'MAX_0_01_USD', '2022-01-01')
ON CONFLICT (rule_id) DO NOTHING;

-- 6. QA: Test Cases Catalog
INSERT INTO qa.test_cases (test_case_id, rule_id, test_category, test_name, description, target_component, expected_outcome)
VALUES
    ('TC-ACCR-001', 'RULE-ACCR-001', 'FINANCIAL_CALC', 'Verify Actual/360 Commercial Facility Accrual', 'Compute 30-day accrual on $1M at 6% using Actual/360', 'math_truth', 'Exact $5,000.00 accrual with zero penny drift'),
    ('TC-ACCR-002', 'RULE-ACCR-002', 'FINANCIAL_CALC', 'Verify Actual/365 Consumer Credit Accrual', 'Compute 30-day accrual on $100k at 7.3% using Actual/365', 'math_truth', 'Exact $600.00 accrual with zero penny drift'),
    ('TC-ACCR-003', 'RULE-ACCR-003', 'FINANCIAL_CALC', 'Verify 30/360 Mortgage Facility Accrual', 'Compute monthly accrual on $250k at 4.8% using 30/360', 'math_truth', 'Exact $1,000.00 accrual with zero penny drift'),
    ('TC-ROUND-001', 'RULE-ACCR-001', 'FINANCIAL_CALC', 'Validate Banker Rounding Half-Even', 'Test 2.125 -> 2.12 and 2.135 -> 2.14 rounding logic', 'math_truth', 'Unbiased half-even rounding behavior confirmed'),
    ('TC-WATERFALL-001', 'RULE-WATERFALL-001', 'FUNCTIONAL', 'Verify Standard On-Time Payment Waterfall', 'Process payment covering fee, interest, and scheduled principal', 'payment_engine', 'All buckets satisfied; closing balance reduced accurately'),
    ('TC-WATERFALL-002', 'RULE-WATERFALL-001', 'FUNCTIONAL', 'Verify Short Payment Waterfall Ordering', 'Process partial payment: fee paid first, partial interest, zero principal', 'payment_engine', 'Principal balance untouched; fee satisfied first'),
    ('TC-WATERFALL-003', 'RULE-WATERFALL-001', 'FUNCTIONAL', 'Verify Surplus Payment Prepayment Allocation', 'Process excess payment with surplus directed to unscheduled principal', 'payment_engine', 'Closing principal reduced by scheduled plus prepayment'),
    ('TC-DPD-001', 'RULE-DPD-001', 'FUNCTIONAL', 'Verify DPD Regulatory Bucket Transitions', 'Test bucket assignments across 0, 15, 45, 75, 95 DPD values', 'servicing_engine', 'Exact match with Current, B1, B2, B3, Default buckets'),
    ('TC-RECON-001', 'RULE-RECON-001', 'RECONCILIATION', 'Verify Exact Match Reconciliation Pass', 'Compare equal expected and processed accrual amounts ($12,450.00)', 'recon_service', 'Status PASS, variance $0.00'),
    ('TC-RECON-002', 'RULE-RECON-001', 'RECONCILIATION', 'Verify Penny Tolerance Boundary Pass', 'Verify $0.005 difference passes within $0.01 tolerance', 'recon_service', 'Status PASS, within tolerance True'),
    ('TC-RECON-003', 'RULE-RECON-001', 'RECONCILIATION', 'Verify Tolerance Breach Detection Fail', 'Verify $0.02 discrepancy triggers FAIL status', 'recon_service', 'Status FAIL, variance $0.02 logged as defect candidate'),
    ('TC-RECON-004', 'RULE-RECON-001', 'RECONCILIATION', 'Verify Material Miscalculation Defect Extraction', 'Verify $350.00 accrual error flags CRITICAL failure', 'recon_service', 'Status FAIL, variance $350.00 logged with root cause')
ON CONFLICT (test_case_id) DO NOTHING;

-- 7. QA: Traceability Mapping (RTM)
INSERT INTO qa.requirement_test_mapping (requirement_id, rule_id, test_case_id, coverage_type)
VALUES
    ('BRD-FIN-001', 'RULE-ACCR-001', 'TC-ACCR-001', 'PRIMARY_VALIDATION'),
    ('BRD-FIN-001', 'RULE-ACCR-002', 'TC-ACCR-002', 'PRIMARY_VALIDATION'),
    ('BRD-FIN-001', 'RULE-ACCR-003', 'TC-ACCR-003', 'PRIMARY_VALIDATION'),
    ('BRD-FIN-001', 'RULE-ACCR-001', 'TC-ROUND-001', 'BOUNDARY_VALIDATION'),
    ('BRD-CORE-006', 'RULE-WATERFALL-001', 'TC-WATERFALL-001', 'PRIMARY_VALIDATION'),
    ('BRD-CORE-006', 'RULE-WATERFALL-001', 'TC-WATERFALL-002', 'BOUNDARY_VALIDATION'),
    ('BRD-CORE-006', 'RULE-WATERFALL-001', 'TC-WATERFALL-003', 'BOUNDARY_VALIDATION'),
    ('BRD-CORE-007', 'RULE-DPD-001', 'TC-DPD-001', 'PRIMARY_VALIDATION'),
    ('BRD-FIN-005', 'RULE-RECON-001', 'TC-RECON-001', 'PRIMARY_VALIDATION'),
    ('BRD-FIN-006', 'RULE-RECON-001', 'TC-RECON-002', 'BOUNDARY_VALIDATION'),
    ('BRD-FIN-006', 'RULE-RECON-001', 'TC-RECON-003', 'NEGATIVE_VALIDATION'),
    ('BRD-FIN-006', 'RULE-RECON-001', 'TC-RECON-004', 'SEVERITY_VALIDATION')
ON CONFLICT (requirement_id, test_case_id) DO NOTHING;
