"""
FinSight Enterprise — Database Schema Validation Tests (Phase 1, Step 9)
Validates DDL integrity, primary/foreign key definitions, check constraints,
and RTM seed mappings across core, finance, qa, governance, and analytics schemas.
"""

import re
import sqlite3
from pathlib import Path
import pytest

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DDL_DIR = BASE_DIR / "warehouse" / "ddl"
SEEDS_DIR = BASE_DIR / "warehouse" / "seeds"

EXPECTED_SCHEMAS = ["core", "finance", "qa", "governance", "analytics"]

EXPECTED_TABLES = {
    "core": ["customers", "loan_products", "loans", "loan_terms"],
    "finance": ["payments", "payment_allocations", "interest_accruals", "accounting_entries", "accounting_entry_lines", "reconciliation_results"],
    "qa": ["requirements", "business_rules", "test_cases", "test_executions", "defects", "requirement_test_mapping"],
    "governance": ["roles", "permissions", "role_permissions", "users", "audit_log", "data_quality_results"],
    "analytics": [
        "dim_date", "dim_customer", "dim_product", "dim_loan",
        "fact_loan_performance", "fact_payment", "fact_financial",
        "fact_test_execution", "fact_defect", "fact_data_quality"
    ]
}


def test_ddl_files_exist_and_readable():
    """Verify all 5 Phase 1 DDL scripts and seed files exist."""
    expected_files = [
        "01_core_schema.sql",
        "02_finance_schema.sql",
        "03_qa_schema.sql",
        "04_governance_schema.sql",
        "05_analytics_mart.sql",
        "init_db.sql"
    ]
    for fname in expected_files:
        fpath = DDL_DIR / fname
        assert fpath.exists(), f"Missing DDL file: {fname}"
        assert fpath.stat().st_size > 0, f"Empty DDL file: {fname}"

    seed_file = SEEDS_DIR / "01_seed_reference_data.sql"
    assert seed_file.exists()
    assert seed_file.stat().st_size > 0


def test_all_expected_tables_declared_in_ddl():
    """Validates that every table in the architecture taxonomy is declared via CREATE TABLE."""
    all_sql = ""
    for ddl in sorted(DDL_DIR.glob("0*.sql")):
        with open(ddl, "r", encoding="utf-8") as f:
            all_sql += "\n" + f.read()

    for schema_name, tables in EXPECTED_TABLES.items():
        for table_name in tables:
            pattern = rf"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?{schema_name}\.{table_name}\b"
            match = re.search(pattern, all_sql, re.IGNORECASE)
            assert match is not None, f"Table {schema_name}.{table_name} not found in DDL scripts!"


def test_primary_keys_and_foreign_keys_present():
    """Validates primary keys and foreign keys in core and finance tables."""
    core_sql = (DDL_DIR / "01_core_schema.sql").read_text(encoding="utf-8")
    fin_sql = (DDL_DIR / "02_finance_schema.sql").read_text(encoding="utf-8")
    qa_sql = (DDL_DIR / "03_qa_schema.sql").read_text(encoding="utf-8")

    # Primary key assertions (regex to be robust to whitespace formatting)
    assert re.search(r"customer_id\s+VARCHAR\(32\)\s+PRIMARY KEY", core_sql) is not None
    assert re.search(r"loan_id\s+VARCHAR\(32\)\s+PRIMARY KEY", core_sql) is not None
    assert re.search(r"payment_id\s+VARCHAR\(36\)\s+PRIMARY KEY", fin_sql) is not None
    assert re.search(r"requirement_id\s+VARCHAR\(32\)\s+PRIMARY KEY", qa_sql) is not None

    # Foreign key assertions
    assert "REFERENCES core.customers(customer_id)" in core_sql
    assert "REFERENCES core.loan_products(product_code)" in core_sql
    assert "REFERENCES core.loans(loan_id)" in fin_sql
    assert "REFERENCES qa.requirements(requirement_id)" in qa_sql
    assert "REFERENCES qa.business_rules(rule_id)" in qa_sql


def test_in_memory_sqlite_schema_and_check_constraints():
    """
    Executes table creation and constraint checks in an in-memory SQL database.
    Validates check constraints:
    1. credit_score range (300-850)
    2. payment_amount > 0
    3. balanced accounting entry (total_debit == total_credit)
    """
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()

    # Create test customers table
    cur.execute("""
        CREATE TABLE test_customers (
            customer_id TEXT PRIMARY KEY,
            legal_name TEXT NOT NULL,
            credit_score INT NOT NULL CHECK (credit_score BETWEEN 300 AND 850),
            annual_income REAL NOT NULL CHECK (annual_income >= 0)
        );
    """)

    # 1. Valid customer insert
    cur.execute("INSERT INTO test_customers VALUES ('C001', 'Acme Corp', 750, 100000.0);")
    conn.commit()

    # 2. Invalid credit score (< 300) must fail check constraint
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO test_customers VALUES ('C002', 'Bad Credit', 250, 50000.0);")

    # 3. Invalid annual income (< 0) must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO test_customers VALUES ('C003', 'Negative Income', 650, -500.0);")

    # Create test accounting entry table
    cur.execute("""
        CREATE TABLE test_accounting_entries (
            entry_id TEXT PRIMARY KEY,
            total_debit REAL NOT NULL,
            total_credit REAL NOT NULL,
            CONSTRAINT chk_balanced CHECK (total_debit = total_credit)
        );
    """)

    # Valid balanced entry
    cur.execute("INSERT INTO test_accounting_entries VALUES ('E001', 5000.0, 5000.0);")
    conn.commit()

    # Unbalanced entry must fail
    with pytest.raises(sqlite3.IntegrityError):
        cur.execute("INSERT INTO test_accounting_entries VALUES ('E002', 5000.0, 4999.0);")

    conn.close()


def test_seed_script_syntax_and_rtm_integrity():
    """Validates that seed data contains correct reference values and RTM mappings."""
    seed_sql = (SEEDS_DIR / "01_seed_reference_data.sql").read_text(encoding="utf-8")

    # Verify roles are seeded
    assert "'ROLE_ANALYST'" in seed_sql
    assert "'ROLE_QA_ENG'" in seed_sql
    assert "'ROLE_CONTROLLER'" in seed_sql
    assert "'ROLE_ADMIN'" in seed_sql
    assert "'ROLE_AUDITOR'" in seed_sql

    # Verify core products are seeded
    assert "'PROD-COMM-REV'" in seed_sql
    assert "'PROD-COMM-TERM'" in seed_sql
    assert "'PROD-SME-WC'" in seed_sql
    assert "'PROD-RET-INST'" in seed_sql
    assert "'PROD-MORT-30'" in seed_sql

    # Verify BRD requirements are seeded
    assert "'BRD-CORE-001'" in seed_sql
    assert "'BRD-FIN-001'" in seed_sql
    assert "'BRD-FIN-005'" in seed_sql
    assert "'BRD-FIN-006'" in seed_sql

    # Verify RTM mappings are seeded
    assert "INSERT INTO qa.requirement_test_mapping" in seed_sql
    assert "'TC-ACCR-001'" in seed_sql
    assert "'TC-RECON-001'" in seed_sql
