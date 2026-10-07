# ADR-001: Architectural Pattern — Modular Monolith vs. Distributed Microservices

---

### Status: ACCEPTED

### Context
FinSight Enterprise encompasses diverse domain boundaries: loan onboarding, servicing, daily accruals, financial reconciliation, quality assurance, defect management, predictive forecasting, and administrative governance.

A common pitfall in enterprise showcase projects is prematurely decomposing the application into 8–10 independent network-distributed microservices (e.g. separate Docker containers for `loan-service`, `payment-service`, `accounting-service`, `qa-service`). In a local development or single-node demonstration environment, this creates:
- Severe operational overhead (orchestration complexity, network latency, distributed transaction failure modes, inter-service authentication boilerplate).
- Complex debugging and difficult local setup for interview evaluators or CI/CD pipelines.
- Distributed data consistency dilemmas (e.g., dual-write failure between servicing and accounting).

### Decision
We will construct **FinSight Enterprise as a Modular Monolith in Python / FastAPI**:
1. All domain services (`core`, `finance`, `qa`, `forecasting`, `governance`) reside within a single codebase under structured domain packages.
2. Domain services communicate via well-defined internal Python interfaces, domain events, and shared database transaction contexts rather than high-latency HTTP/gRPC network hops.
3. Database isolation is maintained logically via distinct PostgreSQL schemas (`core`, `finance`, `qa`, `governance`, `analytics`).
4. FastAPI serves unified, route-grouped API endpoints under `/api/v1/` with decoupled dependency injection.

### Consequences
- **Positive**: Single codebase, atomic database transactions across servicing and accounting updates, zero network latency between services, trivial local setup via `docker compose up`, fast end-to-end integration tests.
- **Negative**: Scalability is constrained to vertical scaling or stateless horizontal scaling of the entire monolith.
- **Mitigation**: Clear package isolation ensures any domain service can be extracted into an independent microservice in the future if scale justifies it.
