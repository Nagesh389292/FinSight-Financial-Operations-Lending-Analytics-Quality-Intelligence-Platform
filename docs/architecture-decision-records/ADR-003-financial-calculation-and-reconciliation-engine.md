# ADR-003: Financial Calculation & Reconciliation Engine Architecture

---

### Status: ACCEPTED

### Context
In loan servicing platforms (including platforms like Finastra Loan IQ or proprietary core banking engines), software bugs often manifest as subtle rounding discrepancies, incorrect day-count conventions, or payment waterfall ordering bugs.

To demonstrate a robust Quality Engineering and Financial Validation capability (as required by the Genpact JD), FinSight needs an architectural mechanism to prove whether servicing calculations match true financial mathematics.

### Decision
We will establish an **Independent Dual-Path Financial Validation Architecture**:
1. **Operational Servicing Simulator (Path A)**:
   - Simulates operational servicing transactions as they occur in real banking systems (billing generation, payment cash allocation, ledger posting).
   - Injected with a controlled percentage of real-world operational defects (rounding drift, convention mismatch).
2. **Mathematical Truth Engine (Path B)**:
   - An independent, pure mathematical calculation module implementing rigorous financial banking equations using Python `decimal.Decimal` and exact calendar mathematics.
   - Computes the uncompromised theoretical benchmark for:
     - Daily interest accrual ($I_{\text{expected}}$)
     - Scheduled principal reduction ($P_{\text{expected}}$)
     - Total fee allocation ($F_{\text{expected}}$)
     - Ending facility principal balance ($B_{\text{expected}}$)
3. **Reconciliation & Variance Analyzer**:
   - An automated engine that evaluates:
     $$\Delta = \text{Processed Value} - \text{Expected Value}$$
   - Compares variance against a strict tolerance threshold ($\le \$0.01$).
   - Flags discrepancies, assigns failure categories, and triggers automated defect creation.

### Consequences
- **Positive**: Directly mirrors tier-1 commercial banking QA and financial reconciliation practices; provides real data for the QA dashboard; empowers business analysts to trace variance down to individual calculation rules.
- **Negative**: Requires maintaining two parallel calculation pathways.
- **Mitigation**: The Truth Engine is kept pure and stateless, while the Servicing Simulator handles state persistence.
