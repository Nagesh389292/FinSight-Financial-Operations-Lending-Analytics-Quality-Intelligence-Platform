# ADR-002: Dual Database Design — Relational OLTP vs. Dimensional Star Schema OLAP

---

### Status: ACCEPTED

### Context
FinSight Enterprise must satisfy two competing data access patterns:
1. **High-Integrity Transactional Operations (OLTP)**:
   - Loan disbursement, payment application, loan status updates, defect state changes, and audit log appending.
   - Requires 3NF normalization, strict foreign keys, atomic constraints, and row-level precision.
2. **High-Performance Analytical Reporting & BI (OLAP)**:
   - Power BI multi-year trend analysis, portfolio slicing, delinquency migration matrices, scenario stress simulations, and executive KPI cards.
   - Performing multi-table joins across deeply normalized 3NF transaction tables in real-time produces slow DAX queries and complex BI semantic models.

### Decision
We adopt a **Dual Schema Architecture inside PostgreSQL**:
1. **OLTP Layer (3NF Normalized)**:
   - Schema `core`: Customers, Loans, Payments, Products, Billing Statements.
   - Schema `finance`: Ledger Accounts, Journal Entries, Daily Accruals, Reconciliation Records.
   - Schema `qa`: Requirements, Test Catalog, Test Executions, Defects.
   - Schema `governance`: Users, Roles, Audit Logs, Pipeline Runs.
2. **OLAP Layer (Kimball Star Schema)**:
   - Schema `analytics`: Conformed dimensions (`dim_date`, `dim_customer`, `dim_loan`, `dim_product`, `dim_region`, `dim_test`, `dim_macro`) and fact tables (`fact_loan_daily_snapshot`, `fact_payment_stream`, `fact_financial_reconciliation`, `fact_forecast`, `fact_scenario`, `fact_test_execution`).
   - Populated and transformed via deterministic ELT / SQL transformations (or dbt models).
3. **Power BI Connection**:
   - Power BI connects strictly to the `analytics` schema, consuming pure Star Schemas without touching transactional tables.

### Consequences
- **Positive**: Blazing fast analytical queries in Power BI with simple DAX measures; zero read-lock contention on transactional tables; clean separation of operational banking from analytical reporting.
- **Negative**: Requires an automated pipeline step to synchronize transactional updates into dimensional marts.
- **Mitigation**: Automated daily or on-demand mart refresh scripts execute with idempotent staging logic.
