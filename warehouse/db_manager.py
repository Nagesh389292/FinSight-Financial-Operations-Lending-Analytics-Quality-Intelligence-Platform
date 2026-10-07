"""
FinSight Enterprise — Database Schema Manager & Migration Runner
Connects to PostgreSQL and initializes the OLTP & OLAP schemas and reference seeds.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DDL_DIR = BASE_DIR / "ddl"
SEEDS_DIR = BASE_DIR / "seeds"

DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5432")
DB_USER = os.getenv("POSTGRES_USER", "finsight_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "finsight_secure_pass_2026")
DB_NAME = os.getenv("POSTGRES_DB", "finsight_db")


def get_connection(dbname: str = DB_NAME):
    """Establishes connection to the target PostgreSQL database."""
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        dbname=dbname
    )


def ensure_database_exists():
    """Ensures target database exists on the PostgreSQL cluster."""
    print(f"[*] Checking database '{DB_NAME}' on {DB_HOST}:{DB_PORT}...")
    try:
        conn = get_connection(dbname="postgres")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        cur.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}';")
        if not cur.fetchone():
            print(f"[*] Database '{DB_NAME}' not found. Creating...")
            cur.execute(f"CREATE DATABASE {DB_NAME};")
            print(f"[+] Database '{DB_NAME}' created successfully.")
        else:
            print(f"[+] Database '{DB_NAME}' already exists.")
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"[!] Warning: Could not verify database existence via default postgres DB: {e}")
        return False


def run_sql_script(conn, file_path: Path):
    """Reads and executes an SQL script within a transaction."""
    script_name = file_path.name
    print(f"[*] Executing SQL Script: {script_name}...")
    with open(file_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print(f"[+] Successfully executed: {script_name}")


def initialize_all_schemas():
    """Initializes all DDL scripts and seed files in order."""
    print("=" * 70)
    print(" FinSight Enterprise — Database Schema Initialization ")
    print("=" * 70)
    
    ensure_database_exists()

    try:
        conn = get_connection()
    except Exception as e:
        print(f"[!] Error connecting to PostgreSQL at {DB_HOST}:{DB_PORT}/{DB_NAME}: {e}")
        print("[!] Ensure PostgreSQL is running (e.g. via 'docker compose up db -d').")
        return False

    ddl_scripts = [
        DDL_DIR / "01_core_schema.sql",
        DDL_DIR / "02_finance_schema.sql",
        DDL_DIR / "03_qa_schema.sql",
        DDL_DIR / "04_governance_schema.sql",
        DDL_DIR / "05_analytics_mart.sql",
    ]

    seed_scripts = [
        SEEDS_DIR / "01_seed_reference_data.sql",
    ]

    try:
        print("\n--- Phase 1: Creating Relational & Dimensional Schemas ---")
        for ddl in ddl_scripts:
            if ddl.exists():
                run_sql_script(conn, ddl)
            else:
                print(f"[!] Missing DDL file: {ddl}")

        print("\n--- Phase 2: Populating Seed Reference Data ---")
        for seed in seed_scripts:
            if seed.exists():
                run_sql_script(conn, seed)
            else:
                print(f"[!] Missing Seed file: {seed}")

        print("\n" + "=" * 70)
        print(" [SUCCESS] All FinSight Enterprise schemas and seeds applied successfully! ")
        print("=" * 70)
        return True

    except Exception as e:
        conn.rollback()
        print(f"\n[!] ERROR applying schemas: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = initialize_all_schemas()
    sys.exit(0 if success else 1)
