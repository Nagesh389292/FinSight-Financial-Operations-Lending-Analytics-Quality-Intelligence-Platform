# ADR-004: QA Traceability, Test Automation & Defect Lifecycle Architecture

---

### Status: ACCEPTED

### Context
Financial institutions undergoing platform migrations, releases, or core system upgrades (e.g., Loan IQ migrations or banking system patches) require absolute traceability from Business Requirements Documents (BRDs) to test scenarios, automated test execution results, and defect resolution.

Historically, this is managed across disparate systems (e.g., Jira, HP ALM, Excel RTM matrices) with manual QA entry. In FinSight Enterprise, we need an automated, programmatic framework demonstrating end-to-end Quality Intelligence.

### Decision
We will implement an **Integrated Pytest + RTM + Automated Defect Architecture**:
1. **Requirements Repository (`qa.requirements`)**:
   - Structured relational table containing all business requirements (`BRD-CORE-*`, `BRD-FIN-*`, `BRD-QA-*`, `BRD-BI-*`, `BRD-OPS-*`).
2. **Test Scenario & Test Case Catalog (`qa.test_cases`)**:
   - Every test case in the Pytest suite is decorated with its associated Requirement ID (e.g., `@pytest.mark.requirement("BRD-FIN-001")`).
3. **Automated Test Runner & Execution Telemetry (`qa.test_executions`)**:
   - A custom Pytest hook and CLI test runner captures execution metadata: test case ID, timestamp, duration, pass/fail status, and stdout/stderr assertion payloads.
   - Automatically populates the `qa.test_executions` table upon suite completion.
4. **Automated Defect Extraction & Triage Engine (`qa.defects`)**:
   - When a test case fails, a post-test hook automatically extracts:
     - Linked requirement ID
     - Expected vs. Actual financial values
     - Calculated variance magnitude
     - Error stack trace
   - Categorizes severity automatically:
     - `CRITICAL`: Financial variance $\ge \$100$ or unhandled system crash.
     - `MAJOR`: Financial variance $\$0.02 - \$99.99$ or business rule violation.
     - `MINOR`: Formatting or cosmetic discrepancy.
   - Inserts a new defect record into `qa.defects` with status `NEW`.
5. **Traceability Matrix API & View**:
   - A dedicated view cross-joins requirements, test cases, and latest execution outcomes to produce an interactive Requirements Traceability Matrix (RTM).

### Consequences
- **Positive**: Direct closure of the Genpact JD requirements ("BRD analysis, extract testing requirements, test strategy, test scenarios, QA validation, automation, defect management, issue resolution"); instantaneous feedback on platform regressions; complete audit trail for compliance.
- **Negative**: Custom Pytest reporting plugin required.
- **Mitigation**: Implemented with standard, clean Pytest hooks (`pytest_runtest_makereport`).
