# ADR-005: Cloud Model & Deployment Strategy — PaaS-First with IaaS Control

---

### Status: ACCEPTED

### Context
When positioning **FinSight Enterprise**, we must choose an appropriate cloud delivery and deployment model. 

Positioning the project as **SaaS (Software-as-a-Service)** is inaccurate and unhelpful: SaaS is a commercial business-to-customer software sales model (requiring tenant billing, sign-up funnels, marketing portals, stripe integration). FinSight is an **internal enterprise financial analytics, lending validation, and QA decision platform** built for a financial institution.

Conversely, deploying exclusively on **pure IaaS (Infrastructure-as-a-Service)** (e.g., bare EC2 instances, manual OS patching, manual PostgreSQL configuration, manual load balancer wiring) creates excessive administrative overhead and distracts from core financial calculation, testing, and analytics capabilities.

### Decision
We adopt a **PaaS-First Cloud Model with IaaS Infrastructure Control**:

1. **PaaS Services (Primary Application & Data Tier)**:
   - **AWS App Runner / ECS Fargate**: Managed container runtime for the FastAPI backend. Eliminates VM maintenance, provides automated TLS, and handles horizontal scaling.
   - **AWS RDS PostgreSQL**: Managed relational database service providing automated daily snapshots, connection encryption, and managed engine updates for our OLTP and OLAP schemas.
   - **AWS S3**: Managed object storage for the Bronze Parquet data lake, ML forecast model registry, and QA execution artifacts.
   - **AWS CloudWatch**: Managed metrics, structured log ingestion, and SLI alarms.

2. **IaaS Services (Infrastructure, Network & Security Control)**:
   - **AWS VPC**: Custom virtual private cloud with private subnets for RDS, public subnets for load balancing/ingress, and network security groups.
   - **AWS IAM**: Fine-grained least-privilege IAM roles (`FinSightAppExecutionRole`, `FinSightIngestionPolicy`).
   - **Docker Containers**: Portable container images defined via `Dockerfile` and orchestrated locally via `docker-compose.yml`.

3. **Zero-Cost Local Development Parity**:
   - The entire cloud architecture is mirrored locally using Docker Compose (`postgres:16`, `fastapi`, local volume storage) so developers, evaluators, and CI pipelines can run, test, and verify the platform without incurring AWS cloud hosting costs.

### Consequences
- **Positive**:
  - Highlights enterprise cloud competency across both managed platform services (PaaS) and infrastructure fundamentals (IaaS).
  - Aligns directly with IQVIA (Cloud Data Platforms, SRE, Governance), Genpact (Application Testing & Validation), and Barclays (Enterprise Reporting).
  - Prevents cloud bills while providing production-ready AWS deployment scripts (Terraform/CloudFormation & Docker).
- **Negative**:
  - Requires maintaining configuration parity between local Docker Compose and AWS deployment manifests.
- **Mitigation**:
  - Use containerized 12-Factor App design patterns where environment variables (`.env`) govern whether the app connects to local PostgreSQL or AWS RDS.
