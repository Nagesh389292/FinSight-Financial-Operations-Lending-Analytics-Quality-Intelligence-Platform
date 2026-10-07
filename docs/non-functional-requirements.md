# FinSight Enterprise — Non-Functional Requirements (NFR)

---

### 1. Financial Accuracy & Precision (NFR-ACC)

| ID | Category | Requirement Specification | Verification Method |
| :--- | :--- | :--- | :--- |
| **NFR-ACC-001** | Exact Decimal Precision | All monetary calculations (principal, interest, fees, accruals, ledger balances) must use fixed-point exact arithmetic (`decimal.Decimal` in Python, `NUMERIC(18, 4)` in PostgreSQL). Standard IEEE 754 floating-point numbers (`float`) are strictly prohibited in the financial path. | Static code analysis AST scan + unit tests asserting zero rounding penny drift. |
| **NFR-ACC-002** | Rounding Conventions | Rounding to currency cents ($0.01) must employ `ROUND_HALF_EVEN` (Banker's Rounding) to prevent systematic statistical bias over large loan populations. | Automated parameterized tests asserting rounding on test vectors. |
| **NFR-ACC-003** | Idempotency | Payment processing, daily accrual posting, and billing cycle jobs must be strictly idempotent. Re-executing an accrual job for date $T$ must yield identical state without duplicate transactions. | Automated replay tests executing identical payment payloads twice. |

---

### 2. Performance, Scalability & Latency (NFR-PERF)

| ID | Category | Requirement Specification | Target SLA |
| :--- | :--- | :--- | :--- |
| **NFR-PERF-001** | Accrual Engine Throughput | The daily interest calculation engine must process at least 1,500 loan facilities per second on standard commodity single-node compute. | $\ge 1,500 \text{ loans/sec}$ |
| **NFR-PERF-002** | Operational API Latency | Operational REST endpoints (`GET /loans/{id}`, `GET /servicing/waterfall`, `GET /reconciliation/summary`) must respond within $P95 < 150 \text{ ms}$. | $P95 < 150 \text{ ms}$ |
| **NFR-PERF-003** | Scenario Simulation Speed | The financial scenario planning engine must compute full portfolio stress P&L recalculations within $P95 < 600 \text{ ms}$. | $P95 < 600 \text{ ms}$ |
| **NFR-PERF-004** | Batch Reconciliation SLA | End-of-day mathematical reconciliation across all active loans must complete within $< 30 \text{ seconds}$. | $< 30 \text{ seconds}$ |

---

### 3. Reliability, Resilience & Data Integrity (NFR-REL)

| ID | Category | Requirement Specification | Implementation Detail |
| :--- | :--- | :--- | :--- |
| **NFR-REL-001** | ACID Transaction Boundaries | All loan disbursement, payment allocations, and general ledger journal postings must execute within atomic database transactions. If any sub-operation fails, the entire transaction rolls back. | PostgreSQL atomic transaction blocks (`BEGIN ... COMMIT / ROLLBACK`). |
| **NFR-REL-002** | External API Fault Tolerance | External data ingestion pipelines (FRED, Census) must implement exponential backoff with jitter (max 3 retries) and fallback to cached Bronze Parquet snapshots if upstream APIs are unreachable. | Ingestion retry decorators + local Bronze Parquet fallback cache. |
| **NFR-REL-003** | Data Quality Gatekeeping | The dbt transformation layer must enforce schema tests (not null, unique, referential relationships) before populating Gold dimensional marts. | Automated dbt test execution with non-zero exit codes on failure. |

---

### 4. Security, Governance & Auditability (NFR-SEC)

| ID | Category | Requirement Specification | Implementation Detail |
| :--- | :--- | :--- | :--- |
| **NFR-SEC-001** | Role-Based Access Control | Access to system services and endpoints must be strictly partitioned across five explicit roles: `ANALYST`, `QA_ENGINEER`, `FINANCE_CONTROLLER`, `ADMIN`, and `AUDITOR`. | JWT token-based FastAPI security dependency injection. |
| **NFR-SEC-002** | Immutable Audit Trail | All state-changing actions (loan creation, disbursement, reconciliation approvals, manual adjustments) must write append-only records to `governance.audit_logs`. Database triggers prohibit `UPDATE` or `DELETE` on this table. | PostgreSQL row-level append-only table with trigger-enforced immutability. |
| **NFR-SEC-003** | Audit Trail Non-Repudiation | Every audit log entry must store the acting user, role, timestamp, client IP, action type, entity identifier, and SHA-256 state hashes. | Cryptographic state hashes (`pre_state_hash`, `post_state_hash`). |

---

### 5. Quality Engineering & Test Automation (NFR-QA)

| ID | Category | Requirement Specification | Target Benchmark |
| :--- | :--- | :--- | :--- |
| **NFR-QA-001** | Requirements Traceability | 100% of all functional and financial calculation business requirements must be mapped to at least one active automated test scenario in the RTM. | $100\%$ RTM Coverage |
| **NFR-QA-002** | Regression Suite Run Time | The core automated test suite (functional, reconciliation, data quality) must execute in $< 45 \text{ seconds}$ to enable rapid CI/CD feedback loops. | $< 45 \text{ seconds}$ execution |
| **NFR-QA-003** | Regression Certification Gate | Releases must pass $\ge 98\%$ of all automated tests before certification. Zero critical defects are permissible for production readiness. | $\ge 98\%$ Pass Rate; $0$ Critical Defects |
| **NFR-QA-004** | Automated Defect Extraction | Any test case assertion failure must programmatically generate a structured defect payload with root-cause categorization within $< 1 \text{ second}$. | Instantaneous defect generation |
